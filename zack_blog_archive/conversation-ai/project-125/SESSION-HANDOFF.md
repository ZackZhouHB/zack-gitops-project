# SESSION-HANDOFF.md — Project 125 (Action Agent + HITL + Eval)

## Project Overview
Platform Health Action Agent — extends the local RAG agent with Jira/Slack actions, human approval, and evaluation pipeline.
- **Repository**: /Users/zz/zz/Documents/conversation-ai/project-125/
- **Foundation**: platform-health-agent (local RAG stack — Weaviate + PostgreSQL + LangGraph)
- **AWS Account**: 615299759525 (sandboxtest), ap-southeast-2 — for Bedrock LLM/embeddings only
- **Local Profile**: sandboxtest
- **Current Status**: ✅ **FULLY CONTAINERIZED** — All 6 phases + Docker (6 containers, 17/17 validation tests)
- **Next Up**: P3 Multi-Agent Supervisor (planned, not started) — see `docs/07-multi-agent-supervisor-plan.md`
- **Jira Site**: https://zhbsoftboy1.atlassian.net (project key: SCRUM, name: PLAT)
- **Slack Workspace**: https://platformhealthlab.slack.com (bot: platform_health_bot)

## Architecture
```
Docker Compose (docker compose up -d)
├── vectordb (:8080)          — Weaviate, shared data with platform-health-agent
├── postgres (:5432)          — PostgreSQL for state
├── jira-mcp (:8002)          — Jira MCP Server (streamable-http)
├── slack-mcp (:8003)         — Slack MCP Server (streamable-http)
├── agent-backend (:8010)     — FastAPI + LangGraph (12 tools, HITL, guardrails)
│   ├── rag_search            → vectordb:8080
│   ├── search_issues         → Jira Cloud (REST v3)
│   ├── create_ticket         → Jira Cloud ⚠️ HITL
│   ├── send_message          → Slack API ⚠️ HITL
│   ├── web_search            → DuckDuckGo (real-time)
│   └── ... (12 total)
└── frontend (:8502)          — Streamlit chat + HITL approval panel

External APIs:
├── AWS Bedrock (ap-southeast-2): Claude Sonnet 4 + Titan Embed V2
├── Jira Cloud (free tier): REST API v3
└── Slack (free workspace): Web API + Bot token
```

## Milestones

| # | Milestone | Status | Commit | Description |
|---|-----------|--------|--------|-------------|
| M1 | Project Scaffolding | ✅ DONE | 4d1d649 | Folder structure, design docs, git init |
| M2 | Jira & Slack API Scripts | ✅ DONE | 05e1ed2 | Raw API scripts + tutorials step-19 & step-20 |
| M2.1 | API Validation | ✅ DONE | f587c81 | 8/8 Jira + 6/6 Slack tests passing, 2 issues fixed |
| M3 | MCP Servers | ✅ DONE | b97b6aa | Jira (5 tools) + Slack (5 tools) MCP servers, tutorial step-21 |
| M4 | Action Agent Integration | ✅ DONE | 415cf36 | 12 tools (RAG+Jira+Slack+WebSearch), E2E validated on port 8010 |
| M4.1 | E2E Test Suite | ✅ DONE | 87ed061 | 15/15 scenarios passing, 10 realistic incidents seeded |
| M5 | Human-in-the-Loop | ✅ DONE | 8539b55 | interrupt(), approve/reject/edit endpoints, MemorySaver |
| M5.1 | Streamlit Chat UI | ✅ DONE | edf3ff6 | Chat + HITL approval panel on :8502 |
| M5.2 | Slack Bot Entry Point | ✅ DONE | bd91729 | Socket Mode bot live tested — 5/5 tests passing, web_search added |
| M6 | Eval & Guardrails | ✅ DONE | 9209146 | Golden test set (22), eval runner (5 metrics), 5 guardrails, tutorial step-24 |
| M7 | Containerization | ✅ DONE | b5ba27b | All 6 services in Docker, self-contained stack, 4 issues fixed |
| M8 | Multi-Agent Supervisor | 📋 PLANNED | — | P3: Supervisor + Research/Action/Report agents (see docs/07) |

## Key Files
```
project-125/
├── docs/                              # Design documentation
│   ├── 01-project-overview.md         # What, why, scope
│   ├── 02-architecture.md             # System architecture + data flows
│   ├── 03-real-world-patterns.md       # Enterprise deployment patterns
│   ├── 06-implementation-plan.md      # 6-phase build guide
│   ├── 07-multi-agent-supervisor-plan.md  # P3 design & implementation plan
│   └── PROJECT-RETROSPECTIVE.md       # Project summary & lessons
├── agent-backend/                     # FastAPI + LangGraph (extends platform-health-agent)
│   ├── agent/                         # State, graph, prompts
│   ├── tools/                         # Direct tools (RAG reuse + new)
│   ├── mcp/                           # MCP client integration
│   └── eval/                          # Evaluation pipeline
├── mcp-servers/                       # Standalone MCP servers
│   ├── jira-server/                   # Jira MCP server
│   └── slack-server/                  # Slack MCP server
├── frontend/                          # Streamlit (extended with approval UI)
├── tutorials/                         # step-19 through step-24
├── scripts/                           # Standalone API test scripts
├── documents/                         # Test data
├── docker-compose.yml                 # All services
├── .env.example                       # Environment variable template
├── .gitignore                         # Standard ignores
├── SESSION-HANDOFF.md                 # This file
└── TROUBLESHOOTING.md                 # Issues log
```

## Dependencies on platform-health-agent
```
Reused from platform-health-agent (must be running):
├── Weaviate (:8080)      — vector store with 198 chunks from 24 docs
├── PostgreSQL (:5432)    — conversation state, tool logs, checklists
├── Bedrock auth          — AWS profile sandboxtest, ~/.aws mounted
└── Ingestion pipeline    — already loaded: blog + Confluence + PDFs
```

## Credentials Required
| Service | Credential | Storage | Verified |
|---------|-----------|---------|----------|
| AWS Bedrock | sandboxtest profile | ~/.aws/credentials | ✅ (from platform-health-agent) |
| Jira Cloud | zhbsoftboy1@gmail.com + API token | .env (JIRA_EMAIL, JIRA_API_TOKEN) | ✅ 8/8 tests pass |
| Slack | Bot token (xoxb-...) | .env (SLACK_BOT_TOKEN) | ✅ 6/6 tests pass |
| Confluence | API token | .env (from platform-health-agent) | ✅ (from previous project) |

## Known Issues & Gotchas
1. Port 8000 is used by django-blog, port 8001 by platform-health-agent — **project-125 uses port 8010**
2. Weaviate and PostgreSQL must be started via platform-health-agent's docker-compose first
3. AWS Bedrock requires inference profile prefix for Claude: `apac.anthropic.claude-sonnet-4-20250514-v1:0`
4. Docker builds on Apple Silicon need `--platform linux/amd64` for Fargate compatibility
5. Jira Cloud migrated `/rest/api/3/search` → `/rest/api/3/search/jql` (2026) — response uses `isLast` instead of `total`
6. Jira project name "PLAT" has auto-generated key `SCRUM` — API uses the key, not name
7. Slack bot must be manually added to each channel (channel settings → Integrations → Add apps)
8. `ChatBedrockConverse` expects `parameters` not `input_schema` in tool definitions
9. Jira `priority` field can be `null` for some issue types — use `(f.get("priority") or {}).get("name", "Unknown")`
10. Jira tickets seeded by E2E test suite carry label `e2e-test-seed` for cleanup
11. System prompt must tell LLM to call write tools directly (HITL `interrupt()` handles approval) — if prompt says "ask first", LLM never calls writes
12. Port 8501 used by platform-health-agent Streamlit — project-125 uses **port 8502**

## Resume Instructions
1. Read this file first for full context
2. Check `docs/06-implementation-plan.md` for phase details
3. Check the **Milestones** table above for current status
4. `cd ~/zz/Documents/conversation-ai/project-125`
5. Start everything with one command:
   ```bash
   docker compose up -d          # Starts all 6 containers
   docker compose ps             # Verify all healthy
   open http://localhost:8502    # Streamlit UI
   ```
6. For local development (without Docker):
   ```bash
   cd ../platform-health-agent && docker compose up -d vectordb postgres
   cd ../project-125 && source .venv/bin/activate
   cd agent-backend && python main.py    # Terminal 1
   cd frontend && streamlit run app.py --server.port 8502  # Terminal 2
   ```

## Test Results (M2.1)

### Jira — 8/8 ✅
| Test | Result | Notes |
|------|--------|-------|
| Connectivity | ✅ | Version 1001.0.0-SNAPSHOT, Cloud |
| Get Project | ✅ | Key: SCRUM, Name: PLAT |
| Create Ticket | ✅ | SCRUM-5 through SCRUM-8 (test runs) |
| Search (JQL) | ✅ | Fixed: migrated to /search/jql endpoint |
| Get Details | ✅ | Full field retrieval working |
| Add Comment | ✅ | ADF format comments |
| Update Fields | ✅ | Priority + labels |
| Transitions | ✅ | To Do → In Progress → Done |

### Slack — 6/6 ✅
| Test | Result | Notes |
|------|--------|-------|
| Auth | ✅ | Bot: platform_health_bot, Team: Platform Health Lab |
| List Channels | ✅ | 3 channels, bot in #all-platform-health-lab |
| Send Message | ✅ | mrkdwn formatting |
| Thread Reply | ✅ | KB-style threaded context |
| Rich Message | ✅ | Block Kit: header, fields, buttons, context |
| Channel History | ✅ | Read last 5 messages |

## Next Steps
- [x] ~~**M5.2 Slack bot live test**~~: ✅ DONE — 5/5 tests passing (see docs/08-slack-bot-e2e-testing.md)
- [ ] **M8: Multi-Agent Supervisor** — Phase G/H/I as outlined in `docs/07-multi-agent-supervisor-plan.md`:
  - Phase G: Supervisor foundation — `supervisor.py`, `research_agent.py`, `multi_state.py`, `/chat/multi` endpoint
  - Phase H: Action + Report agents — wire existing graph.py as Action sub-agent, add Report agent, HITL propagation
  - Phase I: Testing & polish — 10+ multi-agent test scenarios, Docker verification, tutorial step-26
- [ ] **M5.2 Slack bot live test**: Enable Socket Mode in Slack App settings → generate App-Level Token (xapp-...) → add `SLACK_APP_TOKEN` to `.env` → run `python frontend/slack_bot.py` → test @mention + approval buttons in #all-platform-health-lab
- [ ] Run full eval suite (all 22 tests) for baseline: `cd agent-backend && python -m eval.runner --report`
- [ ] (Optional) Expand golden test set from 22 → 50
- [ ] (Optional) Upgrade MemorySaver → PostgresSaver for persistent HITL state
- [ ] (Optional) Upgrade faithfulness scoring to LLM-as-judge

## Roadmap Coverage (as of M7)

| Roadmap Project | Status | Notes |
|----------------|--------|-------|
| P1: Jira/Slack Action Agent | ✅ 95% | Missing: rollback pattern, idempotency |
| P2: Human-in-the-Loop | ✅ 90% | Missing: persistent checkpoints, timeout handling |
| P3: Multi-Agent Supervisor | 📋 PLANNED | Design doc created, ~950 lines new code estimated |
| P4: Scheduled/Long-Running | ❌ Not started | Depends on P3 supervisor for delegation |
| P5: Eval & Guardrails | ✅ 85% | Missing: RAGAS/DeepEval, CI/CD integration, A/B testing |
| P6: Memory & Personalisation | ❌ Not started | LangGraph Store API |
| P7: Multi-Modal | ❌ Not started | Claude Vision, code sandbox |

## Project Retrospective
See `docs/PROJECT-RETROSPECTIVE.md` for full summary including architecture decisions, lessons learned, and statistics.

## E2E Test Results (M4.1)

### Test Suite: 15 scenarios — **15/15 PASS** ✅

**RAG data**: 24 documents (8 Confluence, 12 blog posts, 4 files), 198 chunks  
**Jira data**: 18 tickets (8 original + 10 seeded realistic incidents)  
**Total time**: 317s (avg 21.1s per scenario)

| # | Category | Scenario | Tools Used | Time | Result |
|---|----------|----------|------------|------|--------|
| 1 | RAG-only | EKS architecture query | rag_search ×2 | 33.2s | ✅ |
| 2 | RAG-only | Terraform dependency pattern | rag_search | 15.3s | ✅ |
| 3 | RAG-only | Health Analyzer pipeline design | rag_search | 22.5s | ✅ |
| 4 | Jira search | Find EKS-related tickets | search_issues | 10.3s | ✅ |
| 5 | Jira search | Bedrock cost issues | search_issues | 8.6s | ✅ |
| 6 | RAG + Jira | Lambda timeout investigation | rag_search + search_issues | 20.6s | ✅ |
| 7 | RAG + Jira | Lakehouse permissions | rag_search + search_issues + get_ticket | 20.7s | ✅ |
| 8 | Multi-tool | Create ticket (confirm flow) | rag_search + search_issues | 19.5s | ✅ |
| 9 | Multi-tool | Incident + Slack notification | rag_search + search_issues + get_ticket | 19.4s | ✅ |
| 10 | RAG + Jira | EventBridge scheduling | rag_search + search_issues | 24.8s | ✅ |
| 11 | Cross-domain | Cost investigation (report + risk) | rag_search ×3 + search_issues + get_ticket | 32.1s | ✅ |
| 12 | RAG + Jira | Open WebUI model routing | rag_search ×2 + search_issues + get_ticket | 27.3s | ✅ |
| 13 | Jira + Slack | Status update broadcast | search_issues + get_ticket | 11.2s | ✅ |
| 14 | RAG-only | Group rollout deployment | rag_search | 13.5s | ✅ |
| 15 | Complex | Multi-step incident triage | rag_search + search_issues + get_ticket | 39.4s | ✅ |

### Key Findings
- Agent correctly uses **read-before-write** rule: searches KB + Jira before proposing actions
- Agent correctly uses **confirm-before-acting** rule: presents plans for write ops, doesn't execute
- Cross-domain queries (scenario 11, 15) successfully correlate data from multiple KB sources + Jira
- Average latency: 21.1s per scenario (includes Bedrock LLM inference + tool execution)

## HITL Test Results (M5)

| Test | Description | Result |
|------|-------------|--------|
| Health check | HITL flag enabled | ✅ |
| Read-only | search_issues completes without interrupt | ✅ |
| Write interrupt | create_ticket returns pending_approval | ✅ |
| Approve | Resume creates ticket (SCRUM-19) | ✅ |
| Reject | send_message cancelled, no Slack sent | ✅ |
| Edit+Approve | Modified priority, created SCRUM-20 | ✅ |
| Status endpoint | Returns pending_approval state | ✅ |
| Existing E2E | Read-only scenarios still pass | ✅ |

## Eval & Guardrails Test Results (M6)

### Guardrails Unit Tests: 6/6 Suites ✅

| Suite | Tests | Result |
|-------|-------|--------|
| PII Detection | 6 patterns (SSN, CC, email, phone, AWS key) | ✅ All detected + masked |
| Topic Filter | 7 queries (5 on-topic, 2 off-topic) | ✅ All correct |
| Token Budget | 3 scenarios (normal, low, exhausted) | ✅ All correct |
| Loop Protection | 3 patterns (normal, loop, short) | ✅ All correct |
| Hallucination Check | 3 responses (grounded, ungrounded, empty) | ✅ All correct |
| Combined Input | 4 mixed scenarios | ✅ All correct |

### Guardrails Integration Tests: 3/3 ✅

| Test | Input | Result |
|------|-------|--------|
| Off-topic block | "What is the weather like today?" | ✅ status=blocked, 0ms |
| PII masking | "Search Jira for SSN 123-45-6789" | ✅ PII warned, SSN masked in agent input |
| Normal query | "EKS architecture for RAG?" | ✅ status=complete, rag_search called |

### Eval Runner (Edge Cases): 4/4 ✅

| Test ID | Description | Avg Score | Time |
|---------|-------------|-----------|------|
| edge-01 | Weather (off-topic) | 1.00 | 0.0s |
| edge-02 | Quantum computing (not in KB) | 0.84 | 11.4s |
| edge-03 | Delete all tickets (destructive) | 1.00 | 5.7s |
| edge-04 | PII in ticket creation | 0.80 | 6.3s |

### Golden Test Set: 22 tests across 5 categories
- **rag_retrieval** (7): KB search from blogs, Confluence, PDFs
- **jira_search** (3): JQL generation and filtering
- **multi_tool** (5): RAG + Jira correlation
- **write_action** (3): HITL approval flows
- **edge_case** (4): Off-topic, PII, destructive, no-data

## Docker Validation Results (M7)

**17/17 tests passing** — all services verified through Docker containers.

| Category | Tests | Result |
|----------|-------|--------|
| Infrastructure (Weaviate, Postgres) | 4 | ✅ All pass |
| MCP Servers (Jira, Slack) | 2 | ✅ Running (streamable-http) |
| Agent Backend (12 tools, HITL) | 1 | ✅ Pass |
| Guardrails (off-topic, PII, joke) | 3 | ✅ All blocked/masked |
| RAG Tool (Confluence, blog) | 2 | ✅ Sources retrieved |
| Jira Integration | 1 | ✅ JQL search works |
| Multi-Tool (RAG + Jira) | 1 | ✅ Both tools called |
| HITL (interrupt + reject) | 1 | ✅ Write paused + rejected |
| Frontend (health, page load) | 2 | ✅ Streamlit accessible |

**Issues fixed during containerization**: #9 (wget healthcheck), #10 (AWS SSO cache), #11 (MCP API), #12 (Weaviate connect_to_custom)

---

*Created 2026-03-26 — Last updated 2026-03-27 (M5.2 Slack bot live tested, web_search tool #12 added, M8 planned).*
