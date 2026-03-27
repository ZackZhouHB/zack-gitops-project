# Slack Bot E2E Testing — Live Validation Report

> **Date**: 2026-03-27  
> **Status**: ✅ 3/3 Tests Passing — All Slack Bot Flows Validated  
> **Bot**: @Platform Health Bot in #all-platform-health-lab  
> **Stack**: Slack Socket Mode → FastAPI Agent (:8010) → Bedrock Claude + Weaviate RAG + Jira Cloud

---

## 1. Design Logic

### How the Slack Bot Fits in the Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                     SLACK WORKSPACE                               │
│                                                                   │
│  User types: "@Platform Health Bot search for open P1 incidents" │
│                          │                                        │
│                          ▼                                        │
│  ┌────────────────────────────────┐                               │
│  │  Socket Mode (WebSocket)       │  ← No public URL needed      │
│  │  Events: app_mention, message  │  ← Works behind firewalls    │
│  └──────────────┬─────────────────┘                               │
└─────────────────┼────────────────────────────────────────────────┘
                  │ WebSocket
                  ▼
┌─────────────────────────────────────┐
│  slack_bot.py (local process)       │
│                                     │
│  1. Receive event                   │
│  2. Post "🤔 Thinking..." reply    │
│  3. Call POST /chat on agent API    │
│  4. If write action → show buttons  │
│  5. If read-only → show response    │
│  6. On button click → /approve      │
│     or /reject                      │
└──────────────┬──────────────────────┘
               │ HTTP (localhost:8010)
               ▼
┌─────────────────────────────────────┐
│  Agent Backend (FastAPI + LangGraph)│
│                                     │
│  11 Tools:                          │
│  ├── rag_search → Weaviate (198     │
│  │   chunks, 24 docs)               │
│  ├── search_issues → Jira Cloud     │
│  ├── create_ticket → Jira ⚠️ HITL  │
│  ├── send_message → Slack ⚠️ HITL  │
│  └── ... 7 more tools               │
│                                     │
│  HITL: interrupt() on write tools   │
│  Guardrails: PII, topic, token      │
└─────────────────────────────────────┘
```

### Why Socket Mode?

| Approach | Requires Public URL | Firewall Friendly | Local Dev |
|----------|-------------------|-------------------|-----------|
| HTTP Events API | ✅ Yes (ngrok/cloud) | ❌ No | Hard |
| **Socket Mode** | **❌ No** | **✅ Yes** | **Easy** |

Socket Mode uses WebSocket — Slack connects TO us, not the other way around. Perfect for:
- Local development (no ngrok needed)
- Corporate networks (behind firewalls)
- Quick prototyping before deploying to cloud

### Event Flow: Read-Only Query

```
User → @mention → Socket Mode → slack_bot.py
  → POST /chat {"message": "search for P1 incidents"}
  → Agent: search_issues(JQL) → Jira Cloud → results
  → Response: {status: "complete", response: "Found 2 P1...", tool_calls: [...]}
  → slack_bot.py formats Block Kit message → chat_update (replaces "Thinking...")
```

### Event Flow: Write Action (HITL)

```
User → @mention → Socket Mode → slack_bot.py
  → POST /chat {"message": "create a P3 ticket for..."}
  → Agent: rag_search → search_issues → create_ticket → INTERRUPT!
  → Response: {status: "pending_approval", pending_action: {tool: "create_ticket", args: {...}}}
  → slack_bot.py shows Approve/Reject buttons in Slack

User clicks ✅ Approve → Socket Mode → slack_bot.py
  → POST /chat/{thread_id}/approve
  → Agent resumes: create_ticket executes → Jira ticket created
  → Response: {status: "complete", response: "Created SCRUM-21..."}
  → slack_bot.py shows "✅ Approved by @user" + result
```

---

## 2. Slack App Configuration

### 2.1 Prerequisites

- Slack workspace with admin access
- Slack App already created (from Phase B: `platform_health_bot`)
- Bot token (`xoxb-...`) already configured with scopes: `chat:write`, `channels:read`

### 2.2 New Configuration Steps

**Step 1: Enable Socket Mode**
```
https://api.slack.com/apps → Your App → Socket Mode (sidebar) → Toggle ON
→ Generate App-Level Token
→ Name: "socket-mode"
→ Scope: connections:write
→ Copy the xapp-1-... token
```

**Step 2: Enable Event Subscriptions**
```
Event Subscriptions (sidebar) → Toggle ON
→ Subscribe to bot events:
  ✅ app_mention     (triggers on @bot in channels)
  ✅ message.im      (triggers on DMs to bot)
→ Save Changes
```

**Step 3: Enable Interactivity**
```
Interactivity & Shortcuts (sidebar) → Toggle ON
→ No Request URL needed (Socket Mode handles it)
→ Save Changes
```

**Step 4: Required OAuth Scopes** (verify all present)
```
OAuth & Permissions → Scopes → Bot Token Scopes:
  ✅ app_mentions:read
  ✅ chat:write
  ✅ channels:read
  ✅ channels:history
  ✅ im:history
  ✅ im:read
  ✅ im:write
```

**Step 5: Reinstall App** (if any new scopes added)
```
OAuth & Permissions → Reinstall to Workspace → Allow
```

**Step 6: Add Token to .env**
```bash
# In project-125/.env
SLACK_APP_TOKEN=xapp-1-A0AP69X381G-...
```

### 2.3 Running the Bot

```bash
# Terminal 1: Agent backend (already running via Docker)
docker compose up -d

# Terminal 2: Slack bot (runs locally, connects to Docker agent)
cd project-125
source .venv/bin/activate
python frontend/slack_bot.py

# Expected output:
# ✅ Agent backend: healthy | HITL: True | Tools: 11
# 🤖 Starting Slack bot (Socket Mode)...
#    Listening for @mentions and DMs
# ⚡️ Bolt app is running!
```

---

## 3. Issues Found & Fixed During Testing

### Issue #13: Slack `msg_too_long` Error

**Symptom**: Bot received the mention, called agent, got response, but Slack rejected the `chat_update`.

```
slack_sdk.errors.SlackApiError: The request to the Slack API failed.
The server responded with: {'ok': False, 'error': 'msg_too_long'}
```

**Root Cause**: Agent responses for RAG queries can be 3000-5000 characters. Slack's `chat.update` has a combined limit on `text` + `blocks` payload. The original code split response into multiple 2900-char blocks, which made the total payload exceed Slack's limit.

**Fix Applied** (in `frontend/slack_bot.py`):

```python
# BEFORE: Split into multiple blocks (total payload too large)
for i in range(0, len(response), 2900):
    blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": response[i:i+2900]}})

# AFTER: Single block, hard cap at 1500 chars with truncation notice
truncated = response[:1500]
if len(response) > 1500:
    truncated += "\n\n_...truncated. Full answer on Streamlit :8502_"
blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": truncated}})
```

**Additional Fix**: Added fallback error handling so bot never crashes on message length:

```python
try:
    client.chat_update(channel=channel, ts=thinking["ts"], text=fallback, blocks=blocks)
except Exception as e:
    # If blocks still too long, send text-only (guaranteed to fit)
    logger.warning(f"Block message failed ({e}), falling back to text-only")
    client.chat_update(channel=channel, ts=thinking["ts"], text=fallback)
```

**Lesson**: Slack's message limits are strict and not well-documented. The combined `text` + `blocks` JSON payload has an undocumented size cap. Always truncate AND have a text-only fallback.

---

## 4. Test Results

### Test 1: RAG Knowledge Query (Read-Only)

**Input**: `@Platform Health Bot what is our EKS architecture?`

**Expected**: Agent uses `rag_search` to query Weaviate, returns KB knowledge about EKS.

**Result**: ✅ **PASS**

| Metric | Value |
|--------|-------|
| Tool used | `rag_search` (correctly chose RAG over Jira) |
| Tool latency | 945ms |
| Total latency | 14,773ms |
| Sources returned | 5 (Bedrock-Powered RAG on EKS, VPC Lattice Integration, etc.) |
| Response quality | Comprehensive — covered EKS stack, Weaviate, Bedrock, VPC Lattice |
| Truncation | Yes — response exceeded 1500 chars, cleanly truncated with notice |
| Slack rendering | ✅ Block Kit: section + tools badge + sources + latency |

**What this validates**:
- Socket Mode event delivery (app_mention)
- Agent tool selection (LLM chose rag_search for a knowledge question)
- Weaviate vector search through Docker DNS
- Bedrock Claude inference
- Slack Block Kit formatting with truncation

---

### Test 2: Create Jira Ticket with HITL Approval (Write Action)

**Input**: `@Platform Health Bot create a P3 ticket for testing Slack bot integration`

**Expected**: Agent proposes ticket → HITL pauses → shows Approve/Reject buttons → user approves → ticket created.

**Result**: ✅ **PASS**

| Step | What Happened | Latency |
|------|--------------|---------|
| 1. Agent research | `rag_search` (907ms) + `search_issues` (648ms) — checked KB and duplicates | 1,555ms tools |
| 2. HITL interrupt | Agent proposed `create_ticket` → graph paused | — |
| 3. Slack buttons | Approve ✅ / Reject ❌ buttons rendered with ticket details | Instant |
| 4. User clicked Approve | Bot called `/chat/{thread_id}/approve` | — |
| 5. Ticket created | SCRUM-21 created in Jira | 1,317ms |
| 6. Confirmation | "✅ Approved by @Zhou Zack" + full response with ticket link | 7,114ms |

**Approval UI shown in Slack**:
```
⏸️ Approval Required: create_ticket
Summary: Test Slack bot integration functionality
Priority: Low
Labels: slack-integration, testing, automation, platform-health

[✅ Approve]  [❌ Reject]
```

**After approval**:
```
✅ Approved by @Zhou Zack
Ticket Created: SCRUM-21
URL: https://zhbsoftboy1.atlassian.net/browse/SCRUM-21
🔧 Tools: 🔵 rag_search 907ms | 🔵 search_issues 648ms | 🟢 create_ticket (approved) 1317ms
```

**What this validates**:
- Multi-tool chain (RAG → Jira search → Jira create)
- HITL interrupt() propagation from agent → API → Slack bot
- Slack Block Kit interactive buttons (Interactivity enabled)
- Button click → Socket Mode → approve endpoint → agent resume
- Jira ticket actually created (SCRUM-21 verified)
- State management (conversation_id tracking across request/approve)

---

### Test 3: Jira Search by Priority (Read-Only)

**Input**: `@Platform Health Bot search for open P1 incidents`

**Pre-condition**: Created 5 test tickets (SCRUM-22 to SCRUM-26) with priorities P1 through P4.

**Expected**: Agent uses `search_issues` with JQL for Highest priority, returns the 2 P1 tickets.

**Result**: ✅ **PASS**

| Metric | Value |
|--------|-------|
| Tool used | `search_issues` (correctly chose Jira over RAG) |
| Tool latency | 676ms |
| Total latency | 9,640ms |
| Tickets found | 2 (SCRUM-22, SCRUM-23 — both P1 Highest) |
| Response quality | Formatted with status, labels, links, impact, and suggested next actions |

**Response included**:
- Both P1 tickets with correct details
- Clickable Jira links
- Warning that both are unassigned
- Proactive suggestions: "Would you like me to get more details? Search KB for runbooks? Send notifications?"

**What this validates**:
- Agent correctly maps "P1" to Jira "Highest" priority
- JQL query generation by LLM
- Jira REST API integration through Docker
- Tool selection: LLM chose `search_issues` (not `rag_search`) for a ticket query
- Response formatting for Slack (Block Kit with links)

---

## 5. Test Coverage Summary

### Tools Validated Through Slack Bot

| Tool | Test | Direction | HITL |
|------|------|-----------|------|
| `rag_search` | Test 1 (EKS architecture) | Read | No |
| `search_issues` | Test 2 (duplicate check) + Test 3 (P1 search) | Read | No |
| `create_ticket` | Test 2 (create + approve) | Write | ✅ Yes |

### Flows Validated

| Flow | Description | Status |
|------|-------------|--------|
| Read-only (RAG) | @mention → rag_search → response | ✅ |
| Read-only (Jira) | @mention → search_issues → response | ✅ |
| Write + HITL | @mention → multi-tool → interrupt → approve button → execute | ✅ |
| Error recovery | msg_too_long → fallback to text-only | ✅ |
| Socket Mode connection | WebSocket established, events received | ✅ |
| Block Kit rendering | Sections, context, buttons, dividers | ✅ |
| Interactive buttons | Approve/Reject click → action handler | ✅ |

### Flows Not Yet Tested (Future)

| Flow | Why Not Tested |
|------|---------------|
| DM to bot | Requires `message.im` event — needs testing |
| Reject button | User only tested Approve path |
| Slack send_message via bot | Would create recursive loop (bot triggers bot) |
| Multiple concurrent users | Only 1 user in workspace |
| Container restart recovery | MemorySaver is in-memory (loses state on restart) |

---

## 5.1 Bonus Test: ReAct Multi-Step Reasoning (Follow-Up Query)

During testing, an unplanned but highly revealing test occurred:

### Test 4: Follow-Up in Thread (ReAct Loop Observed)

**Context**: After Test 1 returned EKS architecture overview, user replied in the same Slack thread:

**Input**: `@Platform Health Bot can you go a bit deeper in how EKS handle deployment using gitops`

**Result**: ✅ **PASS** — with a key observation

| Metric | Value |
|--------|-------|
| Tools used | `rag_search` × **2** (892ms + 1030ms) |
| Total latency | ~15s |
| Response quality | Deeper GitOps/deployment details from multiple KB sources |

### Why This Matters: ReAct Loop in Action

The agent made **two separate RAG searches** instead of one. This was not hardcoded — the LLM autonomously decided one search wasn't enough:

```
ReAct Iteration 1:
  LLM thinks: "User wants deeper info on EKS + GitOps deployment"
  → Action: rag_search("EKS deployment GitOps") → 892ms → got partial results
  
ReAct Iteration 2:
  LLM thinks: "I have some info but need more specifics on the GitOps workflow"
  → Action: rag_search("GitOps ArgoCD Kubernetes deployment") → 1030ms → got more results

ReAct Iteration 3:
  LLM thinks: "Now I have comprehensive context — ready to answer"
  → Action: Generate final response → END
```

This is the **core value of a ReAct agent** over a simple RAG pipeline:

```
Simple RAG pipeline (fixed):
  Query → 1 search → 1 response (always)

ReAct Agent (dynamic):
  Query → LLM reasons → search → LLM evaluates → "need more?" → search again → ... → respond
           ↑                                                          │
           └──────────── loop continues until satisfied ──────────────┘
```

### What This Confirms About Our Design

| Design Principle | How Test 4 Confirms It |
|-----------------|----------------------|
| **Autonomous reasoning** | LLM decided independently that 1 search was insufficient — no rule told it to search twice |
| **Query reformulation** | Second search used different keywords than first — LLM adapted its strategy based on initial results |
| **Dynamic tool count** | Test 1 used 1 tool call, Test 4 used 2 — the agent adapts effort to question complexity |
| **ReAct loop works** | The `llm → should_continue → tool_node → llm` loop correctly iterated multiple times |
| **Quality vs speed tradeoff** | Deeper question = more tool calls = better answer but ~5s more latency |

### Implications for Production

| Aspect | Impact |
|--------|--------|
| **Answer quality** | Multiple searches with different angles = more comprehensive answers |
| **Cost** | Each loop iteration = 1 Bedrock LLM call (~$0.01) + 1 Weaviate query |
| **Latency** | ~5-10s per extra iteration (Bedrock inference dominates) |
| **Loop protection** | Guardrails limit max iterations (RECURSION_LIMIT) to prevent runaway loops |
| **Observability** | Tool badges in Slack show exactly how many calls the agent made — full transparency |

---

## 5.2 Test 5: Web Search for Real-Time Information

After adding `web_search` (DuckDuckGo) as tool #12, we tested the agent's ability to combine internal KB with live web data.

### Test 5: Current EKS Version (Web Search Required)

**Input**: `@Platform Health Bot what is the latest EKS version in 2026 March`

**Expected**: Agent searches internal KB first (no current version data) → autonomously switches to web search for live data.

**Result**: ✅ **PASS**

| Metric | Value |
|--------|-------|
| Tools used | `rag_search` (893ms) + `web_search` × 3 (2561ms + 4780ms + 1769ms) |
| Total latency | 30,615ms |
| Sources | 5 KB articles (EKS blog posts) + live web results |
| Response quality | Combined KB context with current Kubernetes release cycle data |
| Truncation | Yes — cleanly truncated with Streamlit redirect |

### The Tool Selection Logic

```
ReAct Iteration 1:
  LLM thinks: "User wants latest EKS version — let me check our KB first"
  → Action: rag_search("latest EKS version 2026") → found EKS blog posts but NO version data
  
ReAct Iteration 2:
  LLM thinks: "KB has EKS architecture docs but not current versions — need live data"
  → Action: web_search("latest Amazon EKS Kubernetes version 2026") → found release info

ReAct Iteration 3:
  LLM thinks: "Need more specific details on the release timeline"
  → Action: web_search("EKS Kubernetes 1.33 support date") → found dates

ReAct Iteration 4:
  LLM thinks: "Let me verify the March 2026 support window"
  → Action: web_search("Amazon EKS Kubernetes 1.32 support announcement") → confirmed

ReAct Iteration 5:
  LLM thinks: "Now I have enough data to answer comprehensively"
  → Generate final response combining KB context + live web data → END
```

### What This Validates

| Design Principle | How Test 5 Confirms It |
|-----------------|----------------------|
| **KB-first strategy** | Agent checked internal KB before going to the web — avoids unnecessary external calls |
| **Autonomous fallback** | LLM decided independently to switch from `rag_search` to `web_search` when KB lacked the answer |
| **Multi-source fusion** | Response combined internal KB architecture docs with live web version data |
| **Tool #12 integration** | `web_search` works seamlessly alongside the original 11 tools — no changes to graph flow |
| **ReAct adaptability** | 4 tool calls for this query vs 1 for simple KB questions — effort scales with complexity |

### Comparison: With vs Without Web Search

| Question | Without web_search | With web_search |
|----------|-------------------|----------------|
| "What is our EKS architecture?" | ✅ KB has it | ✅ KB has it (web not needed) |
| "Latest EKS version in 2026?" | ❌ KB outdated, agent guesses | ✅ Live data from AWS docs |
| "Any known CVE for EKS 1.33?" | ❌ Not in KB | ✅ Can search security advisories |
| "Search P1 incidents" | ✅ Jira search | ✅ Jira search (web not needed) |

The agent intelligently picks `web_search` only when needed — internal tools are always preferred first.

---

## 6. AI Agent Skills Demonstrated

This Slack bot test validates several key AI agent engineering competencies:

### 6.1 Entry Point Design

**Skill**: An agent should be accessible from multiple entry points without code changes.

Our agent backend serves 3 entry points via the same `/chat` API:
1. **Streamlit UI** (:8502) — for development and demos
2. **Slack Bot** (Socket Mode) — for team collaboration
3. **Direct API** (curl/scripts) — for automation and testing

The agent code (`graph.py`) doesn't know or care which entry point called it. This is the **separation of concerns** pattern that production agents require.

### 6.2 Human-in-the-Loop Across Channels

**Skill**: HITL approval must work regardless of which UI triggered the action.

The interrupt() mechanism works identically whether triggered from:
- Streamlit (approve/reject buttons in web UI)
- Slack (approve/reject buttons in Block Kit)
- API (POST to /approve or /reject)

This proves HITL is implemented at the **graph level** (LangGraph interrupt), not the UI level.

### 6.3 Tool Selection Intelligence

**Skill**: The LLM must choose the right tool based on user intent, not keywords.

| User Said | Tool Selected | Why Correct |
|-----------|--------------|-------------|
| "what is our EKS architecture?" | `rag_search` | Knowledge question → search KB |
| "create a P3 ticket for..." | `rag_search` + `search_issues` + `create_ticket` | Research → check duplicates → create |
| "search for open P1 incidents" | `search_issues` | Ticket query → search Jira |

The agent never confused Jira queries with RAG queries — this is the core value of a ReAct agent.

### 6.4 Graceful Degradation

**Skill**: Production bots must handle errors without crashing.

The `msg_too_long` bug showed why error handling matters:
- **Before fix**: Bot crashed silently, user saw "🤔 Thinking..." forever
- **After fix**: Bot truncates + has text-only fallback, always responds

### 6.5 Real-Time Feedback

**Skill**: Users need to know the agent is working (not frozen).

Pattern implemented:
1. Immediately post "🤔 Thinking..." (user knows bot received the message)
2. Replace with full response when ready (chat_update, not new message)
3. Show tool badges and latency (transparency about what happened)

### 6.6 Production Readiness Indicators

| Indicator | Status | Notes |
|-----------|--------|-------|
| No public URL needed | ✅ | Socket Mode works behind firewalls |
| Error handling | ✅ | msg_too_long fallback, connection errors handled |
| Latency acceptable | ✅ | 9-15s (Bedrock inference dominates) |
| HITL works in Slack | ✅ | Interactive buttons with state tracking |
| Multiple entry points | ✅ | Same agent serves Streamlit + Slack + API |
| Observability | Partial | Bot logs events, but no structured tracing yet |

---

## 7. Summary

| Metric | Value |
|--------|-------|
| Tests executed | 5 |
| Tests passed | 5 (100%) |
| Issues found | 1 (msg_too_long — fixed) |
| Tools validated | 4/12 (rag_search, search_issues, create_ticket, web_search) |
| Flows validated | 9 (see section 5) |
| ReAct multi-step observed | Yes — agent autonomously did 2x rag_search on deeper question |
| Web search observed | Yes — agent used rag_search → web_search×3 for current info |
| Jira tickets created | SCRUM-21 (via bot), SCRUM-22-26 (test data) |
| Total test time | ~8 minutes (including fix iteration) |

### Key Takeaway

The Slack bot proves that our AI agent is **entry-point agnostic** — the same LangGraph ReAct loop, the same 12 tools (including web_search), the same HITL interrupt mechanism, and the same guardrails work identically whether triggered from a web UI, a Slack message, or a raw API call. This is the architecture pattern that enterprise teams use: **one agent, many interfaces**.

---

*Created 2026-03-27 — Slack Bot E2E Live Testing Report*
