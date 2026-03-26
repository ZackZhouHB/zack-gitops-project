"""LangGraph agent graph — the agentic brain (AWS ECS deployment).

Adapted from the local development version for AWS ECS deployment.

Key AWS adaptations:
- No AWS_PROFILE — ECS task roles provide credentials automatically via
  the container credential provider chain (no explicit profile needed).
- kb_search (Bedrock Knowledge Base) replaces rag_search (local FAISS).
- DynamoDB tool replaces local SQLite db_tool.
- KB search results include source_uri for S3/web provenance tracking.

Architecture: Single ReAct loop (no router).
    START → llm → [should_continue] → tools → llm → ... → END

The LLM decides which tools to call based on tool descriptions.
Vector search handles content routing — no need for a separate router.
"""

import json
import time
import logging
from langchain_core.messages import AIMessage, ToolMessage, SystemMessage, HumanMessage
from langchain_aws import ChatBedrockConverse
from langgraph.graph import StateGraph, END

from agent.state import AgentState
from agent.prompts import SYSTEM_PROMPT

# AWS ECS config — no AWS_PROFILE needed; ECS task role provides credentials
from config import BEDROCK_MODEL_ID, AWS_REGION, RECURSION_LIMIT

import boto3

logger = logging.getLogger("agent")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")


# ---------------------------------------------------------------------------
# Tool definitions (what the LLM sees as available tools)
# Tool descriptions ARE the routing logic — they tell the LLM when to use each.
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "rag_search",
            "description": (
                "Search the platform knowledge base for ANY information. This covers: "
                "infrastructure docs (Terraform, AWS, Azure AD), technical blog posts "
                "(EKS, Karpenter, CI/CD, Bedrock, Istio), personal blog stories, "
                "Confluence design documents (Health Analyzer, pipeline design, POC proposals), "
                "and uploaded PDFs. ALWAYS use this tool first before answering any question. "
                "When in doubt, search. Multiple searches with different queries are encouraged."
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
                "ONLY use when the user reports a SPECIFIC, ACTIVE infrastructure problem: "
                "service outage, error spike, deployment failure, or performance degradation. "
                "Do NOT use for general questions, lookups, or 'can you check' requests. "
                "Examples: 'our API returns 500 errors', 'EKS nodes not scaling', 'Lambda timeout'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "component": {
                        "type": "string",
                        "description": "The affected component, e.g. 'EventBridge', 'Lambda', 'Bedrock'",
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
                "or onboarding. Persists to the database so it can be tracked over time. "
                "Only use when the user explicitly asks for a checklist or action plan."
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
# AWS adaptations:
#   - kb_search (Bedrock KB) replaces rag_search (local FAISS)
#   - dynamodb_tool replaces db_tool (DynamoDB instead of SQLite)
#   - KB results include source_uri for S3/web document provenance
# ---------------------------------------------------------------------------

async def execute_tool(name: str, args: dict) -> tuple[str, list[dict]]:
    """Execute a tool by name. Returns (result_text, rag_results).

    rag_results is a list of source dicts only for rag_search calls.
    """
    if name == "rag_search":
        # AWS: Bedrock Knowledge Base search replaces local FAISS-based rag_search
        from tools.kb_tool import kb_search, format_context_for_llm
        result = await kb_search(
            query=args.get("query", ""),
            top_k=args.get("top_k", 5),
        )
        # Include source_uri for S3/web provenance tracking in AWS deployment
        rag_results = [
            {
                "title": r.title,
                "source_type": r.source_type,
                "score": r.score,
                "source_uri": r.source_uri,
            }
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
        # AWS: DynamoDB replaces local SQLite for persistent checklist storage
        from tools.dynamodb_tool import create_checklist
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
    """Create a Bedrock Claude client via LangChain.

    AWS ECS adaptation: no profile_name — the ECS task role provides
    credentials automatically through the container credential chain.
    """
    session = boto3.Session(region_name=AWS_REGION)
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

    Simplified graph — single ReAct loop, no router:
        START → llm → [should_continue] → tools → llm → ... → END

    The LLM decides which tools to call based on tool descriptions.
    Vector search in the KB handles content routing naturally.
    """
    graph = StateGraph(AgentState)

    # Nodes
    graph.add_node("llm", llm_node)
    graph.add_node("tools", tool_node)

    # Entry point — go straight to LLM (no router)
    graph.set_entry_point("llm")

    # ReAct loop: LLM → tools → LLM → ... → END
    graph.add_conditional_edges(
        "llm",
        should_continue,
        {"tools": "tools", "end": END},
    )
    graph.add_edge("tools", "llm")

    return graph.compile()


