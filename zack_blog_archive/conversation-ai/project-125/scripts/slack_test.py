#!/usr/bin/env python3
"""
Slack API Test Script — Project 125 Phase B

Tests messaging operations against Slack Web API.
Run: python scripts/slack_test.py

Prerequisites:
  - Slack workspace created
  - Bot app created with scopes: chat:write, channels:read, channels:history
  - Bot installed to workspace and added to channels
  - .env file with SLACK_BOT_TOKEN, SLACK_DEFAULT_CHANNEL
"""

import os
import sys
import json
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(Path(__file__).parent.parent / ".env")

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")  # xoxb-...
SLACK_DEFAULT_CHANNEL = os.getenv("SLACK_DEFAULT_CHANNEL", "#platform-alerts")
SLACK_API_BASE = "https://slack.com/api"


def get_headers() -> dict:
    """Auth header for Slack Web API."""
    return {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json; charset=utf-8",
    }


def check_config():
    """Verify required environment variables."""
    if not SLACK_BOT_TOKEN:
        print("❌ Missing SLACK_BOT_TOKEN in .env")
        print("   Create a Slack app, install to workspace, copy Bot User OAuth Token.")
        sys.exit(1)
    print(f"✅ Config loaded: token starts with {SLACK_BOT_TOKEN[:10]}...")
    print(f"   Default channel: {SLACK_DEFAULT_CHANNEL}")


# ─────────────────────────────────────
# Test 1: Auth Test
# ─────────────────────────────────────
def test_auth():
    """Verify the bot token is valid."""
    print("\n── Test 1: Auth Test ──")
    resp = requests.post(f"{SLACK_API_BASE}/auth.test", headers=get_headers())
    data = resp.json()

    if data.get("ok"):
        print(f"✅ Authenticated as: {data['user']} (bot)")
        print(f"   Team: {data['team']}")
        print(f"   URL: {data.get('url')}")
        return True
    else:
        print(f"❌ Auth failed: {data.get('error')}")
        return False


# ─────────────────────────────────────
# Test 2: List Channels
# ─────────────────────────────────────
def test_list_channels() -> dict:
    """List public channels in the workspace."""
    print("\n── Test 2: List Channels ──")
    resp = requests.get(
        f"{SLACK_API_BASE}/conversations.list",
        headers=get_headers(),
        params={"types": "public_channel", "limit": 20},
    )
    data = resp.json()

    channel_map = {}
    if data.get("ok"):
        channels = data.get("channels", [])
        print(f"✅ Found {len(channels)} channel(s):")
        for ch in channels:
            prefix = "🤖" if ch.get("is_member") else "  "
            print(f"   {prefix} #{ch['name']} (ID: {ch['id']}, members: {ch.get('num_members', '?')})")
            channel_map[f"#{ch['name']}"] = ch["id"]

        # Check if bot is in the target channels
        target = SLACK_DEFAULT_CHANNEL.lstrip("#")
        if f"#{target}" not in channel_map:
            print(f"\n⚠️  Channel {SLACK_DEFAULT_CHANNEL} not found.")
            print(f"   Create it in Slack, then add the bot to it.")
        elif not any(ch.get("is_member") and ch["name"] == target for ch in channels):
            print(f"\n⚠️  Bot is not a member of {SLACK_DEFAULT_CHANNEL}.")
            print(f"   Go to the channel → Integrations → Add apps → add your bot.")
        return channel_map
    else:
        print(f"❌ Failed: {data.get('error')}")
        return channel_map


# ─────────────────────────────────────
# Test 3: Send a Message
# ─────────────────────────────────────
def test_send_message(channel_id: str) -> str | None:
    """Send a test message to the default channel."""
    print(f"\n── Test 3: Send Message ({SLACK_DEFAULT_CHANNEL}) ──")
    resp = requests.post(
        f"{SLACK_API_BASE}/chat.postMessage",
        headers=get_headers(),
        json={
            "channel": channel_id,
            "text": (
                "🤖 *Platform Health Agent — Test Message*\n\n"
                "This is a test message from `project-125/scripts/slack_test.py`.\n"
                "Agent capabilities being tested:\n"
                "• Send messages to channels\n"
                "• Create threaded replies\n"
                "• Rich formatting (bold, code, lists)\n\n"
                f"_Sent at: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}_"
            ),
        },
    )
    data = resp.json()

    if data.get("ok"):
        ts = data["ts"]
        print(f"✅ Message sent (ts: {ts})")
        print(f"   Channel: {data['channel']}")
        return ts
    else:
        print(f"❌ Failed: {data.get('error')}")
        if data.get("error") == "not_in_channel":
            print("   → Add the bot to the channel: channel settings → Integrations → Add apps")
        return None


# ─────────────────────────────────────
# Test 4: Reply in Thread
# ─────────────────────────────────────
def test_thread_reply(channel_id: str, thread_ts: str):
    """Reply to the previous message in a thread."""
    print(f"\n── Test 4: Thread Reply ──")
    resp = requests.post(
        f"{SLACK_API_BASE}/chat.postMessage",
        headers=get_headers(),
        json={
            "channel": channel_id,
            "thread_ts": thread_ts,
            "text": (
                "📋 *Agent Follow-up — Incident Details*\n\n"
                "*KB Search Results:*\n"
                "• Source 1: API Latency Runbook (relevance: 92%)\n"
                "• Source 2: Connection Pool Config Guide (relevance: 87%)\n"
                "• Source 3: Past Incident PLAT-42 (relevance: 78%)\n\n"
                "*Suggested Actions:*\n"
                "1. Check `max_connections` setting (currently 100, recommend 200)\n"
                "2. Review `idle_timeout` (currently 30s, recommend 60s)\n"
                "3. Monitor connection pool utilisation via CloudWatch\n\n"
                "_This is a simulated agent response with KB-enriched context._"
            ),
        },
    )
    data = resp.json()

    if data.get("ok"):
        print(f"✅ Thread reply sent (ts: {data['ts']})")
        return True
    else:
        print(f"❌ Failed: {data.get('error')}")
        return False


# ─────────────────────────────────────
# Test 5: Send Rich Message (Blocks)
# ─────────────────────────────────────
def test_rich_message(channel_id: str):
    """Send a message using Block Kit for rich formatting."""
    print(f"\n── Test 5: Rich Message (Block Kit) ──")
    resp = requests.post(
        f"{SLACK_API_BASE}/chat.postMessage",
        headers=get_headers(),
        json={
            "channel": channel_id,
            "text": "🎫 New Incident Ticket Created",  # fallback for notifications
            "blocks": [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": "🎫 PLAT-87: API Latency Spike"},
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": "*Priority:*\nP2 — High"},
                        {"type": "mrkdwn", "text": "*Status:*\nOpen"},
                        {"type": "mrkdwn", "text": "*Component:*\nAPI Gateway"},
                        {"type": "mrkdwn", "text": "*Assignee:*\nUnassigned"},
                    ],
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            "*Root Cause (from KB):*\n"
                            "Connection pool exhaustion detected. Past incident PLAT-42 "
                            "(2 weeks ago) had same pattern. Runbook suggests increasing "
                            "`max_connections` from 100 → 200."
                        ),
                    },
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "View in Jira"},
                            "url": "https://example.atlassian.net/browse/PLAT-87",
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "View Runbook"},
                            "url": "https://zackblog.work/runbook/api-latency",
                        },
                    ],
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"_Created by Platform Health Agent • {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}_",
                        }
                    ],
                },
            ],
        },
    )
    data = resp.json()

    if data.get("ok"):
        print(f"✅ Rich message sent with Block Kit formatting")
        print(f"   Includes: header, fields, divider, action buttons, context")
        return True
    else:
        print(f"❌ Failed: {data.get('error')}")
        return False


# ─────────────────────────────────────
# Test 6: Get Channel History
# ─────────────────────────────────────
def test_channel_history(channel_id: str):
    """Read recent messages from the channel."""
    print(f"\n── Test 6: Channel History ──")
    resp = requests.get(
        f"{SLACK_API_BASE}/conversations.history",
        headers=get_headers(),
        params={"channel": channel_id, "limit": 5},
    )
    data = resp.json()

    if data.get("ok"):
        messages = data.get("messages", [])
        print(f"✅ Last {len(messages)} message(s):")
        for msg in messages[:3]:
            text_preview = msg.get("text", "")[:80]
            print(f"   [{msg.get('ts')}] {text_preview}...")
        return True
    else:
        print(f"❌ Failed: {data.get('error')}")
        if data.get("error") == "not_in_channel":
            print("   → Bot needs channels:history scope and must be added to channel")
        return False


# ─────────────────────────────────────
# Main — Run All Tests
# ─────────────────────────────────────
def main():
    print("=" * 60)
    print("  Slack API Test Suite — Project 125")
    print("=" * 60)

    check_config()

    # Auth
    if not test_auth():
        print("\n⛔ Cannot authenticate. Check SLACK_BOT_TOKEN.")
        sys.exit(1)

    # List channels
    channel_map = test_list_channels()

    # Resolve channel ID
    channel_name = SLACK_DEFAULT_CHANNEL
    channel_id = channel_map.get(channel_name)
    if not channel_id:
        # Try without # prefix
        channel_id = channel_map.get(f"#{channel_name.lstrip('#')}")
    if not channel_id:
        print(f"\n⛔ Cannot find channel {channel_name}. Create it and add the bot.")
        print("   Available channels:", list(channel_map.keys()))
        sys.exit(1)

    print(f"\n   Using channel: {channel_name} → {channel_id}")

    # Send message
    message_ts = test_send_message(channel_id)
    if not message_ts:
        print("\n⛔ Could not send message. Check bot permissions.")
        sys.exit(1)

    # Thread reply
    test_thread_reply(channel_id, message_ts)

    # Rich message
    test_rich_message(channel_id)

    # Channel history
    test_channel_history(channel_id)

    # Summary
    print("\n" + "=" * 60)
    print("  ✅ All Slack API tests passed!")
    print(f"  Check {channel_name} in your Slack workspace for test messages.")
    print("=" * 60)


if __name__ == "__main__":
    main()
