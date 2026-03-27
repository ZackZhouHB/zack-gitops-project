# Step 20: Slack API — Bot Messaging, Threads, and Rich Formatting

> **What you'll learn**: How to authenticate a Slack bot, send messages, create threads, and use Block Kit for rich formatting — all with plain Python.  
> **Why this matters**: Slack is where teams get notified. An agent that creates a Jira ticket but can't notify anyone is only half useful.  
> **Time**: ~20 minutes reading + 10 minutes hands-on  
> **Prerequisites**: Slack workspace + bot app created, bot token in `.env`, bot added to channels

---

## 20.1 Slack API Model — How Bots Work

Unlike Jira (where you authenticate as a user), Slack uses a **bot identity**:

```
Your Slack Workspace
├── #platform-alerts     ← bot is a member
├── #incidents           ← bot is a member
├── #general             ← bot is NOT a member (intentional)
│
└── Apps
    └── Platform Health Bot
        ├── Bot Token: xoxb-...
        ├── Scopes: chat:write, channels:read, channels:history
        └── Can only act in channels where it's been added
```

> **Key insight**: A Slack bot can only see and post in channels where it's been explicitly added. This is a **security feature** and also a natural guardrail for our agent — it literally cannot post to channels it shouldn't.

---

## 20.2 Authentication

Slack uses **Bearer token** auth (simpler than Jira's Basic Auth):

```python
SLACK_BOT_TOKEN = "xoxb-your-token-here"

headers = {
    "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
    "Content-Type": "application/json; charset=utf-8"
}
```

Token prefixes tell you the type:
| Prefix | Type | Use Case |
|--------|------|----------|
| `xoxb-` | Bot token | Our agent (recommended) |
| `xoxp-` | User token | Acts as a specific user |
| `xapp-` | App-level token | Socket Mode, events |

We use `xoxb-` (bot token) because the agent should have its own identity, not impersonate a user.

---

## 20.3 Core Operations

### Operation 1: Send a Message

```python
import requests

resp = requests.post(
    "https://slack.com/api/chat.postMessage",
    headers=headers,
    json={
        "channel": "#platform-alerts",  # Channel name or ID
        "text": "🎫 New incident ticket PLAT-87 created for API latency spike"
    }
)
data = resp.json()
# {"ok": true, "ts": "1234567890.123456", "channel": "C0123ABCD"}
```

> **Important**: The `ts` (timestamp) in the response is the message's unique ID. You need it to create thread replies. Always save it.

### Operation 2: Reply in a Thread

Threads keep channels clean. Instead of flooding #platform-alerts with details, post a summary as the main message and details as thread replies:

```python
# Original message ts from Operation 1
thread_ts = "1234567890.123456"

resp = requests.post(
    "https://slack.com/api/chat.postMessage",
    headers=headers,
    json={
        "channel": "#platform-alerts",
        "thread_ts": thread_ts,  # This makes it a reply
        "text": "📋 KB Search Results:\n• Root cause: connection pool exhaustion (92%)\n• Runbook: https://..."
    }
)
```

**Agent pattern:**
```
Main message:    "🎫 PLAT-87 created: API latency spike (P2)"
  └─ Thread:     "📋 KB context: 3 related incidents found..."
  └─ Thread:     "🔧 Suggested actions: increase max_connections..."
  └─ Thread:     "✅ Team notified, ticket assigned to on-call"
```

### Operation 3: List Channels

```python
resp = requests.get(
    "https://slack.com/api/conversations.list",
    headers=headers,
    params={
        "types": "public_channel",
        "limit": 100
    }
)
channels = resp.json()["channels"]
# [{"id": "C0123ABCD", "name": "platform-alerts", "is_member": true}, ...]
```

> **Why list channels?** The agent needs to resolve `#platform-alerts` to a channel ID (`C0123ABCD`). Also useful for validation — if the user says "post to #nonexistent", the agent can say "that channel doesn't exist."

### Operation 4: Rich Messages with Block Kit

Plain text works, but **Block Kit** makes messages professional:

```python
resp = requests.post(
    "https://slack.com/api/chat.postMessage",
    headers=headers,
    json={
        "channel": channel_id,
        "text": "Fallback text for notifications",  # Required fallback
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "🎫 PLAT-87: API Latency Spike"}
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": "*Priority:*\nP2 — High"},
                    {"type": "mrkdwn", "text": "*Status:*\nOpen"},
                    {"type": "mrkdwn", "text": "*Component:*\nAPI Gateway"},
                    {"type": "mrkdwn", "text": "*Assignee:*\nUnassigned"}
                ]
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Root Cause (from KB):*\nConnection pool exhaustion..."
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "View in Jira"},
                        "url": "https://your-site.atlassian.net/browse/PLAT-87"
                    }
                ]
            }
        ]
    }
)
```

This renders as a beautifully formatted card with headers, fields, and action buttons.

> **Block Kit Builder**: Use https://app.slack.com/block-kit-builder to visually design message layouts. Paste the JSON into your code.

---

## 20.4 Slack vs Jira — API Comparison

| Aspect | Jira | Slack |
|--------|------|-------|
| Auth | Basic (email:token base64) | Bearer token |
| Rich text | ADF (Atlassian Document Format) | Block Kit + mrkdwn |
| Error format | `{"errors": {...}}` | `{"ok": false, "error": "..."}` |
| Rate limits | Per-user, varies | Tier-based (1-100 req/min) |
| Pagination | `startAt` + `maxResults` | Cursor-based (`next_cursor`) |
| Unique IDs | Issue key (PLAT-87) | Timestamp (1234567890.123456) |

---

## 20.5 Error Handling

Slack always returns HTTP 200, even on errors. Check the `ok` field:

```python
resp = requests.post("https://slack.com/api/chat.postMessage", ...)
data = resp.json()

if data["ok"]:
    return data  # Success
else:
    error = data["error"]
    # Handle specific errors
    if error == "not_in_channel":
        return "Bot is not a member of this channel. Add it first."
    elif error == "channel_not_found":
        return "Channel does not exist."
    elif error == "invalid_auth":
        return "Bot token is invalid or expired."
    elif error == "ratelimited":
        retry_after = int(resp.headers.get("Retry-After", 30))
        time.sleep(retry_after)
        # Retry...
```

| Error | Meaning | Agent Should... |
|-------|---------|----------------|
| `not_in_channel` | Bot not added to channel | Tell user to add bot |
| `channel_not_found` | Channel doesn't exist | Suggest similar channels |
| `invalid_auth` | Token revoked/wrong | Alert — credential issue |
| `ratelimited` | Too many requests | Back off (Retry-After header) |
| `missing_scope` | Bot lacks permission | Alert — reconfigure app |

---

## 20.6 Running the Test Script

```bash
cd project-125

# Make sure .env has your Slack credentials
cat .env | grep SLACK

# Run the test suite
python scripts/slack_test.py
```

Expected output:
```
══════════════════════════════════════════════════════
  Slack API Test Suite — Project 125
══════════════════════════════════════════════════════
✅ Config loaded: token starts with xoxb-1234...
   Default channel: #platform-alerts

── Test 1: Auth Test ──
✅ Authenticated as: platform-health-bot (bot)
   Team: Platform Health Lab

── Test 2: List Channels ──
✅ Found 3 channel(s):
   🤖 #platform-alerts (ID: C0123...)
   🤖 #incidents (ID: C0456...)
      #general (ID: C0789...)

── Test 3: Send Message (#platform-alerts) ──
✅ Message sent (ts: 1234567890.123456)

── Test 4: Thread Reply ──
✅ Thread reply sent

── Test 5: Rich Message (Block Kit) ──
✅ Rich message sent with Block Kit formatting

── Test 6: Channel History ──
✅ Last 3 message(s)

══════════════════════════════════════════════════════
  ✅ All Slack API tests passed!
══════════════════════════════════════════════════════
```

---

## 20.7 Real-World Issues We Hit

### Bot Not in Channel

When first testing, `send_message` may return `not_in_channel`. Slack bots must be **explicitly added** to each channel — they don't automatically join.

**Fix**: Go to each channel → click channel name → **Integrations** → **Add apps** → select your bot.

> **Lesson**: This is actually a security feature and a natural guardrail — the bot literally cannot post to channels it shouldn't.

### Channel Name Resolution

The Slack API works best with **channel IDs** (e.g., `C0AP46Q59E2`), not names (e.g., `#platform-alerts`). Our client resolves names to IDs automatically via `conversations.list`, but this adds an extra API call.

> **Lesson**: Cache channel ID lookups in production. Resolve once on startup and reuse.

---

## 20.8 What We Proved

| Capability | API Call | Works? |
|-----------|---------|--------|
| Authentication | Bearer token (xoxb-) | ✅ |
| Send message | chat.postMessage | ✅ |
| Thread reply | chat.postMessage + thread_ts | ✅ |
| Rich formatting | Block Kit blocks | ✅ |
| List channels | conversations.list | ✅ |
| Read history | conversations.history | ✅ |

---

## 20.9 Key Takeaways

1. **Slack always returns 200** — check `data["ok"]` for real success/failure
2. **Save the `ts` value** — it's the message ID, needed for threads
3. **Bot must be added to channels** — it can't see/post in channels it hasn't joined
4. **Block Kit >> plain text** — for incident notifications, rich formatting is expected
5. **Thread pattern** — main message = summary, thread = details (keeps channels readable)
6. **Channel ID vs name** — API works with both, but ID is more reliable

---

## 20.10 Jira + Slack Together — The Agent Pattern

Now that you understand both APIs, here's how they combine in an agent workflow:

```
User: "Create a ticket for API latency and notify the team"

Agent:
  1. rag_search("API latency")           → KB context (existing tool)
  2. search_jira("API latency")          → duplicate check
  3. create_ticket(enriched with KB)     → PLAT-87
  4. send_slack(summary + PLAT-87 link)  → #platform-alerts
  5. thread_reply(KB details, runbook)   → thread under summary
```

Step 21 will wrap these API calls in MCP servers. Step 22 will wire them into the LangGraph agent.

---

**Previous**: [Step 19 — Jira API Basics](step-19-jira-api-basics.md)  
**Next**: [Step 21 — Building MCP Servers](step-21-mcp-servers.md)

*Created 2026-03-26 — Project 125, Phase B*
