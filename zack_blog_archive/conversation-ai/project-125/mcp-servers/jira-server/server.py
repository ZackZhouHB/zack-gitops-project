#!/usr/bin/env python3
"""
Jira MCP Server — Project 125

Exposes Jira Cloud operations as MCP tools that any MCP-compatible agent can discover and call.

Tools exposed:
  - search_issues: Search Jira with JQL
  - create_ticket: Create a new Jira ticket
  - update_ticket: Update an existing ticket's fields
  - get_ticket: Get full details of a ticket
  - add_comment: Add a comment to a ticket

Transport: stdio (default) or streamable-http (--transport http --port 8002)

Usage:
  python server.py                          # stdio transport (for agent integration)
  python server.py --transport http         # HTTP transport (for testing/Docker)
"""

import os
import sys
import logging
from pathlib import Path

from dotenv import load_dotenv
from jira_client import JiraClient

# Load .env from project root (2 levels up from mcp-servers/jira-server/)
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

# ── Conditional import: use FastMCP if available, otherwise provide stub ──
try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("ERROR: MCP SDK not installed. Run: pip install mcp")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("jira-mcp")

# ── Initialize MCP Server ──
mcp = FastMCP("jira-server")

# ── Initialize Jira Client ──
jira = JiraClient(
    url=os.getenv("JIRA_URL", ""),
    email=os.getenv("JIRA_EMAIL", ""),
    api_token=os.getenv("JIRA_API_TOKEN", ""),
    default_project=os.getenv("JIRA_PROJECT_KEY", "PLAT"),
)


# ─────────────────────────────────────
# MCP Tools
# ─────────────────────────────────────

@mcp.tool()
def search_issues(jql: str, max_results: int = 10) -> dict:
    """Search Jira issues using JQL (Jira Query Language).

    Use this to find existing tickets, check for duplicates before creating new ones,
    or look up recent incidents. Always search before creating to avoid duplicates.

    Args:
        jql: JQL query string. Examples:
            - 'project = PLAT AND status = "Open"'
            - 'project = PLAT AND summary ~ "API latency" AND status != Done'
            - 'project = PLAT AND priority in (Highest, High) AND created >= -7d'
        max_results: Maximum number of results to return (default: 10, max: 50)

    Returns:
        dict with 'total' count and 'issues' list, each containing key, summary, status, priority, labels
    """
    logger.info(f"search_issues: jql={jql}, max_results={max_results}")
    max_results = min(max_results, 50)
    result = jira.search(jql=jql, max_results=max_results)
    logger.info(f"search_issues: found {result.get('total', 0)} results")
    return result


@mcp.tool()
def create_ticket(
    summary: str,
    description: str = "",
    issue_type: str = "Task",
    priority: str = "Medium",
    labels: list[str] | None = None,
    project_key: str | None = None,
) -> dict:
    """Create a new Jira ticket.

    IMPORTANT: Always search for duplicates with search_issues BEFORE creating a ticket.
    This tool should only be called AFTER human approval in production workflows.

    Args:
        summary: Ticket title (required). Be specific and descriptive.
        description: Ticket body text. Include context from KB search, root cause analysis, etc.
        issue_type: Jira issue type — 'Task', 'Bug', 'Story', or 'Epic' (default: Task)
        priority: Priority level — 'Highest', 'High', 'Medium', 'Low', 'Lowest' (default: Medium)
        labels: List of labels for categorisation. Always include 'agent-created'.
        project_key: Jira project key (default: from JIRA_PROJECT_KEY env var)

    Returns:
        dict with 'key' (e.g., 'PLAT-87'), 'id', and 'url' of the created ticket
    """
    if labels is None:
        labels = []
    if "agent-created" not in labels:
        labels.append("agent-created")

    project = project_key or jira.default_project
    logger.info(f"create_ticket: project={project}, summary={summary[:50]}...")

    result = jira.create_issue(
        project_key=project,
        summary=summary,
        description=description,
        issue_type=issue_type,
        priority=priority,
        labels=labels,
    )
    logger.info(f"create_ticket: created {result.get('key')}")
    return result


@mcp.tool()
def get_ticket(issue_key: str) -> dict:
    """Get full details of a Jira ticket.

    Args:
        issue_key: The Jira issue key (e.g., 'PLAT-87')

    Returns:
        dict with key, summary, status, priority, labels, description, comments count, created, updated
    """
    logger.info(f"get_ticket: {issue_key}")
    return jira.get_issue(issue_key)


@mcp.tool()
def update_ticket(
    issue_key: str,
    priority: str | None = None,
    labels: list[str] | None = None,
    summary: str | None = None,
) -> dict:
    """Update fields on an existing Jira ticket.

    This tool should only be called AFTER human approval in production workflows.

    Args:
        issue_key: The Jira issue key (e.g., 'PLAT-87')
        priority: New priority level (optional)
        labels: New labels list — replaces existing labels (optional)
        summary: New summary/title (optional)

    Returns:
        dict with 'success' boolean and 'issue_key'
    """
    fields = {}
    if priority:
        fields["priority"] = {"name": priority}
    if labels is not None:
        fields["labels"] = labels
    if summary:
        fields["summary"] = summary

    if not fields:
        return {"success": False, "error": "No fields to update"}

    logger.info(f"update_ticket: {issue_key}, fields={list(fields.keys())}")
    return jira.update_issue(issue_key, fields)


@mcp.tool()
def add_comment(issue_key: str, comment_text: str) -> dict:
    """Add a comment to an existing Jira ticket.

    Useful for adding agent analysis, KB search results, or status updates to tickets.
    This tool should only be called AFTER human approval in production workflows.

    Args:
        issue_key: The Jira issue key (e.g., 'PLAT-87')
        comment_text: The comment body text

    Returns:
        dict with 'success' boolean, 'comment_id', and 'issue_key'
    """
    logger.info(f"add_comment: {issue_key}")
    return jira.add_comment(issue_key, comment_text)


# ─────────────────────────────────────
# Entry Point
# ─────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Jira MCP Server")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--port", type=int, default=8002)
    args = parser.parse_args()

    if not jira.url:
        logger.error("JIRA_URL not set. Configure .env or environment variables.")
        sys.exit(1)

    logger.info(f"Starting Jira MCP Server (transport={args.transport})")
    if args.transport == "http":
        mcp.settings.host = "0.0.0.0"
        mcp.settings.port = args.port
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")
