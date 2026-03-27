# Project 125 — Retrospective & Summary

> **AI Agent Actions + Human-in-the-Loop + Eval & Guardrails**  
> Built: March 26–27, 2026  
> Author: Hongbo Zhou (NESA Platform Engineer)

---

## What We Built

A production-grade AI agent that can **investigate platform incidents** using RAG knowledge base search, **take action** via Jira and Slack, require **human approval** before write operations, and validate its own quality through **evaluation pipelines and runtime guardrails**.

### The Stack

```
Entry Points:  Streamlit Chat (:8502) │ Slack Bot (Socket Mode) │ API (:8010)
                         │                      │                    │
                         ▼                      ▼                    ▼
Guardrails:    ┌─ PII Detection ─ Topic Filter ─ Token Budget ─────────────┐
               │                                                            │
Agent:         │  LangGraph ReAct Agent (Claude Sonnet 4 via Bedrock)      │
               │  ├── rag_search         → Weaviate (198 chunks, 24 docs)  │
               │  ├── search_issues      → Jira Cloud (JQL)               │
               │  ├── get_ticket         → Jira Cloud                     │
               │  ├── create_ticket      → Jira Cloud  ⚠️ HITL            │
               │  ├── update_ticket      → Jira Cloud  ⚠️ HITL            │
               │  ├── add_comment        → Jira Cloud  ⚠️ HITL            │
               │  ├── send_message       → Slack       ⚠️ HITL            │
               │  ├── create_thread      → Slack       ⚠️ HITL            │
               │  ├── reply_in_thread    → Slack       ⚠️ HITL            │
               │  ├── list_channels      → Slack                          │
               │  └── send_rich_notification → Slack   ⚠️ HITL            │
               │                                                            │
HITL:          │  interrupt() → Approve / Reject / Edit → Command(resume)  │
               │                                                            │
Guardrails:    └─ Hallucination Check ─ Loop Protection ───────────────────┘
```

---

## By The Numbers

| Metric | Count |
|--------|-------|
| Git commits | 15 |
| Total files | 63 |
| Python code | ~5,500 lines |
| Documentation | ~4,500 lines (Markdown) |
| Tutorials written | 8 (step-19 through step-24) |
| Design docs | 4 |
| Tools integrated | 11 (4 read + 7 write) |
| Test scenarios | 41 across 5 test suites |
| E2E scenarios | 15/15 passing |
| Guardrail checks | 5 (PII, topic, token, loop, hallucination) |
| Golden eval tests | 22 across 5 categories |
| Issues documented | 8 in TROUBLESHOOTING.md |
| Jira tickets created | 20+ (SCRUM-1 through SCRUM-20) |
| Phases completed | 6/6 (A through F) |

---

## Phases & Milestones

| Phase | Milestone | What Was Delivered |
|-------|-----------|-------------------|
| **A** | M1 | Scaffold: folder structure, design docs, git init |
| **B** | M2, M2.1 | Jira (8/8 tests) + Slack (6/6 tests) raw API scripts |
| **C** | M3 | Jira MCP server (5 tools) + Slack MCP server (5 tools) |
| **D** | M4, M4.1 | LangGraph agent (11 tools), 15/15 E2E test suite |
| **E** | M5, M5.1, M5.2 | HITL interrupt/resume, Streamlit UI, Slack bot (code) |
| **F** | M6 | Golden test set, eval runner, 5 guardrails |

---

## Roadmap Coverage

This project covered **3 of 7** items from the FUTURE-ROADMAP.md:

| Roadmap Item | Status | Coverage |
|-------------|--------|----------|
| **P1: Action Agent (Jira/Slack)** | ✅ Complete | Full: 11 tools, MCP servers, E2E tested |
| **P2: Human-in-the-Loop** | ✅ Complete | Full: interrupt(), approve/reject/edit, Streamlit UI |
| P3: Multi-Agent Supervisor | ⬜ Not started | Future project |
| P4: Scheduled/Long-Running Agents | ⬜ Not started | Future project |
| **P5: Eval & Guardrails** | ✅ Complete | Full: 22 golden tests, 5 metrics, 5 runtime guardrails |
| P6: Memory & Personalisation | ⬜ Not started | Future project |
| P7: Multi-Modal (Vision, Code) | ⬜ Not started | Future project |

---

## Key Technical Decisions

### 1. Direct Import vs MCP Protocol
**Decision**: Import Jira/Slack clients directly via `sys.path` instead of running MCP servers as separate processes.  
**Why**: Simpler for a learning project. MCP servers exist as standalone code and could be served via MCP protocol in production, but direct import avoids inter-process communication complexity.

### 2. MemorySaver vs PostgresSaver
**Decision**: Use in-memory checkpointing for HITL state.  
**Why**: Sufficient for learning/testing. State is lost on restart. Production would use `PostgresSaver` with the existing PostgreSQL instance.

### 3. Heuristic Guardrails vs LLM-as-Judge
**Decision**: Regex-based PII detection, keyword-based topic filter, word-overlap faithfulness.  
**Why**: Zero additional API calls, instant execution, predictable behavior. Production would add LLM-as-judge for semantic understanding.

### 4. Port 8010 (Not 8001)
**Decision**: Agent runs on 8010 to avoid conflict with platform-health-agent.  
**Why**: Both projects share Weaviate (:8080) and Postgres (:5432). Separate agent ports allow both to run simultaneously.

### 5. Guardrails in API Layer (Not Agent Graph)
**Decision**: Input/output guardrails run in FastAPI middleware, not inside the LangGraph graph.  
**Why**: Separation of concerns. Guardrails are orthogonal to agent logic. Bad input is blocked before the agent spends Bedrock API credits.

---

## What We Learned

### About AI Agents
- **Agent = Brain + Tools**: The LLM decides which tools to call, in what order, with what arguments. The ReAct loop (Reason → Act → Observe) is the core pattern.
- **MCP standardizes tool interfaces**: Model Context Protocol turns any API into a tool the agent can use. Build once, plug into any agent.
- **HITL is essential for write actions**: Without `interrupt()`, the agent would create tickets and send messages autonomously. The pause-approve-resume pattern gives humans control.
- **RAG is just one tool**: In the platform-health-agent, RAG was the whole system. Here, it's one of 11 tools the agent can choose from.

### About Testing & Evaluation
- **15 E2E scenarios caught real bugs**: Port config, null priority fields, prompt conflicts — all discovered through systematic testing.
- **Guardrails prevent misuse at the boundary**: PII masking, topic filtering, and token budgets protect the system before the expensive LLM call.
- **Faithfulness scoring is hard**: Word overlap doesn't capture semantic equivalence. LLM-as-judge is the production answer.

### About Real-World Patterns
- **Four entry points**: Slack bot (most common), event-driven webhooks (most scalable), portal widget (most controllable), CLI (for ops teams).
- **Companies don't start with all of this**: They start with Slack bot + one tool, then add HITL, then guardrails, then eval.

---

## Troubleshooting Highlights

8 issues documented in TROUBLESHOOTING.md:

| # | Issue | Impact | Resolution |
|---|-------|--------|------------|
| 1 | Jira `/search` → `/search/jql` migration | All Jira searches returned 410 | Updated endpoint + response parsing |
| 2 | Project key SCRUM vs name PLAT | Ticket creation failed | Use API key, not display name |
| 3 | `parameters` vs `input_schema` in tool defs | Agent couldn't call any tools | Matched ChatBedrockConverse expected format |
| 4 | Jira priority field null | NoneType crash on ticket display | Defensive `(value or {}).get()` pattern |
| 5 | Port 8001 hardcoded | Conflict with platform-health-agent | Changed to 8010 |
| 6 | "Confirm before acting" prompt | HITL `interrupt()` never triggered | Changed to "proceed with confidence" |
| 7 | Faithfulness heuristic inconsistency | Correct responses scored low | Known — upgrade to LLM-as-judge |
| 8 | Topic filter keyword gaps | "Quantum computing" not blocked | Known — upgrade to LLM classifier |

---

## Open Items

| Item | Status | Action Required |
|------|--------|-----------------|
| Slack bot live test | 🔧 Code done | Enable Socket Mode in Slack App settings, generate App-Level Token (xapp-...), add `SLACK_APP_TOKEN` to `.env`, run `python frontend/slack_bot.py` |
| Full eval suite run | 📋 Ready | Start agent, run `python -m eval.runner --report` for all 22 tests |
| MemorySaver → PostgresSaver | 📋 Enhancement | Swap checkpointer for persistent HITL state |
| Golden test set expansion | 📋 Enhancement | Add 28 more tests to reach 50 (if needed) |

---

## Project Structure

```
project-125/
├── agent-backend/          # FastAPI + LangGraph agent (:8010)
│   ├── agent/              # Graph, prompts, state
│   ├── eval/               # Golden tests, runner, guardrails
│   ├── tools/              # RAG tool (Weaviate direct)
│   ├── main.py             # FastAPI with HITL + guardrails
│   └── config.py           # All config
├── mcp-servers/            # Standalone MCP tool servers
│   ├── jira-server/        # 5 Jira tools
│   └── slack-server/       # 5 Slack tools
├── frontend/
│   ├── app.py              # Streamlit chat + HITL UI (:8502)
│   └── slack_bot.py        # Slack Socket Mode bot
├── scripts/                # Test scripts (5 suites, 41 tests)
├── tutorials/              # 8 step-by-step guides
├── docs/                   # 4 design documents
├── SESSION-HANDOFF.md      # Living handoff document
└── TROUBLESHOOTING.md      # 8 issues documented
```

---

## What's Next (Remaining Roadmap)

If continuing from this project, the recommended order is:

1. **P3: Multi-Agent Supervisor** — Multiple specialized agents coordinated by a supervisor
2. **P4: Scheduled/Long-Running Agents** — Cron-triggered workflows, background monitoring
3. **P6: Memory & Personalisation** — Cross-session memory, user preference learning
4. **P7: Multi-Modal** — Image analysis, code execution sandboxes

Each would extend the same project-125 foundation (agent backend, Jira/Slack tools, HITL, guardrails).

---

*Project completed March 27, 2026. All 6 phases delivered across 15 commits.*
