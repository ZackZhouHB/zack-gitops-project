# 03 — Real-World Implementation Patterns

> How enterprises actually deploy, trigger, and operate AI agent workflows in production.  
> Maps our project-125 learning implementation to real-world architecture decisions.

---

## 1. The Core Insight

**The agent API is the product. The frontend is just a client.**

Our project has:
```
Streamlit UI  ──→  Agent API (:8010)  ──→  [RAG, Jira, Slack]
                   POST /chat
                   POST /approve
                   POST /reject
```

In production, the same API gets called from **multiple entry points simultaneously**:
```
Slack Bot       ─┐
Teams Bot       ─┤
PagerDuty Hook  ─┤──→  Agent API  ──→  [RAG, Jira, Slack, ServiceNow, ...]
CloudWatch Alarm─┤
Portal Widget   ─┤
CLI Tool        ─┘
```

**You don't need "a frontend" — you need the API, and then you connect it to wherever your users already are.**

---

## 2. The Four Entry Points

### 2.1 — Slack/Teams Bot (Most Common for Platform Teams)

**Why**: Engineers already live in Slack. No new tool to learn. Zero adoption friction.

```
┌────────────────────────────────────────────────────────────────────┐
│  #incidents channel                                                │
│                                                                    │
│  @platform-bot investigate the API latency spike on prod           │
│     │                                                              │
│     ▼                                                              │
│  Slack Events API → Lambda/ECS → POST /chat                       │
│     │                                                              │
│     ▼                                                              │
│  Bot replies: "Found 3 related KB docs and 2 Jira tickets.        │
│  I'd like to create a P2 ticket. Details below."                   │
│                                                                    │
│  ┌────────────────────────────────────────────────────────┐        │
│  │ 🎫 Create Ticket: API Latency — Connection Pool       │        │
│  │ Priority: High | Labels: api, latency, pool           │        │
│  │                                                        │        │
│  │  [✅ Approve]  [❌ Reject]  [✏️ Edit]                  │        │
│  └────────────────────────────────────────────────────────┘        │
│                                                                    │
│  Engineer clicks [✅ Approve]                                      │
│     │                                                              │
│     ▼                                                              │
│  Slack Interactivity API → Lambda → POST /chat/{id}/approve        │
│     │                                                              │
│     ▼                                                              │
│  Bot replies: "✅ Created PLAT-142. Notified #platform-alerts."    │
└────────────────────────────────────────────────────────────────────┘
```

**How Approval Works in Slack**:
- Slack "Block Kit" supports interactive buttons natively
- When user clicks a button, Slack sends a POST to your "Interactivity URL"
- Your handler calls `/approve` or `/reject` on the agent API
- No separate approval UI needed — Slack IS the UI

**Implementation Components**:
| Component | What It Does | AWS Service |
|-----------|-------------|-------------|
| Slack App | Receives mentions, sends replies | Slack API |
| Event Handler | Converts Slack events to /chat calls | Lambda or ECS |
| Interactivity Handler | Converts button clicks to /approve calls | Lambda or API Gateway |
| Agent API | Same backend we built | ECS Fargate or EKS |

**Slack App Manifest** (key permissions needed):
```yaml
oauth_config:
  scopes:
    bot:
      - app_mentions:read      # Trigger on @bot
      - chat:write             # Send messages
      - channels:history       # Read context
      - channels:read          # List channels

settings:
  event_subscriptions:
    bot_events:
      - app_mention            # @platform-bot triggers agent
      - message.im             # DM to bot triggers agent
  interactivity:
    is_enabled: true
    request_url: https://your-domain/slack/interactions  # Button clicks
```

**Real Company Examples**:
- Datadog's Bits AI: ChatOps bot for incident investigation
- PagerDuty's AI Operations: Slack-native incident response
- Atlassian Intelligence: Jira/Confluence bot in Slack

---

### 2.2 — Event-Driven / Webhook Triggers (Most Common for Automation)

**Why**: No human needed to start the workflow. Alerts trigger the agent automatically.

```
┌──────────────────────────────────────────────────────────────────────┐
│                        Event-Driven Architecture                      │
│                                                                       │
│  CloudWatch Alarm ─────┐                                              │
│  (CPU > 90%)           │                                              │
│                        │                                              │
│  PagerDuty Incident ───┤    ┌────────────────────┐                    │
│  (P1 created)          ├───→│  Event Router       │                   │
│                        │    │  (EventBridge /     │                   │
│  Datadog Alert ────────┤    │   Lambda / SQS)     │                   │
│  (latency p99 > 5s)   │    └─────────┬──────────┘                    │
│                        │              │                                │
│  GitHub PR merged ─────┘              │ POST /chat                    │
│  (deployment event)                   │ {"message": "CloudWatch:      │
│                                       │  CPU alarm on prod-api-1      │
│                                       │  at 90.2%. Investigate."}     │
│                                       │                                │
│                                       ▼                                │
│                              ┌────────────────┐                       │
│                              │  Agent API      │                       │
│                              │                │                       │
│                              │  1. RAG search  │                       │
│                              │  2. Jira search  │                       │
│                              │  3. Create ticket│ ← auto or HITL      │
│                              │  4. Notify Slack │ ← auto or HITL      │
│                              └────────┬───────┘                       │
│                                       │                                │
│                              Decision: Auto-approve or page human?     │
│                                       │                                │
│                    ┌──────────────────┼──────────────────┐             │
│                    │                  │                   │             │
│              ┌─────▼─────┐    ┌──────▼──────┐    ┌──────▼──────┐      │
│              │ P3/P4:     │    │ P2:          │    │ P1:          │     │
│              │ Auto-create│    │ Page on-call │    │ Auto-create  │     │
│              │ ticket +   │    │ for approval │    │ + page +     │     │
│              │ notify     │    │ via Slack    │    │ start runbook│     │
│              └────────────┘    └─────────────┘    └──────────────┘     │
└──────────────────────────────────────────────────────────────────────┘
```

**Approval Tiers** (a production pattern):

| Alert Severity | Read Actions | Write Actions | Approval |
|----------------|-------------|---------------|----------|
| **P1 Critical** | Auto | Auto-create incident ticket | Auto (no human delay) |
| **P2 High** | Auto | Page on-call engineer in Slack | Human approval via Slack |
| **P3 Medium** | Auto | Create ticket only | Auto-approve tickets, human for Slack |
| **P4 Low** | Auto | Log only | No ticket needed |

**Implementation**:
```python
# Event router Lambda
def handler(event, context):
    severity = event.get("severity", "P4")

    # Always let agent investigate (reads are safe)
    response = requests.post(f"{AGENT_URL}/chat", json={
        "message": f"Investigate: {event['title']}. Details: {event['details']}",
        "conversation_id": event.get("alert_id"),
    })
    data = response.json()

    if data["status"] == "pending_approval":
        if severity == "P1":
            # Auto-approve for P1 — speed matters
            requests.post(f"{AGENT_URL}/chat/{data['conversation_id']}/approve")
        elif severity in ("P2", "P3"):
            # Page on-call via Slack for approval
            notify_oncall_slack(data["conversation_id"], data["pending_action"])
        else:
            # P4: reject write, log only
            requests.post(f"{AGENT_URL}/chat/{data['conversation_id']}/reject")
```

---

### 2.3 — Internal Portal / Dashboard Widget

**Why**: For teams with an existing internal platform (Backstage, ServiceNow, custom React app).

```
┌────────────────────────────────────────────────────────────────────┐
│  Backstage Developer Portal                                         │
│                                                                     │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │  Service: prod-api                                          │     │
│  │  Status: ⚠️ Degraded    SLO: 99.1% (target 99.9%)         │     │
│  │  Recent Incidents: 3 in last 7 days                         │     │
│  │                                                             │     │
│  │  ┌─── AI Assistant ───────────────────────────────────┐     │     │
│  │  │                                                     │     │     │
│  │  │  You: "Why is prod-api degraded? Check the          │     │     │
│  │  │        knowledge base and recent Jira tickets."     │     │     │
│  │  │                                                     │     │     │
│  │  │  Agent: Based on KB and 3 Jira tickets, the root    │     │     │
│  │  │  cause is connection pool exhaustion. I found:      │     │     │
│  │  │  - KB: Runbook for pool tuning (85% match)          │     │     │
│  │  │  - PLAT-139: Same issue reported last week          │     │     │
│  │  │                                                     │     │     │
│  │  │  I'd like to add a comment to PLAT-139 with this    │     │     │
│  │  │  analysis.                                          │     │     │
│  │  │                                                     │     │     │
│  │  │  [✅ Approve] [❌ Skip]                             │     │     │
│  │  │                                                     │     │     │
│  │  └─────────────────────────────────────────────────────┘     │     │
│  └────────────────────────────────────────────────────────────┘     │
└────────────────────────────────────────────────────────────────────┘
```

**Implementation**: A React component that calls the same Agent API:
```jsx
// Simplified React component
function AIAssistant({ serviceId }) {
  const [threadId, setThreadId] = useState(null);
  const [pendingAction, setPendingAction] = useState(null);

  async function sendMessage(text) {
    const res = await fetch('/api/agent/chat', {
      method: 'POST',
      body: JSON.stringify({ message: text }),
    });
    const data = await res.json();

    if (data.status === 'pending_approval') {
      setThreadId(data.conversation_id);
      setPendingAction(data.pending_action);
    }
  }

  async function handleApprove() {
    await fetch(`/api/agent/chat/${threadId}/approve`, { method: 'POST' });
    setPendingAction(null);
  }

  // ... render chat messages + approval buttons
}
```

---

### 2.4 — CLI / API-First (for Platform Engineers)

**Why**: Some teams prefer CLI tools. Quick, scriptable, integrates with existing automation.

```bash
# Direct CLI usage
$ platform-health ask "What's the status of the EKS RAG system?"
🔍 Searching KB... Found 5 relevant docs
📋 Searching Jira... Found 2 open tickets
> The EKS RAG system has 2 known issues: SCRUM-9 (OOMKilled) and SCRUM-18 (memory overflow)...

# With auto-approve for read-only
$ platform-health create-ticket \
    --title "Redis cache miss rate > 50%" \
    --priority High \
    --search-kb-first
🔍 Searching KB for context... Found runbook
🔍 Checking Jira for duplicates... None found
⏸️  Proposed ticket:
    Summary: Redis cache miss rate > 50%
    Priority: High
    Labels: redis, cache, performance
    [Approve? y/n/edit]: y
✅ Created SCRUM-25: https://zhbsoftboy1.atlassian.net/browse/SCRUM-25

# In a CI/CD pipeline (auto-approve)
$ platform-health chat \
    --message "Deployment to prod failed: ${ERROR}" \
    --auto-approve \
    --output json
```

---

## 3. Architecture Decision: What Goes Where

### 3.1 — Agent API (The Core — Always the Same)

This is what we built. It never changes regardless of entry point:

```
Agent API
├── POST /chat              ← Any client can call this
├── POST /chat/{id}/approve ← Any client can approve
├── POST /chat/{id}/reject  ← Any client can reject
├── POST /chat/{id}/edit    ← Any client can edit+approve
├── GET  /chat/{id}/status  ← Any client can poll
└── GET  /health            ← Monitoring
```

### 3.2 — Entry Point Adapters (Thin Layers)

Each entry point is a **thin adapter** that translates platform-specific events to Agent API calls:

| Adapter | Input | Output | Complexity |
|---------|-------|--------|------------|
| Slack Bot | Slack Events API → `/chat` | Agent response → Slack message | ~200 lines |
| PagerDuty Hook | Webhook → `/chat` | Agent response → PagerDuty note | ~100 lines |
| Portal Widget | React form → `/chat` | JSON → React component | ~150 lines |
| CLI | Terminal args → `/chat` | JSON → formatted output | ~100 lines |
| Streamlit (ours) | Chat input → `/chat` | JSON → Streamlit widgets | ~300 lines |

**The adapters are simple because all the intelligence is in the Agent API.**

### 3.3 — What a Production Deployment Looks Like

```
┌──────────────────────────────────────────────────────────────────┐
│  AWS Account (Production)                                         │
│                                                                   │
│  ┌─────────────┐    ┌──────────────────────────────────────────┐  │
│  │ API Gateway  │───→│  ECS Fargate / EKS                       │  │
│  │ (HTTPS)      │    │                                          │  │
│  │              │    │  ┌──────────────────────────────────┐    │  │
│  │ /slack/*     │    │  │  Agent API Container              │    │  │
│  │ /webhook/*   │    │  │  - FastAPI + LangGraph            │    │  │
│  │ /api/*       │    │  │  - HITL (interrupt + resume)      │    │  │
│  │              │    │  │  - 12 tools                       │    │  │
│  └─────────────┘    │  └──────────────────────────────────┘    │  │
│                      │                                          │  │
│  ┌─────────────┐    │  ┌──────────────────────────────────┐    │  │
│  │ EventBridge │────│  │  Slack Bot Handler (Lambda)       │    │  │
│  │ (CloudWatch │    │  │  - @mention → /chat               │    │  │
│  │  alarms)    │    │  │  - Button click → /approve        │    │  │
│  └─────────────┘    │  └──────────────────────────────────┘    │  │
│                      │                                          │  │
│  ┌─────────────┐    │  ┌──────────────────────────────────┐    │  │
│  │ OpenSearch / │    │  │  PostgreSQL (RDS)                 │    │  │
│  │ Weaviate     │    │  │  - Checkpoints (HITL state)       │    │  │
│  │ (Vector DB)  │    │  │  - Audit logs                     │    │  │
│  └─────────────┘    │  │  - Eval results                    │    │  │
│                      │  └──────────────────────────────────┘    │  │
│  ┌─────────────┐    └──────────────────────────────────────────┘  │
│  │ Bedrock     │                                                  │
│  │ - Claude    │    ┌──────────────────────────────────────────┐  │
│  │ - Titan     │    │  Monitoring                               │  │
│  │ - Guardrails│    │  - CloudWatch (latency, errors)           │  │
│  └─────────────┘    │  - X-Ray (tool call tracing)              │  │
│                      │  - Cost Explorer (Bedrock spend)          │  │
│                      └──────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 4. Comparing: Our Project vs Production

| Aspect | Our Project (Learning) | Enterprise (Production) |
|--------|----------------------|------------------------|
| **Agent API** | FastAPI on localhost:8010 | ECS Fargate behind API Gateway + ALB |
| **Entry point** | Streamlit chat UI | Slack bot + webhooks + portal widget |
| **Approval UI** | Streamlit buttons | Slack Block Kit buttons + portal buttons |
| **Vector DB** | Weaviate (Docker) | OpenSearch Serverless or Weaviate on EKS |
| **Checkpointer** | MemorySaver (in-memory) | PostgreSQL (RDS) — survives restarts |
| **Auth** | None | AWS IAM + SSO + RBAC (who can approve) |
| **Secrets** | .env file | AWS Secrets Manager |
| **LLM** | Bedrock (single region) | Bedrock (multi-region with fallback) |
| **KB / RAG** | 24 docs, 198 chunks | 10K+ docs, auto-sync from Confluence/S3 |
| **Monitoring** | Print logs | CloudWatch + X-Ray + Bedrock cost alerts |
| **Eval** | Manual E2E script | CI/CD pipeline: run golden tests on every PR |
| **Guardrails** | Basic (loop limit) | Bedrock Guardrails (PII, topic, toxicity) |

**Key takeaway**: The architecture is the same. Production adds infrastructure concerns (auth, monitoring, persistence, scaling) around the same core agent pattern.

---

## 5. Migration Path: Learning → Production

### Phase 1: What We Built (✅ Done)
```
Local Docker → FastAPI → LangGraph → [RAG + Jira + Slack]
                 ↓
           Streamlit UI (testing)
```

### Phase 2: Add Slack Bot Entry Point
```
Slack Events API → Lambda → Agent API (same FastAPI)
Slack Interactivity → Lambda → /approve, /reject
```
- 200 lines of Lambda code
- Slack App manifest + permissions
- API Gateway for HTTPS endpoint

### Phase 3: Add Event-Driven Triggers
```
CloudWatch Alarm → EventBridge → Lambda → Agent API
PagerDuty Webhook → API Gateway → Lambda → Agent API
```
- Event router Lambda with severity-based approval tiers
- Auto-approve for P4, page human for P1-P3

### Phase 4: Production Infrastructure
```
- ECS Fargate (agent API)
- RDS PostgreSQL (checkpoints + audit)
- Secrets Manager (credentials)
- CloudWatch + X-Ray (monitoring)
- Bedrock Guardrails (safety)
```

### Phase 5: Scale & Governance
```
- Multi-team: RBAC (only incident commanders can approve P1)
- Multi-agent: different agents for different domains
- Cost controls: Bedrock token budgets per team
- Compliance: audit trail, PII masking, data residency
```

---

## 6. Common Enterprise Integration Patterns

### 6.1 — ServiceNow + AI Agent
```
ServiceNow Incident → Webhook → Agent API
Agent → KB search + enrichment → Update ServiceNow ticket fields
Agent → Slack notification to resolver group
```

### 6.2 — PagerDuty + AI Agent
```
PagerDuty Alert → Webhook → Agent API
Agent → KB search for runbook → Post runbook link to PagerDuty timeline
Agent → Check if Jira ticket exists → Create if not
Agent → Summarize impact for incident commander
```

### 6.3 — Backstage + AI Agent
```
Developer in Backstage → Service page → "Ask AI" widget
Agent → KB search for service docs → Show architecture context
Agent → Jira search for known issues → Display inline
Developer → "Create ticket for this" → HITL approval
```

### 6.4 — GitHub Actions + AI Agent
```
CI/CD Pipeline fails → GitHub webhook → Agent API
Agent → KB search for similar failures → Find past fix
Agent → Create Jira ticket with failure details + suggested fix
Agent → Post to PR as a comment with KB context
```

---

## 7. Key Principles for Production AI Agents

### 7.1 — The API is the Product
Build the agent as an API first. Frontends are just clients. This lets you add new entry points (Slack, Teams, portal, CLI) without changing the agent.

### 7.2 — Approval Tiers, Not All-or-Nothing
Not every action needs human approval. Design tiers:
- **Auto-approve**: Read actions, low-risk writes (add comment, update label)
- **Human-approve**: High-risk writes (create P1 incident, send to #all-engineering)
- **Admin-only**: Destructive actions (delete ticket, close incident)

### 7.3 — Audit Everything
Every tool call, every approval decision, every LLM response goes into an audit log. This is non-negotiable for enterprise compliance.

### 7.4 — Degrade Gracefully
If Bedrock is down → return KB results without LLM summary.
If Jira is down → log the intended action, retry later.
If approval times out → auto-reject and notify.

### 7.5 — The Agent Doesn't Replace Humans
The agent **accelerates** humans. It gathers context (KB + Jira), drafts actions (tickets, messages), and presents them for approval. The human makes the final decision. This is not just safety — it builds trust and drives adoption.

---

*Created 2026-03-27 — Real-world implementation patterns for AI agent workflows.*
