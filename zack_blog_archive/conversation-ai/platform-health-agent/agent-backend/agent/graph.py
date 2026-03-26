"""LangGraph agent graph — the agentic brain.

This implements two workflow paths:

1. General QA (ReAct loop):
   START → router → llm → [should_continue] → tools → llm → ... → END

2. Eligibility Check (structured workflow):
   START → router → gather_info → check_policy → [branch] → eligible/ineligible/uncertain → END

Production patterns included:
- Request/response logging with timing
- Loop protection (max iterations)
- Tool execution error handling
- Structured observability via tool_calls_log
"""

import json
import time
import logging
from langchain_core.messages import AIMessage, ToolMessage, SystemMessage, HumanMessage
from langchain_aws import ChatBedrockConverse
from langgraph.graph import StateGraph, END

from agent.state import AgentState
from agent.prompts import SYSTEM_PROMPT
from config import BEDROCK_MODEL_ID, AWS_REGION, AWS_PROFILE, RECURSION_LIMIT

import boto3

logger = logging.getLogger("agent")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")


# ---------------------------------------------------------------------------
# Tool definitions (what the LLM sees as available tools)
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "rag_search",
            "description": (
                "Search the platform knowledge base for architecture docs, design decisions, "
                "runbooks, blog tutorials, and Confluence pages. Use this whenever the user "
                "asks about how something works, was designed, or should be configured."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query — rephrase the user's question for optimal retrieval",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of results to return (default 5)",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "assess_incident",
            "description": (
                "Triage an infrastructure incident by matching symptoms against known "
                "patterns in the knowledge base. Use when a user reports errors, outages, "
                "or unexpected behavior in any platform component."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "component": {
                        "type": "string",
                        "description": "The affected component, e.g. 'EventBridge', 'Lambda', 'Bedrock', 'Terraform', 'Lakehouse'",
                    },
                    "symptoms": {
                        "type": "string",
                        "description": "Description of the problem or error message",
                    },
                    "severity": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "critical"],
                        "description": "How urgent is this? Default: medium",
                        "default": "medium",
                    },
                },
                "required": ["component", "symptoms"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_checklist",
            "description": (
                "Create an action checklist for deployments, incident response, migrations, "
                "or onboarding. Persists to the database so it can be tracked over time."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Name of the checklist, e.g. 'EventBridge Migration Checklist'",
                    },
                    "items": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of action items to track",
                    },
                },
                "required": ["title", "items"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "escalate_to_human",
            "description": (
                "Escalate to a human engineer when the issue is novel, high-risk, "
                "requires production access, or you cannot confidently diagnose the problem."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Why this needs human review",
                    },
                    "conversation_summary": {
                        "type": "string",
                        "description": "Brief summary of the conversation and findings so far",
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "Urgency level",
                        "default": "medium",
                    },
                },
                "required": ["reason", "conversation_summary"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Tool execution registry
# ---------------------------------------------------------------------------

async def execute_tool(name: str, args: dict) -> tuple[str, list[dict]]:
    """Execute a tool by name. Returns (result_text, rag_results).
    
    rag_results is a list of source dicts only for rag_search calls.
    """
    if name == "rag_search":
        from tools.rag_tool import rag_search, format_context_for_llm
        result = await rag_search(
            query=args.get("query", ""),
            top_k=args.get("top_k", 5),
        )
        rag_results = [
            {"title": r["title"], "source_type": r["source_type"], "score": r["score"]}
            for r in result.results
        ] if result.success else []
        if result.success and result.results:
            return format_context_for_llm(result), rag_results
        return result.message, rag_results

    elif name == "assess_incident":
        from tools.incident_tool import assess_incident
        result = await assess_incident(
            component=args.get("component", ""),
            symptoms=args.get("symptoms", ""),
            severity=args.get("severity", "medium"),
        )
        return result.model_dump_json(indent=2), []

    elif name == "create_checklist":
        from tools.db_tool import create_checklist
        result = await create_checklist(
            title=args.get("title", "Untitled Checklist"),
            items=args.get("items", []),
        )
        return result.model_dump_json(indent=2), []

    elif name == "escalate_to_human":
        from tools.escalation_tool import escalate
        result = await escalate(
            reason=args.get("reason", ""),
            conversation_summary=args.get("conversation_summary", ""),
            priority=args.get("priority", "medium"),
        )
        return result.model_dump_json(indent=2), []

    return f"Unknown tool: {name}", []


# ---------------------------------------------------------------------------
# Graph nodes
# ---------------------------------------------------------------------------

def _get_llm():
    """Create a Bedrock Claude client via LangChain."""
    session = boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
    return ChatBedrockConverse(
        model=BEDROCK_MODEL_ID,
        client=session.client("bedrock-runtime"),
        max_tokens=4096,
        temperature=0.1,
    )


async def llm_node(state: AgentState) -> dict:
    """Call Claude with current messages and available tools."""
    llm = _get_llm()

    messages = list(state["messages"])
    if not messages or not isinstance(messages[0], SystemMessage):
        messages.insert(0, SystemMessage(content=SYSTEM_PROMPT))

    llm_with_tools = llm.bind_tools(TOOLS)

    start = time.time()
    response = await llm_with_tools.ainvoke(messages)
    latency = int((time.time() - start) * 1000)

    iteration = state.get("iteration_count", 0) + 1
    tool_names = [tc["name"] for tc in (response.tool_calls or [])]
    logger.info(f"LLM call #{iteration}: {latency}ms, tools={tool_names or 'none'}")

    return {
        "messages": [response],
        "iteration_count": iteration,
    }


async def tool_node(state: AgentState) -> dict:
    """Execute all tool calls from the last LLM response.

    For each tool_call in the AIMessage, run the tool and create
    a ToolMessage with the result. These get appended to messages
    so the LLM can see what the tools returned.
    """
    messages = state["messages"]
    last_message = messages[-1]

    tool_messages = []
    tool_log = list(state.get("tool_calls_log", []))

    for tool_call in last_message.tool_calls:
        name = tool_call["name"]
        args = tool_call["args"]
        tool_call_id = tool_call["id"]

        start = time.time()
        try:
            result_text, rag_results = await execute_tool(name, args)
        except Exception as e:
            result_text = f"Tool error: {str(e)}"
            rag_results = []
            logger.error(f"Tool {name} failed: {e}")
        latency_ms = int((time.time() - start) * 1000)

        logger.info(f"Tool {name}: {latency_ms}ms, output={len(result_text)} chars")

        tool_messages.append(
            ToolMessage(content=result_text, tool_call_id=tool_call_id)
        )
        log_entry = {
            "name": name,
            "input": args,
            "output_length": len(result_text),
            "latency_ms": latency_ms,
        }
        if rag_results:
            log_entry["rag_results"] = rag_results
        tool_log.append(log_entry)

    return {
        "messages": tool_messages,
        "tool_calls_log": tool_log,
    }


def should_continue(state: AgentState) -> str:
    """Decide if we should continue the loop or stop.

    Returns:
        "tools" — if the LLM wants to call tools
        "end"   — if the LLM gave a final response (or loop limit hit)
    """
    messages = state["messages"]
    last_message = messages[-1]

    # Loop protection
    iteration = state.get("iteration_count", 0)
    if iteration >= RECURSION_LIMIT:
        return "end"

    # If the last message has tool calls, execute them
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"

    return "end"


# ---------------------------------------------------------------------------
# Build the graph
# ---------------------------------------------------------------------------

def create_agent_graph():
    """Create and compile the LangGraph agent.

    Graph structure:
        START → router → [general_qa]: llm → [should_continue] → tools → llm → ... → END
                       → [eligibility]: gather_info → check_policy → [branch] → eligible/ineligible/uncertain → END

    The router classifies user intent first, then dispatches to the
    appropriate workflow sub-graph.
    """
    from agent.workflows.incident_triage import (
        gather_symptoms_node, search_docs_node, route_after_search,
        known_fix_node, investigate_node, escalate_node,
    )

    graph = StateGraph(AgentState)

    # --- Nodes ---
    graph.add_node("router", router_node)

    # General QA path (ReAct loop)
    graph.add_node("llm", llm_node)
    graph.add_node("tools", tool_node)

    # Incident triage workflow path
    graph.add_node("gather_symptoms", gather_symptoms_node)
    graph.add_node("search_docs", search_docs_node)
    graph.add_node("known_fix", known_fix_node)
    graph.add_node("investigate", investigate_node)
    graph.add_node("escalate_incident", escalate_node)

    # --- Edges ---
    graph.set_entry_point("router")

    # Router dispatches to workflow
    graph.add_conditional_edges(
        "router",
        lambda s: s.get("current_workflow", "general_qa"),
        {
            "general_qa": "llm",
            "incident_triage": "gather_symptoms",
        },
    )

    # General QA: ReAct loop
    graph.add_conditional_edges(
        "llm",
        should_continue,
        {"tools": "tools", "end": END},
    )
    graph.add_edge("tools", "llm")

    # Incident triage workflow: linear then branch
    graph.add_edge("gather_symptoms", "search_docs")
    graph.add_conditional_edges(
        "search_docs",
        route_after_search,
        {
            "known_fix": "known_fix",
            "investigate": "investigate",
            "escalate": "escalate_incident",
        },
    )
    graph.add_edge("known_fix", END)
    graph.add_edge("investigate", END)
    graph.add_edge("escalate_incident", END)

    return graph.compile()


async def router_node(state: AgentState) -> dict:
    """Classify user intent and route to the appropriate workflow.

    Uses a quick LLM call to determine if the user is asking about
    eligibility (→ structured workflow) or something else (→ general QA).
    """
    from agent.prompts import ROUTER_PROMPT

    messages = state["messages"]
    user_msg = ""
    for m in reversed(messages):
        if isinstance(m, HumanMessage):
            user_msg = m.content
            break

    llm = _get_llm()
    response = await llm.ainvoke([
        SystemMessage(content=ROUTER_PROMPT),
        HumanMessage(content=user_msg),
    ])

    # Content may be a string or list of content blocks
    raw = response.content
    if isinstance(raw, list):
        raw = "".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in raw
        )
    workflow = raw.strip().lower().replace(" ", "_")

    # Map router output to our supported workflows
    if workflow in ("incident_triage", "incident"):
        logger.info(f"Router → incident_triage (raw: {raw.strip()})")
        return {"current_workflow": "incident_triage"}
    else:
        logger.info(f"Router → general_qa (raw: {raw.strip()})")
        return {"current_workflow": "general_qa"}
