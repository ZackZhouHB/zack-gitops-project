# Roadmap Progress Report — From 7 Projects to Production AI Agent

> **Date**: 2026-03-27  
> **Source Roadmap**: `aws-deploy/FUTURE-ROADMAP.md` (7 projects, created after RAG + AWS deployment)  
> **Current State**: P1 + P2 + P5 complete in `project-125/`, P3 designed and ready to build  
> **Next Session**: Build P3 (Multi-Agent Supervisor) on top of existing project-125

---

## 1. Roadmap Overview — Where We Started

The FUTURE-ROADMAP defined 7 projects to evolve from "RAG chatbot" to "production AI agent engineer":

```
Recommended order: P1 → P2 → P5 → P3 → P4 → P6 → P7

P1: Jira/Slack Action Agent     ← DONE ✅
P2: Human-in-the-Loop           ← DONE ✅  
P5: Eval & Guardrails           ← DONE ✅
P3: Multi-Agent Supervisor      ← NEXT 📋 (designed, ready to build)
P4: Scheduled/Long-Running      ← Not started
P6: Memory & Personalisation    ← Not started
P7: Multi-Modal (Vision+Code)   ← Not started
```

---

## 2. What We Completed (P1 + P2 + P5 + Extras)

### P1: Jira/Slack Action Agent — ✅ 95% Complete

| Roadmap Task | Status | Evidence |
|-------------|--------|---------|
| Jira Cloud API + API token | ✅ | zhbsoftboy1.atlassian.net, 8/8 tests |
| `create_jira_ticket` tool | ✅ | create_ticket in graph.py |
| `search_jira_issues` tool | ✅ | search_issues with JQL |
| `update_jira_ticket` tool | ✅ | update_ticket (priority, labels, summary) |
| Slack workspace + bot token | ✅ | platform_health_bot, 6/6 tests |
| `send_slack_message` tool | ✅ | send_message, create_thread, reply_in_thread |
| `create_slack_thread` tool | ✅ | create_thread (summary + details) |
| Confirmation flow | ✅ | HITL interrupt() — automatic pause on write tools |
| Rollback pattern | ❌ | Not implemented — if Jira succeeds but Slack fails, no rollback |
| Idempotency | ❌ | Not implemented — duplicate requests could create duplicate tickets |
| E2E multi-tool flow | ✅ | 15/15 test scenarios passing |
| Error handling | ✅ | Graceful API error handling, 12 issues documented |

**What went beyond roadmap**: MCP servers (Jira + Slack), web search tool (#12), Slack bot entry point

### P2: Human-in-the-Loop — ✅ 90% Complete

| Roadmap Task | Status | Evidence |
|-------------|--------|---------|
| LangGraph interrupt() + Command | ✅ | interrupt() in tool_node, Command(resume=...) |
| Approval workflow | ✅ | Approve / Reject / Edit flows all working |
| Persistent checkpointing | ❌ | Using MemorySaver (in-memory) — lost on restart |
| Approval dashboard | ✅ | Streamlit chat UI + HITL panel on :8502 |
| Timeout handling | ❌ | No auto-cancel if no approval in X minutes |
| Multi-step approval | Partial | Sequential write tools pause individually |

**What went beyond roadmap**: Slack bot with interactive Approve/Reject buttons in Block Kit

### P5: Eval & Guardrails — ✅ 85% Complete

| Roadmap Task | Status | Evidence |
|-------------|--------|---------|
| Golden test set | ✅ | 22 tests across 5 categories |
| Faithfulness metric | ✅ | Heuristic-based (keyword overlap) |
| Relevancy metric | ✅ | Source relevance scoring |
| Answer correctness | ✅ | Keyword matching against expected |
| PII detection + masking | ✅ | 6 regex patterns (SSN, CC, email, phone, AWS key, IP) |
| Topic filtering | ✅ | Block off-topic queries (weather, sports, etc.) |
| Token budget guardrails | ✅ | Max tokens per conversation |
| Hallucination detection | ✅ | Cross-check answer vs retrieved context |
| RAGAS/DeepEval framework | ❌ | Using custom eval, not industry frameworks |
| A/B test framework | ❌ | Not implemented |
| CI/CD integration | ❌ | Eval not in deployment pipeline |

### Extras (Not in Original Roadmap)

| Feature | Description |
|---------|-------------|
| **Web search (tool #12)** | DuckDuckGo for real-time info when KB is outdated |
| **Slack bot entry point** | Socket Mode — trigger agent from Slack @mentions |
| **Docker containerisation** | 6-service stack, 17/17 validation tests |
| **MCP protocol servers** | Jira + Slack as MCP streamable-http servers |
| **Comprehensive docs** | 9 tutorials, 9 design docs, 12 troubleshooting issues |

---

## 3. Current System Architecture

```
Docker Compose (6 services)
├── vectordb (:8080)          — Weaviate with 198 chunks from 24 docs
├── postgres (:5432)          — PostgreSQL for state
├── jira-mcp (:8002)          — Jira MCP Server (5 tools)
├── slack-mcp (:8003)         — Slack MCP Server (5 tools)
├── agent-backend (:8010)     — FastAPI + LangGraph (12 tools, HITL, guardrails)
└── frontend (:8502)          — Streamlit chat + approval panel

External:
├── AWS Bedrock (ap-southeast-2) — Claude Sonnet 4 + Titan Embed V2
├── Jira Cloud — REST API v3
├── Slack — Web API + Socket Mode
└── DuckDuckGo — Web search

Entry Points:
├── Streamlit UI (:8502)      — Development & demos
├── Slack Bot (Socket Mode)    — Team collaboration (5/5 tests passing)
└── Direct API (:8010)         — Automation & testing
```

### Tool Inventory (12 Tools)

| # | Tool | Source | Type | HITL |
|---|------|--------|------|------|
| 1 | rag_search | Weaviate | Read | No |
| 2 | search_issues | Jira | Read | No |
| 3 | get_ticket | Jira | Read | No |
| 4 | create_ticket | Jira | Write | ✅ Yes |
| 5 | update_ticket | Jira | Write | ✅ Yes |
| 6 | add_comment | Jira | Write | ✅ Yes |
| 7 | web_search | DuckDuckGo | Read | No |
| 8 | send_message | Slack | Write | ✅ Yes |
| 9 | create_thread | Slack | Write | ✅ Yes |
| 10 | reply_in_thread | Slack | Write | ✅ Yes |
| 11 | send_rich_notification | Slack | Write | ✅ Yes |
| 12 | list_channels | Slack | Read | No |

---

## 4. What's Next — P3: Multi-Agent Supervisor

### Why P3 Is the Right Next Step

1. **Natural evolution**: Single agent with 12 tools → specialised agents coordinated by a supervisor
2. **Same stack**: LangGraph, Bedrock, Weaviate, Jira, Slack — zero new infrastructure
3. **Additive**: Existing `/chat` endpoint stays untouched — new `/chat/multi` alongside it
4. **~950 lines of new code**: Not a rewrite, an extension

### What Changes

```
BEFORE (current — single agent):
  User → LLM (12 tools) → tool_node → LLM → ... → END

AFTER (multi-agent supervisor):
  User → Supervisor → Research Agent (rag, jira read, web search)
                     → Action Agent (jira write, slack write) + HITL
                     → Report Agent (summarise, format)
```

### Design Doc

Full architecture, implementation phases, design decisions, test scenarios, and risk mitigations are in:

📄 **`project-125/docs/07-multi-agent-supervisor-plan.md`**

### Implementation Phases (3 phases + MCP)

| Phase | Goal | Key Deliverables |
|-------|------|-----------------|
| **G: Supervisor Foundation** | Supervisor routes to Research Agent + MCP client | `supervisor.py`, `research_agent.py`, `multi_state.py`, `mcp_client.py`, `/chat/multi` endpoint |
| **H: Action + Report Agents** | Full 3-agent pipeline E2E via MCP | Action Agent, Report Agent, HITL propagation, all tools via MCP protocol |
| **I: Testing & Polish** | Validation, MCP discovery test, docs, Docker | 10+ test scenarios, MCP auto-discovery test, tutorial step-26, handoff update |

### What We Reuse (90%)

| Component | Reuse |
|-----------|-------|
| Bedrock Claude | ✅ Same model, each agent gets its own prompt |
| Weaviate RAG | ✅ Research Agent calls same rag_search |
| Jira/Slack clients | ✅ Action Agent uses same 10 tools |
| HITL interrupt() | ✅ Works in nested sub-graphs |
| Guardrails | ✅ Same input/output checks on supervisor entry |
| Docker stack | ✅ No new containers — just more Python code |
| Streamlit UI | ✅ Minor update to show which agent is active |

### What's New (~10%)

| Component | Location | Lines |
|-----------|----------|-------|
| Supervisor graph | `agent/supervisor.py` | ~200 |
| Research Agent | `agent/research_agent.py` | ~100 |
| Report Agent | `agent/report_agent.py` | ~80 |
| Shared state | `agent/multi_state.py` | ~30 |
| Supervisor prompt | `agent/prompts.py` | ~50 |
| API endpoint | `main.py` (+/chat/multi) | ~40 |
| Tests | `scripts/multi_agent_test.py` | ~150 |
| Tutorial | `tutorials/step-26-*.md` | ~300 |

### Key Test Scenario

**User**: "Investigate the high error rate on payment API, create an incident ticket, and notify the team"

```
1. Supervisor decomposes → 3 sub-tasks
2. Research Agent → rag_search + search_issues → findings
3. Action Agent → create_ticket → HITL pause → user approves → SCRUM-27
4. Report Agent → formats summary → send_message to Slack → HITL → approve
5. Supervisor → returns final response with ticket link + Slack confirmation
```

---

## 5. Remaining Roadmap (P4, P6, P7)

### P4: Scheduled/Long-Running Agent
- **Dependency**: P3 (supervisor can delegate to scheduled tasks)
- **Key skills**: Background execution, cron/EventBridge triggers, progress reporting
- **Example**: Nightly KB freshness scan, weekly cost analysis report

### P6: Memory & Personalisation
- **Dependency**: None (can build anytime)
- **Key skills**: LangGraph Store, cross-session memory, user profiles
- **Example**: "You usually ask about EKS — here's what's changed since last time"

### P7: Multi-Modal Agent
- **Dependency**: P3 (Vision Agent becomes another sub-agent)
- **Key skills**: Claude Vision API, code execution sandbox, file upload
- **Example**: User uploads error screenshot → agent diagnoses + creates ticket

### Recommended Order

```
Tomorrow:     P3 (Multi-Agent Supervisor)  ← builds on everything we have
Then:         P6 (Memory)                  ← makes agents smarter over time
Then:         P4 (Scheduled)               ← leverages P3 supervisor
Stretch:      P7 (Multi-Modal)             ← most complex, least urgent
```

---

## 6. Gaps to Address (Across All Completed Projects)

| Gap | Project | Priority | Effort |
|-----|---------|----------|--------|
| Rollback pattern | P1 | Medium | ~2 hours |
| Idempotency | P1 | Medium | ~2 hours |
| Persistent checkpoints (PostgresSaver) | P2 | High | ~1 hour |
| Timeout handling | P2 | Medium | ~1 hour |
| RAGAS/DeepEval integration | P5 | Medium | ~3 hours |
| CI/CD eval pipeline | P5 | Low | ~4 hours |
| LangSmith/OpenTelemetry tracing | All | High | ~3 hours |
| Golden test set expansion (22 → 50) | P5 | Low | ~2 hours |

These can be addressed as enhancements alongside P3 or after.

---

## 6.1 MCP Gap — What We Built vs What MCP Really Means

### What MCP (Model Context Protocol) Is

MCP is a **standard protocol** for tools to expose capabilities to AI agents — like USB for AI. Instead of hardcoding tool functions, agents discover tools dynamically from MCP servers at runtime.

```
The MCP Vision:
  Agent → "What tools do you have?" → MCP Server → "I have create_ticket, search_issues, ..."
  Agent → "Call create_ticket({summary: ...})" → MCP Server → executes → returns result

  Benefits:
  - Agent doesn't need to know implementation details
  - Add new MCP servers without changing agent code
  - Same protocol works for any tool provider (Jira, Slack, PagerDuty, Datadog...)
  - Tools are discoverable, not hardcoded
```

### What We Actually Built

We built **MCP servers** but the **agent bypasses the MCP protocol**:

```
WHAT WE HAVE (current — partial MCP):

  ┌────────────────────┐     ┌──────────────────┐
  │  Agent (graph.py)  │     │  Jira MCP Server  │
  │                    │     │  (:8002)           │
  │  import            │     │                    │
  │  jira_client.py ──────→  │  Jira REST API     │
  │                    │  ↗  │                    │
  │  (bypasses MCP     │ │   └──────────────────┘
  │   protocol entirely)│ │
  │                    │ │   ┌──────────────────┐
  │  import            │ │   │  Slack MCP Server │
  │  slack_client.py ────┘   │  (:8003)          │
  │                    │     │                    │
  └────────────────────┘     └──────────────────┘

  ⚠️ MCP servers are running in Docker but the agent
     imports the client modules directly as Python code.
     The MCP HTTP endpoints on :8002/:8003 are unused by the agent.


WHAT FULL MCP LOOKS LIKE (target):

  ┌────────────────────┐     ┌──────────────────┐
  │  Agent (graph.py)  │     │  Jira MCP Server  │
  │                    │     │  (:8002)           │
  │  MCP Client ───HTTP──→   │                    │
  │  1. List tools     │     │  • search_issues   │
  │  2. Call tool      │     │  • create_ticket   │
  │  3. Get result     │     │  • get_ticket      │
  │                    │     │  • update_ticket   │
  │  MCP Client ───HTTP──→   │  • add_comment     │
  │                    │     └──────────────────┘
  │                    │
  │                    │     ┌──────────────────┐
  │                    │     │  Slack MCP Server │
  │  (same MCP Client)──→   │  (:8003)          │
  │                    │     │                    │
  └────────────────────┘     │  • send_message   │
                             │  • create_thread  │
                             │  • list_channels  │
                             └──────────────────┘

  ✅ Agent discovers tools dynamically via MCP protocol
  ✅ Adding a new MCP server = agent auto-discovers new tools
  ✅ No code changes in agent when tools change
```

### What's Missing (Specific Gaps)

| Gap | What It Means | Impact |
|-----|--------------|--------|
| **No MCP client in agent** | Agent imports Python modules directly, doesn't use MCP HTTP transport | Tools are hardcoded, not discovered |
| **No tool discovery** | Tool definitions are manually written in `_build_tool_definitions()` | Adding a tool = editing graph.py |
| **No protocol negotiation** | Agent doesn't call MCP server's `/mcp/v1/tools/list` endpoint | Can't auto-detect available tools |
| **MCP servers are underused** | Servers run and expose HTTP endpoints, but nothing calls them via MCP | Docker resources wasted |
| **No dynamic tool registration** | If someone deploys a PagerDuty MCP server on :8004, agent won't know | No plug-and-play capability |

### Why This Matters for AI Agent Engineering

In interviews and real-world architectures, MCP is becoming the standard:

```
Without MCP (what we have):
  - Add Datadog tool → edit graph.py, add tool def, add execution handler, redeploy
  - Add PagerDuty tool → same manual process
  - 5 new tools = 5 code changes to agent

With MCP (industry standard):
  - Add Datadog tool → deploy datadog-mcp-server on :8004 → agent auto-discovers
  - Add PagerDuty tool → deploy pagerduty-mcp-server on :8005 → agent auto-discovers
  - 5 new tools = 5 new containers, ZERO changes to agent code
```

---

## 6.2 Plan: Fix MCP Gap Alongside P3

The MCP fix naturally fits into the Multi-Agent Supervisor work. Here's how:

### Approach: Build an MCP Client That Discovers Tools at Startup

```python
# NEW: agent/mcp_client.py — generic MCP client
class MCPToolDiscovery:
    """Discover tools from MCP servers at startup."""
    
    def __init__(self, servers: list[dict]):
        # servers = [{"name": "jira", "url": "http://jira-mcp:8002"}, ...]
        self.servers = servers
        self.tools = {}   # tool_name → {server_url, definition}
    
    async def discover(self):
        """Call each MCP server to list available tools."""
        for server in self.servers:
            tools = await self._list_tools(server["url"])
            for tool in tools:
                self.tools[tool["name"]] = {
                    "server": server["url"],
                    "definition": tool,
                }
    
    async def call_tool(self, tool_name: str, args: dict) -> dict:
        """Call a tool via MCP protocol on the correct server."""
        server_url = self.tools[tool_name]["server"]
        return await self._invoke_tool(server_url, tool_name, args)
```

### Integration with P3 Phases

| Phase | MCP Work | Alongside |
|-------|----------|-----------|
| **G (Supervisor Foundation)** | Build `mcp_client.py`, discover tools from Jira + Slack MCP servers at startup | Building supervisor.py |
| **H (Action + Report Agents)** | Research Agent + Action Agent use MCP client instead of direct imports | Wiring sub-agents |
| **I (Testing & Polish)** | Test: deploy a mock MCP server → agent auto-discovers new tools | Validation |

### What This Gives Us

| Before (Current) | After (With MCP Client) |
|-------------------|------------------------|
| `from clients.jira_client import JiraClient` | `mcp = MCPToolDiscovery([{"url": "http://jira-mcp:8002"}, ...])` |
| 12 tool definitions hardcoded in graph.py | Tools discovered dynamically from MCP servers |
| Adding a tool = edit Python code | Adding a tool = deploy new MCP server container |
| Agent restart needed for tool changes | Agent discovers new tools on startup (or hot-reload) |

### Config-Driven Tool Discovery

```yaml
# docker-compose.yml (or config.py)
MCP_SERVERS:
  - name: jira
    url: http://jira-mcp:8002
  - name: slack
    url: http://slack-mcp:8003
  - name: pagerduty          # ← just add a new entry
    url: http://pagerduty-mcp:8004
```

Agent reads this config → discovers tools from all servers → builds tool definitions automatically. **Zero code changes to add new tool providers.**

---

## 7. Files to Read Tomorrow

### To Resume Work

| Order | File | Why |
|-------|------|-----|
| 1 | **This file** (`docs/10-roadmap-progress-report.md`) | Big picture — where we are, what's next |
| 2 | `SESSION-HANDOFF.md` | Technical state — ports, credentials, Docker status |
| 3 | `docs/07-multi-agent-supervisor-plan.md` | P3 design — architecture, phases, code structure |
| 4 | `agent-backend/agent/graph.py` | Current agent — becomes the Action Agent sub-graph |
| 5 | `agent-backend/agent/prompts.py` | Current system prompt — need supervisor prompt |

### Quick Start

```bash
cd ~/zz/Documents/conversation-ai/project-125

# Start everything
docker compose up -d
docker compose ps          # Verify 6 containers healthy

# Verify agent
curl -s localhost:8010/health | python3 -m json.tool   # 12 tools

# Start Slack bot (optional)
source .venv/bin/activate
python frontend/slack_bot.py

# Begin P3: Create supervisor.py, research_agent.py, report_agent.py
```

---

## 8. Summary

| Metric | Value |
|--------|-------|
| Projects completed | 3/7 (P1, P2, P5) |
| Projects designed | 1/7 (P3 — ready to build) |
| Projects remaining | 3/7 (P4, P6, P7) |
| Overall roadmap coverage | ~55% |
| After P3 completion | ~70% |
| Tools built | 12 |
| Tests passing | 17 Docker + 15 E2E + 6 guardrail + 5 Slack bot = **43 total** |
| Tutorials written | 9 (step-19 through step-25) |
| Issues documented | 12 (TROUBLESHOOTING.md) |
| Commits | 24 (project-125) |
| Docker services | 6 (all containerised) |

---

*Created 2026-03-27 — Starting point for P3 Multi-Agent Supervisor implementation.*
