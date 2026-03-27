#!/usr/bin/env python3
"""
Slack MCP Server — Project 125

Exposes Slack messaging operations as MCP tools that any MCP-compatible agent can discover and call.

Tools exposed:
  - send_message: Send a message to a Slack channel
  - create_thread: Send a message and start a discussion thread
  - reply_in_thread: Reply to an existing message thread
  - list_channels: List available channels (bot must be a member)

Transport: stdio (default) or streamable-http (--transport http --port 8003)

Usage:
  python server.py                          # stdio transport (for agent integration)
  python server.py --transport http         # HTTP transport (for testing/Docker)
"""

import os
import sys
import logging
from pathlib import Path

from dotenv import load_dotenv
from slack_client import SlackClient

# Load .env from project root
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("ERROR: MCP SDK not installed. Run: pip install mcp")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("slack-mcp")

# ── Initialize MCP Server ──
mcp = FastMCP("slack-server")

# ── Initialize Slack Client ──
slack = SlackClient(
    bot_token=os.getenv("SLACK_BOT_TOKEN", ""),
    default_channel=os.getenv("SLACK_DEFAULT_CHANNEL", "#platform-alerts"),
)


# ─────────────────────────────────────
# MCP Tools
# ─────────────────────────────────────

@mcp.tool()
def send_message(channel: str, text: str) -> dict:
    """Send a message to a Slack channel.

    Use this to notify teams about incidents, ticket creation, or status updates.
    The bot must be a member of the target channel.
    This tool should only be called AFTER human approval in production workflows.

    Args:
        channel: Channel name (e.g., '#platform-alerts') or channel ID (e.g., 'C0123ABCD').
        text: Message text. Supports Slack mrkdwn formatting:
            - *bold*, _italic_, ~strikethrough~
            - `code`, ```code block```
            - Bullet lists with •

    Returns:
        dict with 'success', 'channel', 'ts' (message timestamp/ID), and 'message' on error
    """
    logger.info(f"send_message: channel={channel}, text_len={len(text)}")
    result = slack.post_message(channel=channel, text=text)
    logger.info(f"send_message: success={result.get('success')}")
    return result


@mcp.tool()
def create_thread(channel: str, summary: str, details: str) -> dict:
    """Send a summary message to a channel, then add details as a thread reply.

    This is the recommended pattern for incident notifications:
    - Main message: brief summary (visible in channel)
    - Thread reply: detailed context from KB, root cause, actions (keeps channel clean)

    This tool should only be called AFTER human approval in production workflows.

    Args:
        channel: Channel name or ID
        summary: Main message text — keep it brief (1-2 lines). This is what everyone sees.
        details: Thread reply text — include KB context, root cause, suggested actions, links.

    Returns:
        dict with 'success', 'channel', 'message_ts' (main message), 'thread_ts' (reply)
    """
    logger.info(f"create_thread: channel={channel}")

    # Post summary as main message
    main_result = slack.post_message(channel=channel, text=summary)
    if not main_result.get("success"):
        return main_result

    # Post details as thread reply
    thread_result = slack.post_message(
        channel=main_result["channel"],
        text=details,
        thread_ts=main_result["ts"],
    )

    return {
        "success": thread_result.get("success", False),
        "channel": main_result["channel"],
        "message_ts": main_result["ts"],
        "thread_ts": thread_result.get("ts", ""),
    }


@mcp.tool()
def reply_in_thread(channel: str, thread_ts: str, text: str) -> dict:
    """Reply to an existing message thread.

    Use this to add follow-up information to an ongoing incident thread.

    Args:
        channel: Channel name or ID
        thread_ts: Timestamp of the parent message (returned by send_message or create_thread)
        text: Reply text

    Returns:
        dict with 'success', 'channel', 'ts' (reply timestamp)
    """
    logger.info(f"reply_in_thread: channel={channel}, thread_ts={thread_ts}")
    return slack.post_message(channel=channel, text=text, thread_ts=thread_ts)


@mcp.tool()
def list_channels() -> dict:
    """List Slack channels that the bot is a member of.

    Use this to discover available channels before sending messages.
    Only channels where the bot has been added will be listed.

    Returns:
        dict with 'channels' list, each containing 'id', 'name', 'is_member', 'num_members'
    """
    logger.info("list_channels")
    return slack.list_channels()


@mcp.tool()
def send_rich_notification(
    channel: str,
    title: str,
    fields: dict,
    context_text: str = "",
    jira_url: str = "",
) -> dict:
    """Send a richly formatted incident notification using Slack Block Kit.

    Creates a professional-looking notification card with structured fields,
    optional context, and action buttons.

    This tool should only be called AFTER human approval in production workflows.

    Args:
        channel: Channel name or ID
        title: Notification header (e.g., '🎫 PLAT-87: API Latency Spike')
        fields: Key-value pairs to display in two columns.
            Example: {"Priority": "P2 — High", "Status": "Open", "Component": "API Gateway"}
        context_text: Additional context text (e.g., root cause from KB search)
        jira_url: Optional URL to the Jira ticket (adds a 'View in Jira' button)

    Returns:
        dict with 'success', 'channel', 'ts'
    """
    logger.info(f"send_rich_notification: channel={channel}, title={title}")
    return slack.post_rich_message(
        channel=channel,
        title=title,
        fields=fields,
        context_text=context_text,
        jira_url=jira_url,
    )


# ─────────────────────────────────────
# Entry Point
# ─────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Slack MCP Server")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--port", type=int, default=8003)
    args = parser.parse_args()

    if not slack.bot_token:
        logger.error("SLACK_BOT_TOKEN not set. Configure .env or environment variables.")
        sys.exit(1)

    logger.info(f"Starting Slack MCP Server (transport={args.transport})")
    if args.transport == "http":
        mcp.settings.host = "0.0.0.0"
        mcp.settings.port = args.port
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")
