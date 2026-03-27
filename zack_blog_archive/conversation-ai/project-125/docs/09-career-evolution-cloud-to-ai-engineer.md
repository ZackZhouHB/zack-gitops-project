# AI Engineer Career Evolution — From Cloud Platform to AI Agent Engineer

> **Author**: Hongbo (Zack) Zhou  
> **Date**: March 2026  
> **Context**: Reflections after completing 3 hands-on AI projects spanning RAG, cloud deployment, and agent orchestration

---

## 1. The Journey So Far

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  CLOUD/PLATFORM ENGINEER            AI ENGINEER                            │
│  (Starting Point)                    (Current + Growing)                    │
│                                                                             │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐             │
│  │ Phase 0  │───→│ Phase 1  │───→│ Phase 2  │───→│ Phase 3  │───→ ...     │
│  │          │    │          │    │          │    │          │             │
│  │ Cloud    │    │ RAG      │    │ Cloud AI │    │ AI Agent │             │
│  │ Platform │    │ Engineer │    │ Engineer │    │ Engineer │             │
│  │ Engineer │    │          │    │          │    │          │             │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘             │
│                                                                             │
│  EKS, Terraform   Chunking,        Bedrock,       LangGraph,              │
│  Docker, CI/CD    Embeddings,      ECS Fargate,   Tools, HITL,            │
│  Monitoring       Vector Search,   OpenSearch,    Guardrails,             │
│                   Retrieval,       Terraform,     Multi-Agent,            │
│                   Frontend UX      Cost Mgmt      Web Search              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Phase Breakdown

### Phase 0: Cloud Platform Engineer (Foundation)

**Background**: NESA platform engineering — AWS infrastructure, Kubernetes, CI/CD, monitoring.

| Skill | How It Applies to AI |
|-------|---------------------|
| EKS / Kubernetes | Deploying AI workloads at scale, GPU scheduling |
| Terraform IaC | Reproducible AI infrastructure, Bedrock provisioning |
| Docker / Compose | Containerising AI stacks (Weaviate + agents + frontends) |
| API design | Building agent APIs, MCP servers, webhook handlers |
| Monitoring / Alerting | AI observability, token tracking, latency monitoring |
| Cost management | Bedrock token budgets, model selection for cost efficiency |
| Networking / Security | VPC design for AI services, credential management |

**Key Insight**: Most AI engineers can't deploy. Most cloud engineers can't build AI. Having both is rare and valuable.

---

### Phase 1: RAG Engineer

**Project**: Platform Health Insight Assistant (local stack)

**What was built**:
- Weaviate vector database with 198 chunks from 24 documents
- Multi-source ingestion pipeline (Confluence, web crawler, PDF, file upload)
- Hybrid search with multiple retrieval strategies
- Streamlit frontend with:
  - Conversation memory and cache management
  - Source visibility with upload/delete controls
  - Dimension and chunk size configuration
  - Response time tracking and display

**Skills gained**:

| Skill | Depth | What Was Learned |
|-------|-------|-----------------|
| Chunking strategies | Deep | Fixed-size, semantic, recursive — trade-offs between recall and precision |
| Embedding models | Moderate | Titan Embed V2 (1024 dims), dimension impact on search quality |
| Vector search | Deep | HNSW algorithm, hybrid search, similarity thresholds |
| Retrieval methods | Moderate | Top-k, MMR, contextual compression |
| Prompt engineering | Moderate | System prompts, context injection, citation formatting |
| Frontend UX for AI | Deep | Streaming responses, source management, settings UI |
| LangChain/LangGraph | Foundational | ReAct loop, tool calling, state management |

**Career relevance**: RAG is the #1 most deployed AI pattern in enterprise. Every company with internal docs needs this. It's also the foundation for agent-based systems — RAG becomes a tool inside the agent.

---

### Phase 2: Cloud AI Engineer

**Project**: AWS-deployed RAG (ECS Fargate + Bedrock KB + OpenSearch)

**What was built**:
- Full serverless deployment: ECS Fargate, ALB, OpenSearch Serverless
- Bedrock Knowledge Base with S3 + Confluence + web crawler sources
- Terraform IaC for entire stack (create and destroy in minutes)
- Cost analysis: $0.80/day steady state, $15-20/month budget
- Production streaming via SSE

**Skills gained**:

| Skill | Depth | What Was Learned |
|-------|-------|-----------------|
| AWS Bedrock | Deep | Models, KB, embeddings, inference profiles, cross-region |
| ECS Fargate | Deep | Task definitions, ALB health checks, auto-scaling |
| OpenSearch Serverless | Moderate | Vector engine, collection types, index management |
| Terraform for AI | Deep | Bedrock resources, IAM for AI services, state management |
| Cost engineering | Deep | Token pricing, provisioned vs on-demand, destroy playbook |
| Production deployment | Deep | Health checks, environment configs, secrets management |
| Serverless architecture | Moderate | When to use Lambda vs ECS vs Bedrock native |

**Career relevance**: Companies need AI engineers who can take a local prototype and deploy it to production cloud. This phase proved that transition — same RAG logic, completely different infrastructure, with cost awareness.

---

### Phase 3: AI Agent Engineer (Current)

**Project**: Project-125 — Action Agent + HITL + Eval + Guardrails + Slack Bot

**What was built**:
- LangGraph ReAct agent with 12 tools (RAG, Jira 5, Slack 5, web search)
- MCP servers for Jira and Slack (streamable-http protocol)
- Human-in-the-Loop approval workflow using LangGraph interrupt()
- Evaluation pipeline: 22 golden tests, 5-metric scoring
- 5 runtime guardrails: PII detection, topic filter, token budget, loop protection, hallucination check
- Slack bot entry point (Socket Mode — no public URL needed)
- DuckDuckGo web search for real-time information
- Full Docker containerisation (6 services, 17/17 validation tests)
- 9 tutorials, 12 troubleshooting issues documented

**Skills gained**:

| Skill | Depth | What Was Learned |
|-------|-------|-----------------|
| LangGraph orchestration | Deep | StateGraph, ReAct loop, interrupt(), Command(resume=...) |
| Tool/Skill design | Deep | Tool definitions, read vs write tools, tool selection by LLM |
| MCP protocol | Moderate | Server implementation, streamable-http transport |
| Human-in-the-Loop | Deep | interrupt(), checkpointing, approve/reject/edit flows |
| Eval & testing | Moderate | Golden test sets, 5-metric scoring, automated eval runner |
| Guardrails | Moderate | PII regex, topic filtering, hallucination detection |
| Multi-entry-point design | Deep | Same agent serves Streamlit, Slack bot, and raw API |
| Slack bot development | Moderate | Socket Mode, Block Kit, interactive buttons |
| Web search integration | Basic | DuckDuckGo as fallback tool, KB-first strategy |
| Docker for AI stacks | Deep | Multi-service compose, shared volumes, DNS resolution |

**Career relevance**: AI Agent Engineer is the fastest-growing role in 2025-2026. Companies are moving from "chatbots that answer questions" to "agents that take actions." This phase demonstrates the full lifecycle: design, build, test, deploy, and validate.

---

## 3. The AI Engineering Landscape

### Four Career Tracks

```
                        RESEARCH                          APPLICATION
                           │                                  │
                ┌──────────┼──────────┐          ┌───────────┼───────────┐
                │          │          │          │           │           │
           ┌────▼────┐ ┌──▼──────┐  │    ┌─────▼─────┐ ┌──▼────────┐  │
           │ ML/     │ │ ML Ops  │  │    │ RAG/      │ │ AI Agent  │  │
           │ Research│ │ Engineer│  │    │ Knowledge │ │ Engineer  │  │
           │ Engineer│ │         │  │    │ Engineer  │ │           │  │
           └─────────┘ └─────────┘  │    └───────────┘ └───────────┘  │
                │          │        │          │           │           │
                │          │        │          │           │           │
           Train models  Deploy   Scale    Build RAG    Orchestrate   │
           Fine-tune     models   infra    Chunking     agents        │
           Datasets      CI/CD    Monitor  Search       Tools, HITL   │
           RLHF          A/B test          Eval         Multi-agent   │
                                                                      │
                                                        ┌─────────────▼─┐
                                                        │ AI Platform   │
                                                        │ Engineer      │
                                                        │               │
                                                        │ All of the    │
                                                        │ above +       │
                                                        │ cloud infra   │
                                                        └───────────────┘
                                                              ▲
                                                              │
                                                         YOU ARE HERE
```

### Coverage by Track

| Track | Focus | Your Coverage | Notes |
|-------|-------|--------------|-------|
| **ML/Research Engineer** | Train models, fine-tune, RLHF, datasets | ❌ Not covered | Requires deep ML/math background. Not your path (and that's fine) |
| **MLOps Engineer** | Deploy models, CI/CD for ML, A/B testing | 🟡 Partial | You can deploy but haven't done model training pipelines |
| **RAG/Knowledge Engineer** | Retrieval pipelines, embeddings, search quality | ✅ **Strong** | Deep hands-on across chunking, search, multi-source |
| **AI Agent Engineer** | Orchestration, tools, HITL, multi-agent | ✅ **Strong & growing** | 12 tools, eval, guardrails, Slack bot — production patterns |
| **AI Platform Engineer** | All of above + cloud infrastructure | ✅ **Your sweet spot** | Cloud background + AI skills = rare combination |

---

## 4. What Makes This Path Valuable

### The Market Gap

```
Traditional Engineer:          AI Researcher:           AI Platform Engineer (You):
  ✅ Can deploy                  ✅ Can build models       ✅ Can build AI apps
  ✅ Understands infra           ❌ Can't deploy           ✅ Can deploy them
  ❌ Can't build AI apps         ❌ Doesn't understand     ✅ Understands infra
  ❌ No ML knowledge               production concerns    ✅ Production-grade
                                                          ✅ Cost-aware
                                                          ✅ Observable & reliable
```

Most companies have plenty of ML researchers but **very few people who can take an AI concept and ship it as a reliable, observable, scalable system**. Your cloud engineering background is a **massive advantage**, not a gap.

### Skills Inventory (Honest Self-Assessment)

| Skill | Level | Evidence |
|-------|-------|---------|
| RAG pipeline (end-to-end) | ⭐⭐⭐⭐ | Multi-source, hybrid search, chunking strategies, frontend UX |
| Agent orchestration | ⭐⭐⭐⭐ | LangGraph ReAct, 12 tools, HITL, web search |
| Cloud deployment for AI | ⭐⭐⭐⭐⭐ | ECS, Bedrock, OpenSearch, Terraform, Docker |
| Production patterns | ⭐⭐⭐⭐ | Guardrails, eval, error handling, cost management |
| Eval & testing | ⭐⭐⭐ | Golden tests, 5-metric scoring, guardrail suites |
| Multi-agent systems | ⭐⭐ | Designed (docs/07), not yet built |
| Prompt engineering | ⭐⭐⭐ | System prompts, tool descriptions, ReAct prompting |
| Fine-tuning / training | ⭐ | Not covered — separate learning path |
| Observability for AI | ⭐⭐ | Basic logging — need LangSmith/OpenTelemetry |
| Memory & personalization | ⭐ | Planned (P6) — LangGraph Store |

---

## 5. What's Still Ahead

### Remaining Roadmap (From FUTURE-ROADMAP.md)

| Project | Status | Key Skills to Gain |
|---------|--------|-------------------|
| P3: Multi-Agent Supervisor | 📋 Planned | Agent handoff, shared state, supervisor routing |
| P4: Scheduled/Long-Running | ❌ Not started | Background execution, cron triggers, progress reporting |
| P6: Memory & Personalisation | ❌ Not started | Cross-session memory, user profiles, LangGraph Store |
| P7: Multi-Modal | ❌ Not started | Vision API, code execution sandbox, file processing |

### Skills to Develop Next

| Gap | Why It Matters | Suggested Approach |
|-----|---------------|-------------------|
| **Multi-agent orchestration** | Complex tasks need specialised agents collaborating | Build P3 — supervisor + research/action/report agents |
| **Observability & tracing** | Production debugging across multi-step agent flows | Integrate LangSmith or OpenTelemetry into agent backend |
| **Evaluation at scale** | Systematic quality measurement, not just spot checks | RAGAS/DeepEval integration, regression suites in CI/CD |
| **Memory & context** | Agents that remember past interactions are far more useful | LangGraph Store, conversation summarization |
| **Fine-tuning basics** | Sometimes RAG isn't enough — model needs domain adaptation | Fine-tune a small model (Mistral/Llama) on platform health data |
| **MCP ecosystem** | Standard protocol is growing — more servers, more integrations | Build or integrate MCP servers for monitoring tools (Datadog, PagerDuty) |

---

## 6. Three Concrete Projects to Complete the Picture

### Project A: Multi-Agent System (P3) — Est. 2-3 days
**What**: Supervisor agent routing to Research, Action, and Report sub-agents
**Why**: Proves you can design systems where agents collaborate, not just individual tool-calling agents
**Skills**: Agent handoff, shared state, supervisor patterns, partial failure handling

### Project B: Observability Layer — Est. 1-2 days
**What**: Add LangSmith or custom tracing to the agent backend
**Why**: "How do you debug an agent in production?" is a common interview question
**Skills**: Distributed tracing, token usage tracking, latency profiling, error attribution

### Project C: Memory & Personalisation (P6) — Est. 2-3 days
**What**: Cross-session memory using LangGraph Store
**Why**: Stateless agents repeat themselves; real assistants remember context
**Skills**: Long-term memory patterns, user profiles, conversation summarization

Completing A + B + C would bring coverage to approximately **80-85%** of what's expected from a senior AI Agent/Platform Engineer role.

---

## 7. The Narrative for Interviews

### "Tell me about your AI experience"

> "I've built AI systems from three angles:
>
> **First, deep RAG engineering** — I built a knowledge retrieval system from scratch, handling multi-source ingestion (Confluence, web, PDF), tested different chunking strategies, and built a full frontend with source management and conversation memory.
>
> **Second, cloud deployment** — I took that RAG system and deployed it to AWS using ECS Fargate, Bedrock Knowledge Base, and OpenSearch Serverless, all managed by Terraform. I did cost analysis and built a destroy/rebuild playbook.
>
> **Third, AI agent orchestration** — I built an action-taking agent with 12 tools (RAG, Jira, Slack, web search), human-in-the-loop approval workflows, evaluation pipelines, runtime guardrails, and a Slack bot entry point. The entire stack runs in Docker with 17 automated validation tests.
>
> What makes my approach different is that I come from a cloud platform engineering background — I don't just build AI demos, I build production-grade systems with proper error handling, cost awareness, observability, and deployment automation."

---

## 8. Projects & Evidence Summary

| Project | Repo/Folder | Key Artifacts |
|---------|-------------|--------------|
| Local RAG Stack | `platform-health-agent/` | 7 steps, Weaviate, Streamlit, multi-source ingestion |
| AWS Cloud Deployment | `aws-deploy/` | Terraform, ECS Fargate, Bedrock KB, cost analysis |
| AI Agent System | `project-125/` | 12 tools, HITL, eval, guardrails, Slack bot, Docker (6 services) |

**Total**: ~30 tutorials, ~50 test scenarios, 12 documented troubleshooting issues, 3 architecture docs, and a comprehensive future roadmap.

---

*Created 2026-03-27 — Career evolution reflection after completing 3 AI engineering projects.*
