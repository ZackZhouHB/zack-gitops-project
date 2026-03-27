"""Agent state definition for Project 125 action agent."""

from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """State shared across all nodes in the agent graph.

    Fields:
        messages: Conversation history (LangGraph reducer appends automatically)
        tool_calls_log: Track all tool calls for observability and source citations
        iteration_count: Loop protection — fail after max iterations
        pending_approval: When set, agent is paused waiting for human approval
        approval_response: Human's decision after reviewing proposed action
    """
    messages: Annotated[list, add_messages]
    tool_calls_log: list[dict]
    iteration_count: int
    pending_approval: dict | None  # Proposed action awaiting approval
    approval_response: dict | None  # User's approve/edit/reject response
