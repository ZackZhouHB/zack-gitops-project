"""
LangGraph agent graph with Human-in-the-Loop — Project 125 Action Agent

Tools: RAG (Weaviate), Jira (REST API), Slack (Web API)
HITL: interrupt() pauses graph before write tools; resume via Command(resume=...)
Checkpointer: MemorySaver (in-memory, survives within process lifetime)

Graph flow:
  START -> llm -> should_continue -> tool_node -> llm -> ... -> END
                                        |
                                  (write tool detected)
                                        |
                                  interrupt() -> user approves/rejects -> execute/cancel
"""

import os
import sys
import json
import time
import logging
from pathlib import Path

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_aws import ChatBedrockConverse
from langgraph.graph import StateGraph, END
from langgraph.types import interrupt
from langgraph.checkpoint.memory import MemorySaver

from agent import AgentState
from agent.prompts import SYSTEM_PROMPT
from config import (
    BEDROCK_MODEL_ID, AWS_REGION, AWS_PROFILE, RECURSION_LIMIT, JIRA_PROJECT_KEY,
)

# Import MCP client modules — works in both Docker and local dev
try:
    # Docker: clients are copied to /app/clients/ by docker-compose
    from clients.jira_client import JiraClient
    from clients.slack_client import SlackClient
except ImportError:
    # Local dev: use sys.path to reach mcp-servers/
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "mcp-servers" / "jira-server"))
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "mcp-servers" / "slack-server"))
    from jira_client import JiraClient
    from slack_client import SlackClient

logger = logging.getLogger("agent.graph")

# Write tools that require human approval before execution
WRITE_TOOLS = {"create_ticket", "update_ticket", "add_comment", "send_message",
               "create_thread", "reply_in_thread", "send_rich_notification"}
READ_TOOLS = {"rag_search", "search_issues", "get_ticket", "list_channels", "web_search"}


def _create_llm():
    """Create Bedrock Claude LLM."""
    import boto3
    session = boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
    return ChatBedrockConverse(
        model=BEDROCK_MODEL_ID,
        region_name=AWS_REGION,
        credentials_profile_name=AWS_PROFILE,
        max_tokens=4096,
        temperature=0.1,
    )


def _create_jira_client() -> JiraClient:
    """Create Jira client from environment."""
    # In Docker: env vars injected by docker-compose. Local: load from .env file
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        from dotenv import load_dotenv
        load_dotenv(env_path)
    return JiraClient(
        url=os.getenv("JIRA_URL", ""),
        email=os.getenv("JIRA_EMAIL", ""),
        api_token=os.getenv("JIRA_API_TOKEN", ""),
        default_project=JIRA_PROJECT_KEY,
    )


def _create_slack_client() -> SlackClient:
    """Create Slack client from environment."""
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        from dotenv import load_dotenv
        load_dotenv(env_path)
    return SlackClient(
        bot_token=os.getenv("SLACK_BOT_TOKEN", ""),
        default_channel=os.getenv("SLACK_DEFAULT_CHANNEL", "#all-platform-health-lab"),
    )


def _build_tool_definitions() -> list[dict]:
    """Build Bedrock tool definitions for all available tools."""
    return [
        {
            "name": "rag_search",
            "description": (
                "Search the knowledge base for relevant documents about platform health topics. "
                "ALWAYS use this tool FIRST before taking any action. Returns past incidents, "
                "runbooks, architecture docs, and technical blog posts with relevance scores."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Natural language search query"},
                    "top_k": {"type": "integer", "description": "Number of results (default 5)", "default": 5},
                },
                "required": ["query"],
            },
        },
        {
            "name": "search_issues",
            "description": (
                "Search Jira issues using JQL query string. Use BEFORE creating tickets to "
                "check for duplicates. Example: 'project = SCRUM AND text ~ \"API latency\"'"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "jql": {"type": "string", "description": "JQL query (e.g., 'project = SCRUM AND status = Open')"},
                    "max_results": {"type": "integer", "description": "Max results (default 10)", "default": 10},
                },
                "required": ["jql"],
            },
        },
        {
            "name": "create_ticket",
            "description": (
                "Create a new Jira ticket. WRITE ACTION - requires human approval. "
                "Always search for duplicates FIRST using search_issues."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string", "description": "Ticket title"},
                    "description": {"type": "string", "description": "Detailed description"},
                    "priority": {"type": "string", "description": "Priority: Highest/High/Medium/Low/Lowest", "default": "Medium"},
                    "labels": {"type": "array", "items": {"type": "string"}, "description": "Labels to add"},
                },
                "required": ["summary"],
            },
        },
        {
            "name": "get_ticket",
            "description": "Get details of a specific Jira ticket by its key (e.g., SCRUM-42).",
            "parameters": {
                "type": "object",
                "properties": {
                    "issue_key": {"type": "string", "description": "Jira issue key (e.g., SCRUM-42)"},
                },
                "required": ["issue_key"],
            },
        },
        {
            "name": "update_ticket",
            "description": (
                "Update fields on an existing Jira ticket. WRITE ACTION - requires human approval."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "issue_key": {"type": "string", "description": "Jira issue key"},
                    "summary": {"type": "string", "description": "New summary (optional)"},
                    "priority": {"type": "string", "description": "New priority (optional)"},
                    "labels": {"type": "array", "items": {"type": "string"}, "description": "New labels (optional)"},
                },
                "required": ["issue_key"],
            },
        },
        {
            "name": "add_comment",
            "description": (
                "Add a comment to an existing Jira ticket. WRITE ACTION - requires human approval."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "issue_key": {"type": "string", "description": "Jira issue key"},
                    "comment_text": {"type": "string", "description": "Comment body in plain text"},
                },
                "required": ["issue_key", "comment_text"],
            },
        },
        {
            "name": "send_message",
            "description": (
                "Send a message to a Slack channel. WRITE ACTION - requires human approval."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "channel": {"type": "string", "description": "Channel name (e.g., #all-platform-health-lab)"},
                    "text": {"type": "string", "description": "Message text (supports mrkdwn)"},
                    "thread_ts": {"type": "string", "description": "Thread timestamp for replies (optional)"},
                },
                "required": ["channel", "text"],
            },
        },
        {
            "name": "create_thread",
            "description": (
                "Create a new Slack thread: posts a summary, then adds details as a reply. "
                "WRITE ACTION - requires human approval."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "channel": {"type": "string", "description": "Channel name"},
                    "summary": {"type": "string", "description": "Thread-starting message"},
                    "details": {"type": "string", "description": "Detailed reply in thread"},
                },
                "required": ["channel", "summary", "details"],
            },
        },
        {
            "name": "reply_in_thread",
            "description": (
                "Reply to an existing Slack thread. WRITE ACTION - requires human approval."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "channel": {"type": "string", "description": "Channel name"},
                    "text": {"type": "string", "description": "Reply text"},
                    "thread_ts": {"type": "string", "description": "Thread timestamp to reply to"},
                },
                "required": ["channel", "text", "thread_ts"],
            },
        },
        {
            "name": "list_channels",
            "description": "List all Slack channels the bot is a member of.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
        {
            "name": "send_rich_notification",
            "description": (
                "Send a rich Slack notification with Block Kit formatting (headers, fields, "
                "buttons, context). WRITE ACTION - requires human approval."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "channel": {"type": "string", "description": "Channel name"},
                    "title": {"type": "string", "description": "Notification header"},
                    "fields": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "label": {"type": "string"},
                                "value": {"type": "string"},
                            },
                        },
                        "description": "Key-value fields to display",
                    },
                    "text": {"type": "string", "description": "Body text (optional)"},
                    "color": {"type": "string", "description": "Sidebar color: good/warning/danger/#hex"},
                },
                "required": ["channel", "title"],
            },
        },
        {
            "name": "web_search",
            "description": (
                "Search the internet using DuckDuckGo for real-time, up-to-date information. "
                "Use this when the internal knowledge base (rag_search) does not have the answer, "
                "or when the question requires current information like latest versions, recent "
                "outages, CVEs, release notes, or external documentation not in our KB."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query (natural language or keywords)"},
                    "max_results": {"type": "integer", "description": "Number of results (default 5)", "default": 5},
                },
                "required": ["query"],
            },
        },
    ]


async def _execute_tool(
    tool_name: str,
    tool_args: dict,
    jira: JiraClient,
    slack: SlackClient,
) -> dict:
    """Execute a tool by name and return the result."""
    start = time.time()

    try:
        if tool_name == "rag_search":
            from tools.rag_tool import rag_search
            result = await rag_search(**tool_args)
            return result.model_dump()

        elif tool_name == "search_issues":
            return jira.search(**tool_args)

        elif tool_name == "create_ticket":
            labels = tool_args.get("labels", [])
            if "agent-created" not in labels:
                labels.append("agent-created")
            return jira.create_issue(
                project_key=jira.default_project,
                summary=tool_args["summary"],
                description=tool_args.get("description", ""),
                issue_type="Task",
                priority=tool_args.get("priority", "Medium"),
                labels=labels,
            )

        elif tool_name == "get_ticket":
            return jira.get_issue(tool_args["issue_key"])

        elif tool_name == "update_ticket":
            fields = {}
            if "priority" in tool_args and tool_args["priority"]:
                fields["priority"] = {"name": tool_args["priority"]}
            if "labels" in tool_args:
                fields["labels"] = tool_args["labels"]
            if "summary" in tool_args and tool_args["summary"]:
                fields["summary"] = tool_args["summary"]
            return jira.update_issue(tool_args["issue_key"], fields)

        elif tool_name == "add_comment":
            return jira.add_comment(tool_args["issue_key"], tool_args["comment_text"])

        elif tool_name == "send_message":
            return slack.post_message(**tool_args)

        elif tool_name == "create_thread":
            main = slack.post_message(channel=tool_args["channel"], text=tool_args["summary"])
            if not main.get("success"):
                return main
            reply = slack.post_message(
                channel=main["channel"], text=tool_args["details"], thread_ts=main["ts"]
            )
            return {"success": True, "message_ts": main["ts"], "thread_ts": reply.get("ts", "")}

        elif tool_name == "reply_in_thread":
            return slack.post_message(**tool_args)

        elif tool_name == "list_channels":
            return slack.list_channels()

        elif tool_name == "send_rich_notification":
            return slack.post_rich_message(**tool_args)

        elif tool_name == "web_search":
            from tools.web_search import web_search
            return await web_search(**tool_args)

        else:
            return {"error": f"Unknown tool: {tool_name}"}

    except Exception as e:
        logger.error(f"Tool {tool_name} failed: {e}")
        return {"error": str(e), "tool": tool_name}


def create_agent_graph():
    """Build the LangGraph agent with HITL support.

    Write tools trigger interrupt() which pauses the graph.
    The caller resumes with Command(resume={"decision": "approve"|"reject"|"edit", ...}).
    """
    llm = _create_llm()
    jira = _create_jira_client()
    slack = _create_slack_client()
    tool_defs = _build_tool_definitions()
    checkpointer = MemorySaver()

    # -- Graph Nodes --

    async def llm_node(state: AgentState) -> dict:
        """Call Claude with system prompt and tool definitions."""
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
        iteration = state.get("iteration_count", 0) + 1

        if iteration > RECURSION_LIMIT:
            return {
                "messages": [AIMessage(content="I've reached the maximum number of steps. Please simplify your request.")],
                "iteration_count": iteration,
            }

        response = await llm.ainvoke(messages, tools=tool_defs)
        return {"messages": [response], "iteration_count": iteration}

    async def tool_node(state: AgentState) -> dict:
        """Execute tool calls — interrupt() before any write tools for human approval."""
        last_message = state["messages"][-1]
        tool_calls_log = list(state.get("tool_calls_log", []))
        new_messages = []

        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            tool_id = tool_call["id"]
            is_write = tool_name in WRITE_TOOLS

            logger.info(f"Tool requested: {tool_name}({json.dumps(tool_args)[:200]})")

            # HITL: interrupt before write tools
            if is_write:
                logger.info(f"HITL: Requesting approval for write tool '{tool_name}'")
                approval = interrupt({
                    "tool": tool_name,
                    "args": tool_args,
                    "is_write": True,
                    "message": f"Approve this action? Tool: {tool_name}",
                })

                # interrupt() returns the resume value from Command(resume=...)
                decision = approval.get("decision", "reject") if isinstance(approval, dict) else str(approval)

                if decision == "reject":
                    logger.info(f"HITL: User REJECTED '{tool_name}'")
                    result_str = json.dumps({"status": "rejected", "message": "Action rejected by user"})
                    tool_calls_log.append({
                        "tool": tool_name,
                        "args": tool_args,
                        "result_preview": result_str,
                        "latency_ms": 0,
                        "is_write": True,
                        "approval": "rejected",
                    })
                    new_messages.append(
                        ToolMessage(content=result_str, tool_call_id=tool_id, name=tool_name)
                    )
                    continue

                if decision == "edit":
                    edited_args = approval.get("edited_args", tool_args)
                    logger.info(f"HITL: User EDITED '{tool_name}' args")
                    tool_args = edited_args

                logger.info(f"HITL: User APPROVED '{tool_name}' — executing")

            # Execute the tool
            start = time.time()
            result = await _execute_tool(tool_name, tool_args, jira, slack)
            latency_ms = int((time.time() - start) * 1000)
            result_str = json.dumps(result, default=str)

            log_entry = {
                "tool": tool_name,
                "args": tool_args,
                "result_preview": result_str[:500],
                "latency_ms": latency_ms,
                "is_write": is_write,
                "success": "error" not in result,
            }
            if is_write:
                log_entry["approval"] = "approved"
            if tool_name == "rag_search" and result.get("results"):
                log_entry["rag_results"] = result["results"]

            tool_calls_log.append(log_entry)
            new_messages.append(
                ToolMessage(content=result_str, tool_call_id=tool_id, name=tool_name)
            )

        return {"messages": new_messages, "tool_calls_log": tool_calls_log}

    def should_continue(state: AgentState) -> str:
        """Decide whether to continue the ReAct loop or end."""
        last_message = state["messages"][-1]

        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return "end"

    # -- Build Graph --
    graph = StateGraph(AgentState)

    graph.add_node("llm", llm_node)
    graph.add_node("tools", tool_node)

    graph.set_entry_point("llm")

    graph.add_conditional_edges("llm", should_continue, {
        "tools": "tools",
        "end": END,
    })
    graph.add_edge("tools", "llm")

    return graph.compile(checkpointer=checkpointer), checkpointer
