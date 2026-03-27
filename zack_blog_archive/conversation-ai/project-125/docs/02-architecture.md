# Architecture — Project 125

> **Pattern**: Extended ReAct Agent + MCP Servers + Human-in-the-Loop + Eval Pipeline  
> **Foundation**: platform-health-agent local stack (Weaviate + PostgreSQL + LangGraph)

---

## 1. System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         LOCAL (Docker Compose)                      │
│                                                                     │
│  ┌──────────────┐     ┌──────────────────────────────────────────┐  │
│  │  Streamlit   │────→│  FastAPI + LangGraph Agent               │  │
│  │  (:8502)     │     │  (:8010)                                 │  │
│  │              │     │                                          │  │
│  │  • Chat UI   │     │  ReAct Loop:                             │  │
│  │  • Approval  │◀───│  START → llm → should_continue → tools  │  │
│  │    Panel     │     │    ↑                              │      │  │
│  │  • Eval      │     │    └──────────────────────────────┘      │  │
│  │    Dashboard │     │                                          │  │
│  └──────────────┘     │  Tools (direct):                         │  │
│                        │  ├── rag_search      → Weaviate         │  │
│                        │  ├── assess_incident → pattern match    │  │
│                        │  ├── create_checklist→ PostgreSQL       │  │
│                        │  └── escalate        → PostgreSQL       │  │
│                        │                                          │  │
│                        │  Tools (via MCP):                        │  │
│                        │  ├── MCP Client ──→ Jira MCP Server     │  │
│                        │  └── MCP Client ──→ Slack MCP Server    │  │
│                        │                                          │  │
│                        │  HITL Layer:                              │  │
│                        │  └── interrupt() → approval → resume     │  │
│                        └──────────────────────────────────────────┘  │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────────┐  │
│  │  Weaviate    │  │  PostgreSQL  │  │  MCP Servers              │  │
│  │  (:8080)     │  │  (:5432)     │  │                           │  │
│  │              │  │              │  │  ┌─────────────────────┐  │  │
│  │  198 chunks  │  │  • sessions  │  │  │ Jira Server (:8002) │  │  │
│  │  24 docs     │  │  • tool_logs │  │  │ • search_issues     │  │  │
│  │  1024d embed │  │  • checklists│  │  │ • create_ticket     │  │  │
│  └──────────────┘  │  • approvals │  │  │ • update_ticket     │  │  │
│                     │  • eval_runs │  │  └─────────────────────┘  │  │
│                     └──────────────┘  │  ┌─────────────────────┐  │  │
│                                        │  │ Slack Server (:8003)│  │  │
│                                        │  │ • send_message      │  │  │
│                                        │  │ • create_thread     │  │  │
│                                        │  │ • list_channels     │  │  │
│                                        │  └─────────────────────┘  │  │
│                                        └───────────────────────────┘  │
└────────────────────────────────────────────┬────────────────────────┘
                                             │ API calls
                    ┌────────────────────────┼────────────────────────┐
                    │                        │                        │
           ┌────────▼─────────┐   ┌─────────▼────────┐   ┌──────────▼──────┐
           │  AWS Bedrock     │   │  Jira Cloud      │   │  Slack API      │
           │  (ap-southeast-2)│   │  (Free Tier)     │   │  (Free Workspace│
           │                  │   │                  │   │   + Bot App)    │
           │  • Claude Sonnet │   │  • REST API v3   │   │  • Web API      │
           │  • Titan Embed   │   │  • JQL search    │   │  • chat:write   │
           │  • Guardrails    │   │  • CRUD tickets  │   │  • channels:read│
           └──────────────────┘   └──────────────────┘   └─────────────────┘
```

---

## 2. Agent Graph (Extended)

```
START
  ↓
router_node
  ├─ Classifies intent: general_qa | incident_triage | action_request
  ↓
[ACTION REQUEST PATH]                    [GENERAL QA / INCIDENT PATHS]
  │                                        │
  ↓                                        ↓
llm_node (plan the action)              (existing paths — unchanged)
  │
  ↓
tool_node (READ tools only)
  ├── rag_search("API latency")          → KB context
  ├── search_jira("API latency")         → duplicate check
  │
  ↓
llm_node (prepare write action)
  │ "I'll create PLAT ticket with this data..."
  │
  ↓
┌─────────────────────────────────────┐
│  interrupt()  — HUMAN APPROVAL      │
│                                     │
│  Agent presents proposed action     │
│  User: [Approve] [Edit] [Reject]   │
│                                     │
│  On Approve: Command(resume=True)   │
│  On Edit: Command(resume=edits)     │
│  On Reject: Command(resume=False)   │
└──────────────┬──────────────────────┘
               │
               ↓
tool_node (WRITE tools — only after approval)
  ├── create_jira_ticket(enriched data)  → PLAT-87
  ├── send_slack_message(summary)        → posted
  │
  ↓
llm_node (final response)
  │ "Created PLAT-87, notified #platform-alerts"
  │
  ↓
END
```

---

## 3. MCP Server Architecture

### Why MCP (not direct tools)?

| Approach | Pros | Cons |
|----------|------|------|
| **Direct tools** | Simple, fewer moving parts | Tied to this agent framework |
| **MCP servers** | Reusable across any agent, standard protocol, testable independently | Extra process per server |

We use MCP because:
1. Industry standard — Anthropic-created, widely adopted
2. Portfolio value — shows you can build interoperable components
3. Testable — each MCP server runs independently, can test without the agent
4. Portable — same servers work with Claude Desktop, LangChain, any MCP client

### MCP Protocol Flow

```
Agent (LangGraph)
  │
  ├── MCP Client (built into agent)
  │     │
  │     ├── stdio/SSE ──→ Jira MCP Server (separate process)
  │     │                   ├── Tool: search_issues(jql)
  │     │                   ├── Tool: create_ticket(project, summary, ...)
  │     │                   ├── Tool: update_ticket(key, fields)
  │     │                   └── Tool: get_ticket(key)
  │     │
  │     └── stdio/SSE ──→ Slack MCP Server (separate process)
  │                         ├── Tool: send_message(channel, text)
  │                         ├── Tool: create_thread(channel, text)
  │                         └── Tool: list_channels()
  │
  └── Direct tools (existing, no MCP)
        ├── rag_search → Weaviate
        ├── assess_incident → pattern match
        ├── create_checklist → PostgreSQL
        └── escalate → PostgreSQL
```

### MCP Server Implementation Pattern

Each MCP server is a standalone Python process:

```
mcp-servers/jira-server/
├── server.py          # MCP server entry point
├── jira_client.py     # Raw Jira REST API wrapper
├── config.py          # Environment variables
├── requirements.txt   # mcp, requests
└── README.md          # How to run/test independently
```

---

## 4. Human-in-the-Loop Flow

### Approval State Machine

```
┌─────────┐     ┌──────────┐     ┌──────────┐
│ PENDING  │────→│ APPROVED │────→│ EXECUTED │
│         │     └──────────┘     └──────────┘
│         │
│         │     ┌──────────┐     ┌──────────┐
│         │────→│ EDITED   │────→│ APPROVED │──→ EXECUTED
│         │     └──────────┘     └──────────┘
│         │
│         │     ┌──────────┐
│         │────→│ REJECTED │
│         │     └──────────┘
│         │
│         │     ┌──────────┐
│         │────→│ TIMED_OUT│  (auto-cancel after configurable timeout)
└─────────┘     └──────────┘
```

### LangGraph Implementation

```python
# In agent graph — write tool node
def write_tool_node(state):
    proposed_action = state["proposed_action"]

    # PAUSE — returns control to frontend
    approval = interrupt({
        "action": proposed_action,
        "message": "Review and approve this action",
        "options": ["approve", "edit", "reject"]
    })

    if approval["decision"] == "approve":
        return execute_action(proposed_action)
    elif approval["decision"] == "edit":
        modified = apply_edits(proposed_action, approval["edits"])
        return execute_action(modified)
    else:
        return {"status": "rejected", "message": "Action cancelled by user"}
```

### Checkpoint Persistence

```
PostgreSQL: agent_checkpoints table
├── thread_id (conversation)
├── checkpoint_id (state snapshot)
├── state (serialised AgentState)
├── created_at
└── metadata (pending_approval, action_type, etc.)

→ Survives container restart
→ User can close browser, come back, and approve
```

---

## 5. Evaluation Pipeline Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Eval Pipeline                          │
│                                                          │
│  ┌──────────────┐     ┌──────────────┐     ┌─────────┐  │
│  │ Golden Test   │────→│ Run Agent    │────→│ Score   │  │
│  │ Set (50 Q&A) │     │ (batch mode) │     │ Results │  │
│  └──────────────┘     └──────────────┘     └────┬────┘  │
│                                                  │       │
│                                          ┌───────▼─────┐ │
│                                          │ Metrics     │ │
│                                          │             │ │
│                                          │ Faithfulness│ │
│                                          │ Relevancy   │ │
│                                          │ Correctness │ │
│                                          │ Precision   │ │
│                                          └───────┬─────┘ │
│                                                  │       │
│                                          ┌───────▼─────┐ │
│                                          │ Report +    │ │
│                                          │ Pass/Fail   │ │
│                                          └─────────────┘ │
└─────────────────────────────────────────────────────────┘

Guardrails (runtime):
├── PII detection → mask before sending to Jira/Slack
├── Topic filter → block off-topic requests
├── Hallucination check → cross-ref answer vs KB context
├── Token budget → max per conversation (50k)
└── Loop protection → max 10 iterations
```

---

## 6. Data Flow — Complete Request Lifecycle

```
1. User Input         → Streamlit chat
2. HTTP Request       → FastAPI /chat/stream
3. Router             → classify intent → "action_request"
4. READ Phase         → rag_search (Weaviate) + search_jira (MCP)
5. Plan Phase         → LLM prepares action proposal
6. APPROVAL Phase     → interrupt() → SSE event → Streamlit shows approval panel
7. User Decision      → Approve/Edit/Reject → Command(resume=...)
8. WRITE Phase        → create_jira (MCP) + send_slack (MCP)
9. Response Phase     → LLM summarises outcome
10. Logging           → tool_calls_log, PostgreSQL audit trail
11. Eval (async)      → score faithfulness, relevancy (if eval mode enabled)
```

---

## 7. Port Allocation

| Service | Port | Notes |
|---------|------|-------|
| Streamlit Frontend (project-125) | 8502 | 8501 used by platform-health-agent |
| Agent Backend (FastAPI) | 8010 | 8001 used by platform-health-agent |
| Weaviate | 8080 | Shared from platform-health-agent |
| PostgreSQL | 5432 | Shared from platform-health-agent |

---

## 8. Real-World Entry Points

Our Streamlit UI is a learning/testing frontend. In production, the same agent API
(`/chat`, `/approve`, `/reject`) is triggered from multiple entry points:

```
                    ┌──────────────────────────────────────────────┐
                    │          Agent Backend API (:8010)            │
                    │  POST /chat   POST /approve   POST /reject   │
                    └──────────────┬───────────────────────────────┘
                                   │
          ┌────────────────────────┼────────────────────────────┐
          │                        │                            │
 ┌────────▼─────────┐  ┌──────────▼──────────┐  ┌─────────────▼──────────┐
 │ 1. Chat Bot       │  │ 2. Event/Webhook    │  │ 3. Portal / Dashboard   │
 │ (Slack/Teams)     │  │ (PagerDuty, CW)     │  │ (ServiceNow, Backstage) │
 │                   │  │                     │  │                         │
 │ @bot create       │  │ CloudWatch Alarm    │  │ Internal React app      │
 │ ticket for X      │  │ → Lambda → /chat    │  │ with embedded chat      │
 │                   │  │                     │  │                         │
 │ Approval via      │  │ Auto-approve reads, │  │ Approval via buttons    │
 │ emoji reactions   │  │ page human for      │  │ in the portal UI        │
 │ or Slack buttons  │  │ writes              │  │                         │
 └───────────────────┘  └─────────────────────┘  └─────────────────────────┘
          │                        │                            │
          └────────────────────────┼────────────────────────────┘
                                   │
                    ┌──────────────▼───────────────────────────────┐
                    │          Same tools: RAG + Jira + Slack      │
                    │          Same HITL: interrupt() + resume     │
                    │          Same audit: tool_calls_log          │
                    └──────────────────────────────────────────────┘
```

See `docs/03-real-world-patterns.md` for detailed implementation guidance.

---

*Created 2026-03-26 — Updated 2026-03-27 (added real-world entry points, corrected ports).*
