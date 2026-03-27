# Implementation Plan — Project 125

> **Build Order**: Phase A → B → C → D → E → F  
> **Estimated Tutorials**: step-19 through step-24 (continuing from platform-health-agent series)  
> **Prerequisite**: platform-health-agent local stack running (Weaviate + PostgreSQL + Agent)

---

## Phase A: Project Scaffolding ✅

**Goal**: Set up project structure, documentation, git repo.

| Task | Description |
|------|-------------|
| Create folder structure | docs/, agent-backend/, mcp-servers/, frontend/, tutorials/ |
| Create design docs | 01-project-overview, 02-architecture, 06-implementation-plan |
| Create SESSION-HANDOFF.md | Initial state with architecture and milestones |
| Create TROUBLESHOOTING.md | Empty template ready for issues |
| Create config files | .env.example, .gitignore, docker-compose.yml |
| Git init + initial commit | Version control from day 1 |

---

## Phase B: Jira & Slack API Fundamentals

**Goal**: Understand the external APIs before building tools or MCP servers. Plain Python scripts — no agent, no LangGraph.

### B1: Jira Cloud Setup & API Scripts

| Task | Description |
|------|-------------|
| Create Jira Cloud site | Free tier at atlassian.com/try |
| Generate API token | atlassian.com/manage-profile/security/api-tokens |
| Create a test project | e.g., "PLAT" for Platform Health |
| Write `scripts/jira_test.py` | Create ticket, search (JQL), update, get ticket |
| Test all CRUD operations | Verify each API call works standalone |
| Write tutorial: step-19 | `step-19-jira-api-basics.md` |

**Key API calls to implement:**
```python
# All via requests.post/get to https://your-site.atlassian.net/rest/api/3/

# 1. Create ticket
POST /rest/api/3/issue
{ "fields": { "project": {"key": "PLAT"}, "summary": "...", "issuetype": {"name": "Task"} } }

# 2. Search (JQL)
GET /rest/api/3/search?jql=project=PLAT AND status="Open"

# 3. Update ticket
PUT /rest/api/3/issue/{issueKey}

# 4. Get ticket details
GET /rest/api/3/issue/{issueKey}
```

### B2: Slack Workspace Setup & API Scripts

| Task | Description |
|------|-------------|
| Create Slack workspace | Free at slack.com/create |
| Create Slack app + bot | api.slack.com → Create New App |
| Configure OAuth scopes | chat:write, channels:read, channels:history |
| Install to workspace | Get bot token (xoxb-...) |
| Create test channels | #platform-alerts, #incidents |
| Write `scripts/slack_test.py` | Send message, list channels, create thread |
| Test all operations | Verify each API call works standalone |
| Write tutorial: step-20 | `step-20-slack-api-basics.md` |

**Key API calls to implement:**
```python
# All via requests.post to https://slack.com/api/

# 1. Send message
POST /api/chat.postMessage
{ "channel": "#platform-alerts", "text": "..." }

# 2. List channels
GET /api/conversations.list

# 3. Reply in thread
POST /api/chat.postMessage
{ "channel": "C123...", "thread_ts": "1234567890.123456", "text": "..." }
```

---

## Phase C: MCP Servers

**Goal**: Wrap the Jira and Slack APIs as MCP-compliant servers that any agent can use.

| Task | Description |
|------|-------------|
| Study MCP protocol | Read spec at modelcontextprotocol.io |
| Build Jira MCP server | `mcp-servers/jira-server/server.py` — expose search, create, update as MCP tools |
| Build Slack MCP server | `mcp-servers/slack-server/server.py` — expose send_message, create_thread, list_channels |
| Test servers standalone | Run each server, call tools via MCP client |
| Write tutorial: step-21 | `step-21-mcp-servers.md` — what MCP is, why, how to build one |

### MCP Server Structure (per server)
```
mcp-servers/jira-server/
├── server.py          # MCP server with @mcp.tool() decorators
├── jira_client.py     # Raw REST API wrapper (from Phase B scripts)
├── config.py          # JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN
├── requirements.txt   # mcp, requests
└── README.md
```

---

## Phase D: Action Agent Integration

**Goal**: Wire MCP tools into the LangGraph agent alongside existing RAG tools. Add confirmation flow.

| Task | Description |
|------|-------------|
| Add MCP client to agent | Connect to Jira + Slack MCP servers |
| Register MCP tools in graph | Agent sees: rag_search, search_jira, create_ticket, send_slack, etc. |
| Update system prompt | Tell agent when to use each tool, read-before-write pattern |
| Implement confirmation flow | Agent proposes action → user confirms → agent executes |
| Implement duplicate detection | search_jira before create_ticket (idempotency) |
| Implement error recovery | Handle partial failures (Jira ok, Slack fails) |
| E2E test suite | 5 test scenarios (see below) |
| Write tutorial: step-22 | `step-22-action-agent.md` |

### E2E Test Scenarios
1. "Create a ticket for the database connection timeout issue"
2. "Find all open P1 incidents from this week"
3. "Notify the team in #platform-alerts about the EKS scaling issue"
4. "Create a ticket and notify Slack" (multi-tool chain with confirmation)
5. Error case: invalid project key / expired token / rate limited

---

## Phase E: Human-in-the-Loop Approval

**Goal**: Production-grade approval workflow using LangGraph interrupt/resume.

| Task | Description |
|------|-------------|
| Study LangGraph interrupt() | Docs + examples for interrupt/Command patterns |
| Implement interrupt in write tools | Pause before any write action |
| Build approval UI in Streamlit | Approve / Edit / Reject panel with action preview |
| Implement persistent checkpointing | PostgreSQL-backed, survives container restart |
| Implement edit flow | User modifies proposed action, agent adjusts |
| Implement timeout handling | Auto-cancel if no response in configurable time |
| Implement multi-step approval | Step 1 → Approve → Step 2 → Approve → Execute |
| Write tutorial: step-23 | `step-23-hitl-approval.md` |

### Test Scenarios
1. Approve flow (happy path)
2. Reject flow (agent acknowledges and stops)
3. Edit flow (user changes priority, agent re-plans)
4. Timeout flow (no response in X minutes → auto-cancel)
5. Resume after container restart (checkpoint recovery)

---

## Phase F: Evaluation & Guardrails

**Goal**: Automated quality measurement + runtime safety guards.

| Task | Description |
|------|-------------|
| Create golden test set | 50 questions with expected answers and sources |
| Set up RAGAS framework | Faithfulness, relevancy, answer correctness, context precision |
| Build eval runner | Batch mode: run all 50 tests, score, generate report |
| Implement Bedrock Guardrails | PII detection, topic filtering, hallucination detection |
| Implement token budget guards | Max tokens per conversation, alert on runaway loops |
| Build eval dashboard | Streamlit page showing metrics over time |
| Write tutorial: step-24 | `step-24-eval-guardrails.md` |

### Quality Thresholds
| Metric | Minimum | Target |
|--------|---------|--------|
| Faithfulness | 0.70 | 0.85+ |
| Relevancy | 0.65 | 0.80+ |
| Answer Correctness | 0.60 | 0.75+ |
| Error Rate | <5% | <2% |

---

## Tutorial Index

| Step | Title | Phase | What You Learn |
|------|-------|-------|---------------|
| 19 | Jira API Basics | B | REST API, authentication, CRUD operations |
| 20 | Slack API Basics | B | Bot tokens, OAuth scopes, messaging API |
| 21 | Building MCP Servers | C | MCP protocol, tool exposure, server testing |
| 22 | Action Agent Integration | D | Multi-tool agent, confirmation, error recovery |
| 23 | Human-in-the-Loop | E | LangGraph interrupt, approval UI, checkpointing |
| 24 | Eval & Guardrails | F | RAGAS, golden tests, Bedrock Guardrails |

---

*Created 2026-03-26 — Implementation plan for Project 125 (P1 + P2 + P5)*
