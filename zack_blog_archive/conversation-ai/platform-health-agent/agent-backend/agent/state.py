"""Agent state definition — shared across all workflow nodes."""

from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """State passed through the LangGraph workflow.

    This is the central state object that all nodes read from and write to.
    LangGraph automatically manages message history via the add_messages reducer.
    """
    # Conversation — add_messages appends new messages (never overwrites)
    messages: Annotated[list, add_messages]

    # Workflow tracking
    current_workflow: str  # e.g., "general_qa", "eligibility_check"
    workflow_step: int
    workflow_status: str  # "in_progress", "completed", "escalated"

    # Workflow-specific data (set by gather nodes, read by branch nodes)
    workflow_data: dict  # e.g., {"component": "...", "symptoms": "..."}
    incident_result: dict  # Result from assess_incident

    # Tool tracking (observability)
    tool_calls_log: list[dict]  # Log of all tool invocations [{name, input, output, latency_ms}]
    iteration_count: int  # Loop protection counter
