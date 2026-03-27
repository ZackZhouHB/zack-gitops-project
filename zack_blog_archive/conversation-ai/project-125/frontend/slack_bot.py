"""
Slack Bot Entry Point — Triggers the Agent directly from Slack

How it works:
  1. User types "@platform_health_bot investigate API latency" in Slack
  2. Bot receives the message via Socket Mode (WebSocket — no public URL needed)
  3. Bot calls Agent API (localhost:8010/chat)
  4. If the agent wants to do a write action → shows Approve/Reject buttons in Slack
  5. User clicks a button → Bot calls /approve or /reject
  6. Agent executes (or cancels) and bot posts the result

Setup:
  1. Go to https://api.slack.com/apps → your app → Socket Mode → Enable
  2. Generate an App-Level Token (xapp-...) with connections:write scope
  3. Add to .env: SLACK_APP_TOKEN=xapp-...
  4. Go to Event Subscriptions → Enable → Subscribe to: app_mention, message.im
  5. Go to Interactivity & Shortcuts → Enable (Socket Mode handles the URL)

Run:
  cd project-125 && source .venv/bin/activate
  # Terminal 1: Agent backend
  cd agent-backend && python main.py
  # Terminal 2: Slack bot
  python frontend/slack_bot.py
"""

import os
import sys
import json
import logging
import requests
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("slack_bot")

AGENT_URL = os.getenv("AGENT_URL", "http://localhost:8010")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")

if not SLACK_BOT_TOKEN:
    print("❌ Missing SLACK_BOT_TOKEN in .env")
    sys.exit(1)
if not SLACK_APP_TOKEN:
    print("❌ Missing SLACK_APP_TOKEN in .env")
    print("   To get one:")
    print("   1. Go to https://api.slack.com/apps → your app")
    print("   2. Click 'Socket Mode' in sidebar → Enable")
    print("   3. Click 'Generate' to create an App-Level Token")
    print("   4. Name it 'socket-mode', scope: connections:write")
    print("   5. Add to .env: SLACK_APP_TOKEN=xapp-1-...")
    sys.exit(1)

app = App(token=SLACK_BOT_TOKEN)


# ── Helper: Call Agent API ──

def call_agent(message: str, conversation_id: str = None) -> dict:
    """Send a message to the agent backend."""
    try:
        payload = {"message": message}
        if conversation_id:
            payload["conversation_id"] = conversation_id
        r = requests.post(f"{AGENT_URL}/chat", json=payload, timeout=120)
        return r.json()
    except requests.exceptions.ConnectionError:
        return {"error": "Agent not running. Start: cd agent-backend && python main.py"}
    except Exception as e:
        return {"error": str(e)}


def approve_agent(thread_id: str) -> dict:
    try:
        r = requests.post(f"{AGENT_URL}/chat/{thread_id}/approve", timeout=60)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def reject_agent(thread_id: str) -> dict:
    try:
        r = requests.post(f"{AGENT_URL}/chat/{thread_id}/reject", timeout=30)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


# ── Helper: Format Slack Blocks ──

def format_tool_badges(tool_calls: list) -> str:
    """Format tool calls as a readable line."""
    badges = []
    for tc in tool_calls:
        tool = tc.get("tool", "?")
        is_write = tc.get("is_write", False)
        approval = tc.get("approval", "")
        icon = "🔴" if approval == "rejected" else "🟢" if approval == "approved" else "🔵" if not is_write else "🟠"
        label = f"{icon} {tool}"
        if approval:
            label += f" ({approval})"
        latency = tc.get("latency_ms", "")
        if latency:
            label += f" {latency}ms"
        badges.append(label)
    return " | ".join(badges) if badges else ""


def build_response_blocks(data: dict) -> list:
    """Build Slack Block Kit blocks for agent response."""
    blocks = []

    # Response text — hard cap at 1500 chars for Slack message limits
    response = data.get("response", "")
    if response:
        truncated = response[:1500]
        if len(response) > 1500:
            truncated += "\n\n_...truncated. Full answer on Streamlit :8502_"
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": truncated}
        })

    # Tool calls
    tool_text = format_tool_badges(data.get("tool_calls", []))
    if tool_text:
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"🔧 *Tools*: {tool_text}"}]
        })

    # Sources
    sources = data.get("sources", [])
    if sources:
        source_lines = [f"• {s.get('title','?')} ({s.get('source_type','?')}) — {s.get('score',0):.0%}" for s in sources[:5]]
        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": "📚 *Sources*:\n" + "\n".join(source_lines)}]
        })

    # Latency
    latency = data.get("latency_ms")
    if latency:
        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"⏱️ {latency}ms"}]
        })

    return blocks


def build_approval_blocks(data: dict) -> list:
    """Build Slack blocks for HITL approval prompt."""
    action = data.get("pending_action", {})
    tool = action.get("tool", "unknown")
    args = action.get("args", {})
    thread_id = data.get("conversation_id", "")

    blocks = []

    # First show any partial response from the agent
    response = data.get("response", "")
    if response:
        for i in range(0, min(len(response), 2900), 2900):
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": response[i:i+2900]}
            })

    blocks.append({"type": "divider"})

    # Approval header
    blocks.append({
        "type": "header",
        "text": {"type": "plain_text", "text": f"⏸️ Approval Required: {tool}"}
    })

    # Action details
    if tool == "create_ticket":
        detail = f"*Summary*: {args.get('summary', '?')}\n*Priority*: {args.get('priority', '?')}"
        if args.get("labels"):
            detail += f"\n*Labels*: {', '.join(args['labels'])}"
    elif tool in ("send_message", "create_thread"):
        detail = f"*Channel*: {args.get('channel', '?')}\n*Message*: {args.get('text', args.get('summary', '?'))[:300]}"
    elif tool == "add_comment":
        detail = f"*Ticket*: {args.get('issue_key', '?')}\n*Comment*: {args.get('comment_text', '?')[:300]}"
    elif tool == "send_rich_notification":
        detail = f"*Channel*: {args.get('channel', '?')}\n*Title*: {args.get('title', '?')}"
    else:
        detail = f"```{json.dumps(args, indent=2)[:500]}```"

    blocks.append({
        "type": "section",
        "text": {"type": "mrkdwn", "text": detail}
    })

    # Approve / Reject buttons
    blocks.append({
        "type": "actions",
        "block_id": "approval_actions",
        "elements": [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "✅ Approve"},
                "style": "primary",
                "action_id": "approve_action",
                "value": thread_id,
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "❌ Reject"},
                "style": "danger",
                "action_id": "reject_action",
                "value": thread_id,
            },
        ]
    })

    return blocks


# ── Event Handlers ──

@app.event("app_mention")
def handle_mention(event, say, client):
    """Handle @bot mentions in channels."""
    text = event.get("text", "")
    user = event.get("user", "")
    channel = event.get("channel", "")

    # Strip the bot mention from the text
    # Format: <@U12345> the actual message
    import re
    clean_text = re.sub(r"<@[A-Z0-9]+>\s*", "", text).strip()

    if not clean_text:
        say(
            text="👋 Hi! Tell me what you need. Examples:\n"
                 "• `@bot search for EKS tickets`\n"
                 "• `@bot create a ticket for API latency`\n"
                 "• `@bot what's our EKS RAG architecture?`",
            thread_ts=event.get("ts"),
        )
        return

    logger.info(f"Mention from {user} in {channel}: {clean_text[:100]}")

    # Send thinking indicator
    thinking = say(text="🤔 Thinking...", thread_ts=event.get("ts"))

    # Call agent
    data = call_agent(clean_text)

    if "error" in data:
        client.chat_update(
            channel=channel,
            ts=thinking["ts"],
            text=f"❌ {data['error']}",
        )
        return

    if data.get("status") == "pending_approval":
        # HITL: Show approval buttons
        blocks = build_approval_blocks(data)
        client.chat_update(
            channel=channel,
            ts=thinking["ts"],
            text="Action requires approval",
            blocks=blocks,
        )
    else:
        # Complete: Show response
        blocks = build_response_blocks(data)
        fallback = data.get("response", "Done.")[:500]
        try:
            client.chat_update(
                channel=channel,
                ts=thinking["ts"],
                text=fallback,
                blocks=blocks,
            )
        except Exception as e:
            # If blocks still too long, send text-only
            logger.warning(f"Block message failed ({e}), falling back to text-only")
            client.chat_update(
                channel=channel,
                ts=thinking["ts"],
                text=fallback,
            )


@app.event("message")
def handle_dm(event, say, client):
    """Handle direct messages to the bot."""
    # Only handle DMs (channel type "im"), skip bot messages
    if event.get("channel_type") != "im":
        return
    if event.get("bot_id"):
        return

    text = event.get("text", "").strip()
    if not text:
        return

    user = event.get("user", "")
    channel = event.get("channel", "")

    logger.info(f"DM from {user}: {text[:100]}")

    thinking = say(text="🤔 Thinking...")

    data = call_agent(text)

    if "error" in data:
        client.chat_update(channel=channel, ts=thinking["ts"], text=f"❌ {data['error']}")
        return

    if data.get("status") == "pending_approval":
        blocks = build_approval_blocks(data)
        client.chat_update(
            channel=channel, ts=thinking["ts"],
            text="Action requires approval", blocks=blocks,
        )
    else:
        blocks = build_response_blocks(data)
        fallback = data.get("response", "Done.")[:500]
        try:
            client.chat_update(
                channel=channel, ts=thinking["ts"],
                text=fallback, blocks=blocks,
            )
        except Exception as e:
            logger.warning(f"Block message failed ({e}), falling back to text-only")
            client.chat_update(
                channel=channel, ts=thinking["ts"],
                text=fallback,
            )


# ── Button Handlers ──

@app.action("approve_action")
def handle_approve(ack, body, client):
    """Handle the Approve button click."""
    ack()
    thread_id = body["actions"][0]["value"]
    channel = body["channel"]["id"]
    user = body["user"]["id"]
    message_ts = body["message"]["ts"]

    logger.info(f"APPROVE from {user} for thread {thread_id}")

    # Update the message to show it's being processed
    client.chat_update(
        channel=channel, ts=message_ts,
        text="⏳ Executing approved action...",
        blocks=[{"type": "section", "text": {"type": "mrkdwn", "text": "⏳ *Executing approved action...*"}}],
    )

    data = approve_agent(thread_id)

    if "error" in data:
        client.chat_update(
            channel=channel, ts=message_ts,
            text=f"❌ Error: {data['error']}",
        )
        return

    if data.get("status") == "pending_approval":
        # Another write action pending
        blocks = build_approval_blocks(data)
        client.chat_update(
            channel=channel, ts=message_ts,
            text="Another action requires approval", blocks=blocks,
        )
    else:
        # Done
        blocks = [
            {"type": "section", "text": {"type": "mrkdwn", "text": f"✅ *Approved by <@{user}>*"}},
            {"type": "divider"},
        ] + build_response_blocks(data)

        client.chat_update(
            channel=channel, ts=message_ts,
            text=data.get("response", "Action completed.")[:3000],
            blocks=blocks,
        )


@app.action("reject_action")
def handle_reject(ack, body, client):
    """Handle the Reject button click."""
    ack()
    thread_id = body["actions"][0]["value"]
    channel = body["channel"]["id"]
    user = body["user"]["id"]
    message_ts = body["message"]["ts"]

    logger.info(f"REJECT from {user} for thread {thread_id}")

    data = reject_agent(thread_id)

    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text": f"❌ *Rejected by <@{user}>*"}},
        {"type": "divider"},
    ] + build_response_blocks(data)

    client.chat_update(
        channel=channel, ts=message_ts,
        text=data.get("response", "Action rejected.")[:3000],
        blocks=blocks,
    )


# ── Main ──

if __name__ == "__main__":
    # Check agent health
    try:
        r = requests.get(f"{AGENT_URL}/health", timeout=3)
        health = r.json()
        print(f"✅ Agent backend: {health['status']} | HITL: {health['hitl_enabled']} | Tools: {len(health['tools'])}")
    except Exception:
        print(f"⚠️  Agent backend not running at {AGENT_URL}")
        print(f"   Start it first: cd agent-backend && python main.py")

    print()
    print("🤖 Starting Slack bot (Socket Mode)...")
    print("   Listening for @mentions and DMs")
    print("   Ctrl+C to stop")
    print()

    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()
