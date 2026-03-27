# Step 23b — Slack Bot Entry Point: Trigger the Agent from Slack

## 23b.1 Goal

Make the agent usable **directly from Slack** — no separate UI needed. Engineers type `@platform_health_bot investigate API latency` in any channel, and the bot:
1. Calls the Agent API
2. Shows the response with sources and tool badges
3. If a write action is proposed → shows **Approve / Reject buttons** in Slack
4. On button click → executes or cancels the action

This uses **Slack Socket Mode** — the bot connects **outbound** to Slack via WebSocket. No public URL, no ngrok, works on localhost.

---

## 23b.2 How Socket Mode Solves the "Local vs Cloud" Problem

```
Traditional (needs public URL):
  Slack Cloud ──HTTP POST──→ https://your-server.com/slack/events
                              ↑ Must be publicly accessible!

Socket Mode (our approach):
  Your laptop ──WebSocket──→ Slack Cloud
                              ↑ Outbound connection — works from anywhere!
```

**Why this matters**: Your agent runs on `localhost:8010`. Slack can't send HTTP to localhost. With Socket Mode, your bot opens a persistent WebSocket TO Slack, and Slack pushes events through that connection.

---

## 23b.3 Setup Steps

### Step 1: Enable Socket Mode

1. Go to https://api.slack.com/apps
2. Click your app (**platform_health_bot**)
3. Left sidebar → **Socket Mode**
4. Toggle **Enable Socket Mode** → ON
5. It will ask you to create an **App-Level Token**:
   - Name: `socket-mode`
   - Scope: `connections:write`
   - Click **Generate**
6. Copy the token (starts with `xapp-1-...`)
7. Add to your `.env`:
   ```
   SLACK_APP_TOKEN=xapp-1-your-token-here
   ```

### Step 2: Enable Event Subscriptions

1. Left sidebar → **Event Subscriptions**
2. Toggle **Enable Events** → ON
3. Under **Subscribe to bot events**, add:
   - `app_mention` — triggers when someone types `@platform_health_bot`
   - `message.im` — triggers on direct messages to the bot
4. Click **Save Changes**

### Step 3: Enable Interactivity

1. Left sidebar → **Interactivity & Shortcuts**
2. Toggle **Interactivity** → ON
3. (Socket Mode handles the URL automatically — no need to enter one)
4. Click **Save Changes**

### Step 4: Reinstall the App

After adding new permissions:
1. Left sidebar → **Install App**
2. Click **Reinstall to Workspace**
3. Approve the new permissions

### Step 5: Run the Bot

```bash
cd project-125 && source .venv/bin/activate

# Terminal 1: Start the agent backend
cd agent-backend && python main.py

# Terminal 2: Start the Slack bot
cd frontend && python slack_bot.py
```

You should see:
```
✅ Agent backend: healthy | HITL: True | Tools: 11

🤖 Starting Slack bot (Socket Mode)...
   Listening for @mentions and DMs
   Ctrl+C to stop
```

---

## 23b.4 How to Use

### In a Channel (via @mention)
```
You:  @platform_health_bot search Jira for EKS tickets
Bot:  Found 3 EKS-related tickets...
      🔵 search_issues 485ms
```

### In a Direct Message
```
You:  What's the architecture of our RAG system?
Bot:  Based on the knowledge base, the Bedrock-powered RAG system...
      🔵 rag_search 892ms
      📚 Sources: Bedrock-Powered RAG on EKS (blog) — 65%
```

### Write Action with Approval
```
You:  @platform_health_bot create a ticket for Redis cache miss spike

Bot:  🤔 Thinking...

Bot:  [updates message with:]
      I searched the KB and Jira. No duplicates found.

      ⏸️ Approval Required: create_ticket
      Summary: Redis cache miss spike
      Priority: High
      Labels: redis, cache, performance

      [✅ Approve]  [❌ Reject]

You:  [clicks ✅ Approve]

Bot:  [updates message with:]
      ✅ Approved by @you
      Created SCRUM-21: https://zhbsoftboy1.atlassian.net/browse/SCRUM-21
```

---

## 23b.5 Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  Slack Cloud                                                  │
│                                                              │
│  #all-platform-health-lab                                    │
│  ├── @platform_health_bot investigate X                      │
│  │      │                                                    │
│  │      │  (event: app_mention)                              │
│  │      ▼                                                    │
│  │   WebSocket ─────────────── outbound ──────────┐          │
│  │                                                │          │
│  │   Button click ──────────── outbound ──────────┤          │
│  │   (action: approve_action)                     │          │
│  │                                                │          │
└──────────────────────────────────────────────────┼──────────┘
                                                   │
┌──────────────────────────────────────────────────┼──────────┐
│  Your Machine (localhost)                        │           │
│                                                  ▼           │
│  ┌───────────────────────────────────────────────────────┐   │
│  │  slack_bot.py (Socket Mode)                           │   │
│  │                                                       │   │
│  │  @mention ──→ POST /chat                              │   │
│  │  approve  ──→ POST /chat/{id}/approve                 │   │
│  │  reject   ──→ POST /chat/{id}/reject                  │   │
│  └───────────────────────┬───────────────────────────────┘   │
│                          │                                    │
│                          ▼                                    │
│  ┌───────────────────────────────────────────────────────┐   │
│  │  Agent API (:8010)                                     │   │
│  │  FastAPI + LangGraph + HITL                            │   │
│  │  [RAG + Jira + Slack tools]                            │   │
│  └───────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

The Slack bot is a **thin adapter** (~300 lines):
- Receives events via WebSocket (Socket Mode)
- Translates them to Agent API calls
- Formats responses as Slack Block Kit
- Handles button clicks for HITL approval

**All intelligence stays in the Agent API** — the bot is just a bridge.

---

## 23b.6 Key Concepts

### Socket Mode vs HTTP Mode

| Feature | HTTP Mode (Events API) | Socket Mode |
|---------|----------------------|-------------|
| Connection | Slack → Your server (inbound) | Your bot → Slack (outbound) |
| Public URL | ✅ Required | ❌ Not needed |
| SSL cert | ✅ Required | ❌ Not needed |
| Works on localhost | ❌ No (need ngrok) | ✅ Yes |
| Production ready | ✅ Yes (standard) | ✅ Yes (supported) |
| Token type | Bot token only | Bot token + App-Level token |

### Block Kit Approval Buttons

Slack's Block Kit lets us show interactive buttons:
```python
{
    "type": "actions",
    "elements": [
        {
            "type": "button",
            "text": {"type": "plain_text", "text": "✅ Approve"},
            "style": "primary",
            "action_id": "approve_action",   # Triggers @app.action("approve_action")
            "value": thread_id,               # Carries the conversation ID
        },
        {
            "type": "button",
            "text": {"type": "plain_text", "text": "❌ Reject"},
            "style": "danger",
            "action_id": "reject_action",
            "value": thread_id,
        },
    ]
}
```

When the user clicks a button:
1. Slack sends an `action` event through the WebSocket
2. `slack-bolt` routes it to the matching `@app.action()` handler
3. Handler calls `/approve` or `/reject` on the Agent API
4. Handler updates the original Slack message with the result

---

## 23b.7 What You Need to Configure

| Setting | Where | Value |
|---------|-------|-------|
| Socket Mode | Slack App → Socket Mode | Enabled |
| App-Level Token | Slack App → Socket Mode → Generate | `xapp-1-...` (add to .env as `SLACK_APP_TOKEN`) |
| Event: app_mention | Slack App → Event Subscriptions → Bot Events | Added |
| Event: message.im | Slack App → Event Subscriptions → Bot Events | Added |
| Interactivity | Slack App → Interactivity | Enabled |
| Reinstall | Slack App → Install App | Reinstalled after changes |

---

## 23b.8 Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Bot doesn't respond to @mention | `app_mention` event not subscribed | Add in Event Subscriptions |
| Bot doesn't respond to DMs | `message.im` event not subscribed | Add in Event Subscriptions |
| Buttons don't work | Interactivity not enabled | Enable in Interactivity & Shortcuts |
| "not_allowed_token_type" error | Using bot token instead of app token | Use `xapp-...` token for SLACK_APP_TOKEN |
| "missing_scope" error | App-Level Token missing `connections:write` | Regenerate token with correct scope |
| Bot responds twice | Handling both `message` and `app_mention` in channels | The code filters: `message` handler only processes DMs |

---

## 23b.9 What's Next

With the Slack bot working, the agent is now accessible from **three entry points**:
1. **Streamlit UI** (localhost:8502) — for testing and development
2. **Slack bot** (@platform_health_bot) — for real team usage
3. **curl / API** (localhost:8010) — for scripting and CI/CD

All three use the same Agent API, the same tools, and the same HITL approval flow.

In **Step 24 (Phase F)**, we'll add eval & guardrails to ensure quality across all entry points.
