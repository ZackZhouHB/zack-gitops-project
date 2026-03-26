# Session Handoff — Platform Health Insight Assistant

> **Last Updated:** 2026-03-26T13:10:00Z  
> **Project Root:** ~/zz/Documents/conversation-ai/platform-health-agent/  
> **Git Branch:** main  
> **Last Commit:** Streaming responses, source citations, and timing display  

---

## 1. Who Is the User

- **Name:** Hongbo Zhou (Hongbo.Zhou@nesa.nsw.edu.au)
- **Org:** NESA — NSW Education Standards Authority (public sector, education)
- **Role:** Technology / AI engineer
- **Background:** Strong in Docker, K8s, EKS, AWS Bedrock, RAG (Weaviate), vLLM. See `~/zz/Documents/AIML-WORKLOAD/progress-analysis-2026-02-03.md` for full skills inventory.
- **Learning goal:** Transition from RAG pipeline engineer → agentic workflow engineer
- **Communication preference:** Wants step-by-step explanations of design and code, not just working code

---

## 2. What We're Building

An **AI agent** that handles multi-step workflows (not just Q&A) using LangGraph, tool calling, and state management. Built locally in Docker, calling AWS Bedrock for LLM/embeddings.

**Domain: Platform Health Insight Assistant** — infrastructure troubleshooting, architecture Q&A, incident triage, onboarding guides. Data sources are all technical (blog posts, Confluence design docs, Terraform/Azure/Lakehouse PDFs).

**Origin story:**
1. Reviewed a conversational AI JD (4WD Supacentre) → decided to pass (mature field, 5-day office)
2. Identified **agentic workflows** as the higher-value career direction
3. Discovered NESA has an existing teacher accreditation chatbot PoC in AWS (lab account)
4. PoC is Q&A only (RAG pipeline, no workflows, no tools, no state)
5. Decision: Build a local agentic version that can later replace/enhance the PoC

**Key insight driving the project:**
> "Building a RAG app proves you can handle Data. Building an Agent proves you can handle Workflow."

---

## 3. Existing PoC (AWS Lab Account — Reference Only)

- **AWS Profile:** `lab` (account 315720945463)
- **Bedrock Agent:** `ta-agent-quick-start-0mns4` (CFE1VRZGDL) — Claude 3.5 Sonnet
- **Knowledge Base:** `teacher-accreditation-kb-01` (0MHCHNAZTB) — OpenSearch Serverless
- **5 data sources:** 3 web crawlers (2 FAILED, 1 partial), 1 Confluence (STOPPED), 1 S3 (OK)
- **Frontend:** Streamlit on ECS Fargate (port 8501) + Cognito auth + ALB
- **Status:** PoC only — no tool calling, no workflows, no state management
- **We are NOT modifying this.** It's reference architecture only.

Full details: `docs/02-existing-poc-architecture.md`, `docs/03-replication-blueprint.md`

---

## 4. Our Local Solution

### AWS Profile & Models

```
AWS Profile:    sandboxtest (account 615299759525)
Region:         ap-southeast-2
LLM:            apac.anthropic.claude-sonnet-4-20250514-v1:0  (inference profile required)
Embeddings:     amazon.titan-embed-text-v2:0  (1024 dimensions, direct model ID)
```

### Data Sources

| Source | Details | Status |
|---|---|---|
| **Blog** | `https://zackblog.work/` (public, no auth) | ✅ Verified (HTTP 200) |
| **Confluence** | 8 pages under parent `4346576951` in space `ET` at `educationstandards.atlassian.net` | ✅ Verified (API token works) |
| **PDFs** | `./documents/` — 4 files (Terraform PDF, Azure AD MD, Lakehouse MDs) | ✅ Files present |

### Confluence Pages

| # | Page ID | Title |
|---|---|---|
| 01 | 4290117633 | Platform Health Insight - AWS - POC Proposal |
| 02 | 4346773530 | AWS Data Sources: What We Collect and Why |
| 03 | 4376821776 | AWS Bedrock Integration in Health Analyzer |
| 04 | 4383342593 | Prompt and Staged Pipeline Design |
| 05 | 4383571971 | EventBridge and SNS Design |
| 06 | 4404707345 | Sample Insight Report |
| 07 | 4410048520 | Group Rollout Deployment Plan |
| 08 | 4464967708 | Risk and Limitation |

### Architecture

```
LOCAL (Docker Compose)                    AWS (API calls only)
──────────────────────                    ────────────────────
Streamlit (:8501)          ──→           Bedrock Claude Sonnet 4
FastAPI + LangGraph (:8001)──→           Bedrock Titan Embed V2
Weaviate (:8080)
PostgreSQL (:5432)
```

**Note:** Port 8000 is in use by `django-blog`. Agent backend uses **8001**.

### Credentials

- All in `.env` (gitignored, never committed)
- `.env.example` has placeholders (committed)
- Confluence API token stored locally only
- AWS auth via `~/.aws` credentials (sandboxtest profile, mounted read-only in Docker)

---

## 5. Project Structure

```
platform-health-agent/
├── docs/                              # Design documentation
│   ├── 01-context-and-direction.md    # Why conversational AI → agentic
│   ├── 02-existing-poc-architecture.md # AWS lab PoC inventory
│   ├── 03-replication-blueprint.md    # Full AWS component spec
│   ├── 04-local-architecture.md       # Local design + workflows + production patterns
│   ├── 05-goal-clarification.md       # What/why/how summary
│   └── 06-implementation-plan.md      # 7-step build guide
├── frontend/                          # Streamlit chat UI (streaming support)
│   ├── Dockerfile, requirements.txt, app.py
├── agent-backend/                     # LangGraph + FastAPI
│   ├── Dockerfile, requirements.txt, config.py, main.py
│   ├── agent/                         # State, graph, prompts
│   │   ├── state.py                   # AgentState TypedDict
│   │   ├── graph.py                   # LangGraph ReAct + router + workflows
│   │   ├── prompts.py                 # System + router prompts
│   │   └── workflows/incident_triage.py # Incident triage workflow (3-branch)
│   ├── tools/                         # RAG, incident, DB, escalation
│   │   ├── rag_tool.py                # Weaviate semantic search
│   │   ├── incident_tool.py           # Incident triage business rules
│   │   ├── db_tool.py                 # PostgreSQL checklists
│   │   └── escalation_tool.py         # Human handoff
│   └── ingestion/                     # Document ingestion (4 modules, tested, 198 chunks)
├── tutorials/                         # Step-by-step learning guides
│   ├── step-01-infrastructure.md      # Docker Compose, Weaviate, PostgreSQL
│   ├── step-02-data-ingestion.md      # Loaders, chunking, embeddings, vector store
│   ├── step-03-rag-tool.md            # RAG search implementation
│   ├── step-04-basic-agent.md         # LangGraph ReAct pattern
│   ├── step-05-multi-tool.md          # Multi-tool agent
│   ├── step-06-workflow.md            # Incident triage workflow
│   ├── step-07-production.md          # Production patterns
│   └── troubleshooting-guide.md       # Common issues and fixes
├── documents/                         # User's PDFs/docs for ingestion
├── docker-compose.yml                 # 4 services with health checks
├── .env                               # Real credentials (gitignored)
├── .env.example                       # Placeholder template
└── .gitignore
```

---

## 6. Implementation Progress

### 7-Step Build Plan

| Step | What | Status |
|---|---|---|
| **1. Infrastructure** | Docker Compose — Weaviate + PostgreSQL running | ✅ DONE |
| **2. Data Ingestion** | Load blog + Confluence + PDFs into Weaviate | ✅ DONE |
| **3. RAG Tool** | Implement rag_search with Weaviate + Bedrock Titan | ✅ DONE |
| **4. Basic Agent** | LangGraph + Claude + RAG answers questions | ✅ DONE |
| **5. Multi-Tool** | Agent picks which tool (RAG, policy, checklist, escalation) | ✅ DONE |
| **6. Workflow 1** | Full eligibility check (branching, multi-turn, state) | ✅ DONE |
| **7. Production Patterns** | Streaming, logging, circuit breaker, checkpoints | ✅ DONE |

### Milestone: Streaming UX (Completed 2026-03-26)

| Feature | Status |
|---|---|
| SSE streaming via `astream_events` | ✅ DONE |
| Router token filtering (only stream answer nodes) | ✅ DONE |
| Content block handling (Bedrock Converse list format) | ✅ DONE |
| Source citation extraction from tool_calls_log | ✅ DONE |
| Server-side latency in complete event | ✅ DONE |
| Frontend live token streaming with cursor | ✅ DONE |
| Expandable source citations with confidence % | ✅ DONE |
| Fallback to non-streaming /chat endpoint | ✅ DONE |

### Workflows

| # | Workflow | Agent Skill | Status |
|---|---|---|---|
| WF1 | General QA (ReAct) | Tool calling + RAG search | ✅ DONE |
| WF2 | Incident Triage | Branching (known_fix/investigate/escalate) | ✅ DONE |
| WF3 | Change Impact Analysis | Future | ⏳ Future |
| WF4 | Onboarding Guide | Future | ⏳ Future |

---

## 7. Key Decisions Made

| Decision | Choice | Reason |
|---|---|---|
| Run locally vs AWS | Local (Docker Compose) | 90% time on agent logic, $5-15/mo vs $500/mo |
| Vector store | Weaviate (Docker) | User knows it, free, replaces $350/mo OpenSearch |
| LLM | Bedrock Claude Sonnet 4 (API) | User's org uses AWS, inference profile prefix needed |
| Embeddings | Bedrock Titan Embed V2 (1024d) | Same as original PoC, works with direct model ID |
| Agent framework | LangGraph | Full control, checkpointing, loops, production-grade |
| Frontend | Streamlit | Same as original PoC, simple Python |
| Backend API | FastAPI | Streaming support, async, lightweight |
| Auth | None (localhost only) | Dev environment, not needed |
| Data | User's own blog + Confluence + docs (not company data) | Personal lab, no compliance risk |
| Streaming | SSE via astream_events v2 | Native LangGraph streaming, node-level filtering, no WebSocket needed |

---

## 8. Resume Instructions

To continue this project in a new session:

1. Read this file first for full context
2. Check `docs/06-implementation-plan.md` for the build steps
3. Check the **Implementation Progress** table above for current step
4. `cd ~/zz/Documents/conversation-ai/platform-health-agent`
5. `git log --oneline -5` to see recent commits
6. The user wants **explanations with every step** — don't just write code, explain why
7. To start services: `docker compose up -d` then `source .venv/bin/activate && cd agent-backend && AWS_PROFILE=sandboxtest uvicorn main:app --port 8001` then `streamlit run frontend/app.py --server.port 8501`
8. Backend: http://localhost:8001, Frontend: http://localhost:8501
9. Port 8000 is used by django-blog, so agent backend uses 8001

---

## 9. Files Outside This Project (Reference)

| File | Location | What |
|---|---|---|
| JD analysis | `~/zz/Documents/conversation-ai/jd.txt` | 4WD Supacentre JD (passed) |
| Prep plan | `~/zz/Documents/conversation-ai/conversational-ai-engineer-prep.md` | Conversational AI learning path (superseded) |
| Skills inventory | `~/zz/Documents/AIML-WORKLOAD/progress-analysis-2026-02-03.md` | User's full AI/ML skills + gaps |

---

## 10. Milestones

| # | Milestone | Date | Commit | Description |
|---|---|---|---|---|
| M1 | Infrastructure + Ingestion | 2026-03-25 | 7e6f2cf..b15c878 | Docker Compose, 198 chunks from 24 docs |
| M2 | Working Agent | 2026-03-25 | 35ce7e1..f46b541 | LangGraph ReAct + 4 tools + incident triage |
| M3 | Production Patterns | 2026-03-25 | 366f46b | Logging, timing, error handling |
| M4 | Domain Reskin | 2026-03-26 | (reskin commit) | Teacher Accreditation → Platform Health |
| M5 | Streaming UX | 2026-03-26 | c240612 | SSE streaming, source citations, timing |
