# Project Wrap-Up — What We Built, Learned, and Shipped

> **Project**: Platform Health Insight Assistant  
> **Author**: Hongbo Zhou (NESA, NSW Education Standards Authority)  
> **Duration**: Full local build + AWS cloud deployment  
> **Final State**: All AWS resources destroyed (cost $0), code & docs preserved

---

## The Big Picture

We built a **production-grade AI assistant** that can answer questions about platform infrastructure by searching across multiple knowledge sources — PDFs, blog posts, and Confluence pages — using RAG (Retrieval-Augmented Generation) with an agentic workflow.

We built it **twice**: first locally with Docker Compose, then adapted and deployed it to AWS using fully-managed services. Along the way, we hit real production issues, debugged them, evolved the architecture, and documented everything.

```
LOCAL (Docker Compose)                    AWS (ECS Fargate)
┌────────────────────────┐                ┌─────────────────────────────────┐
│ Streamlit (8501)       │                │ ALB → Streamlit (Fargate)       │
│ FastAPI + LangGraph    │     ──→        │ FastAPI + LangGraph (Fargate)   │
│ Weaviate (vector DB)   │   Adapted      │ OpenSearch Serverless (vectors) │
│ PostgreSQL (state)     │                │ DynamoDB (state) + EFS (chat)   │
│ Manual ingestion       │                │ Bedrock KB (auto-sync 3 sources)│
└────────────────────────┘                └─────────────────────────────────┘
```

---

## Part 1: Local Deployment — Building the Foundation

### What We Built (14 commits, 8 steps)

#### Step 1: Infrastructure — Docker Compose
Set up 4 containerised services running locally:

| Service | Image | Purpose |
|---------|-------|---------|
| **Weaviate** | `semitechnologies/weaviate:latest` | Vector database (HNSW, cosine distance) |
| **PostgreSQL** | `postgres:16-alpine` | Checklists, escalation queue, tool call logs |
| **agent-backend** | Custom Python | FastAPI + LangGraph agent |
| **frontend** | Custom Python | Streamlit chat UI |

Key learning: Docker Compose orchestrates multi-container apps. Weaviate starts with health checks, backend waits for both Weaviate and Postgres before accepting requests.

#### Step 2: Data Ingestion Pipeline
Built a 3-source ingestion pipeline from scratch:

```
Sources → Load → Chunk → Embed → Store
```

| Source | Loader | Documents |
|--------|--------|-----------|
| Blog (`zackblog.work`) | HTTP scraper (requests + BeautifulSoup) | ~150 posts |
| Confluence | REST API with pagination | 8 design pages |
| Local files | PyPDF2 + markdown parser | 4 docs (PDFs, .md) |

**Chunking**: `RecursiveCharacterTextSplitter` — 2000 chars per chunk, 200 char overlap, respects paragraph → sentence → word boundaries.

**Embedding**: AWS Bedrock Titan Embed V2 — 1024-dimensional vectors, batch processed with rate limiting.

**Result**: 198 chunks from 24 documents indexed into Weaviate.

Key learning: Chunking strategy directly affects retrieval quality. Too small = context fragmentation. Too large = diluted relevance. The 500-token sweet spot with overlap is the industry default for good reason.

#### Step 3: RAG Tool — Semantic Search
Built `rag_tool.py` — the core retrieval engine:

```python
# User asks: "What is Karpenter?"
# 1. Embed the query → 1024d vector
# 2. Search Weaviate (cosine similarity, top-k=5)
# 3. Return ranked chunks with source attribution
# Result: 5 relevant chunks in 754ms
```

Key learning: Vector search is semantic, not keyword-based. "How does node scaling work?" finds Karpenter content even though "Karpenter" isn't in the query. This is the magic — and the limitation (no exact keyword matching).

#### Step 4: Basic LangGraph Agent
Created the agentic brain using LangGraph's `StateGraph`:

```
START → llm → [has tool calls?] → tools → llm → ... → END
```

The LLM (Claude Sonnet 4 via Bedrock) sees tool descriptions and decides when to search the knowledge base. This is the **ReAct pattern** — Reason + Act in a loop.

Key learning: The LLM doesn't "know" your documents. It decides to search, reads the results, then generates an answer grounded in those results. Without RAG, it hallucinates. With RAG, it cites sources.

#### Step 5: Multi-Tool Agent
Added 4 more tools beyond RAG search:

| Tool | Purpose | Storage |
|------|---------|---------|
| `rag_search` | Search knowledge base | Weaviate |
| `assess_incident` | Triage infrastructure problems | KB + pattern matching |
| `create_checklist` | Create trackable action items | PostgreSQL |
| `escalate_to_human` | Hand off complex issues | PostgreSQL |
| `policy_tool` | Check eligibility policies | In-memory rules |

Key learning: Tool descriptions ARE the routing logic. The LLM reads descriptions and decides which tool to call. Well-written descriptions = correct tool selection. Vague descriptions = chaos.

#### Step 6: Incident Triage Workflow
Added a structured multi-step workflow with branching:

```
gather_symptoms → search_docs → [confidence?]
                                 ├── high → known_fix → END
                                 ├── medium → investigate → END
                                 └── low → escalate → END
```

Plus a Router node to classify: is this a general question or an active incident?

Key learning: Structured workflows shine for well-defined processes (incident response, onboarding, approval chains). But they're rigid — if the router misclassifies, the entire conversation goes down the wrong path.

#### Step 7: Production Patterns
Added observability and resilience:
- Request/response logging with timing (every LLM call, every tool call)
- Loop protection (max iterations before forced exit)
- Tool execution error handling (catch, log, continue)
- Structured `tool_calls_log` for debugging

Key learning: Production agents need observability more than any other software. When the LLM makes a bad decision, you need to see exactly what it saw (the prompt), what it decided (the tool calls), and what happened (the tool results).

#### Step 8: Streaming UX
Replaced batch responses with Server-Sent Events (SSE):
- Tokens appear live as Claude generates them (ChatGPT-style)
- Source citations show after response completes
- Response latency displayed
- Tool usage indicators

Key learning: Streaming transforms the UX. A 20-second response feels like 2 seconds when you see tokens appearing immediately. SSE is simpler than WebSockets for this use case.

---

## Part 2: AWS Deployment — Moving to the Cloud

### What Changed (10 commits, 6 milestones)

#### M1: Terraform Infrastructure (49 Resources)

Replaced every local component with an AWS managed service:

| Local | AWS | Why |
|-------|-----|-----|
| Weaviate (Docker) | OpenSearch Serverless | Managed, auto-scales, no cluster ops |
| PostgreSQL (Docker) | DynamoDB | Serverless, on-demand pricing |
| Local file ingestion | Bedrock Knowledge Base | Auto-chunk, auto-embed, auto-index |
| Manual web scraping | Bedrock Web Crawler | Managed crawling with URL scope |
| Manual Confluence API | Bedrock Confluence Connector | Native integration, auth via Secrets Manager |
| `docker compose up` | ECS Fargate + ALB | Public URL, rolling deploys, health checks |
| Chat history in memory | EFS (Elastic File System) | Persists across container restarts |
| `~/.aws/credentials` | IAM Task Roles | No credentials in containers |

**Terraform files**: 13 files defining VPC config, ECS cluster/services/tasks, ALB with listeners, ECR repos, S3 bucket, Bedrock KB + 3 data sources, DynamoDB tables, EFS, Lambda, IAM roles/policies, security groups, CloudWatch log groups, Cloud Map service discovery.

Key learning: Terraform is declarative — you describe the end state, it figures out the order. But some resources have hidden dependencies (OpenSearch must be ACTIVE before creating the vector index, which must exist before creating the Bedrock KB).

#### M2: Docker Build & Deploy

Built images for Fargate (not your Mac):

```bash
docker build --platform linux/amd64 -t platform-health-backend .
```

Key learning: Apple Silicon (arm64) images don't run on Fargate (amd64). Always specify `--platform linux/amd64`. This is the #1 gotcha for Mac developers deploying to AWS.

Code adaptations:
- `boto3.Session(profile_name='sandboxtest')` → `boto3.Session()` (IAM task roles)
- `rag_tool.py` (Weaviate) → `kb_tool.py` (Bedrock KB Retrieve API)
- `db_tool.py` (PostgreSQL) → `dynamodb_tool.py` (DynamoDB)
- Chat history: PostgreSQL → EFS JSON files

#### M3: Data Sync & E2E Testing

Three data sources, each with different ingestion patterns:

| Source | Mechanism | Result |
|--------|-----------|--------|
| **S3** (4 docs) | Upload → Lambda auto-trigger → KB sync | 4 indexed |
| **Web crawler** | Bedrock crawls `zackblog.work` | 64 pages indexed (178 images skipped) |
| **Confluence** | Bedrock connects via API token | 40 pages indexed (8 target + related) |

Tested end-to-end: user question → ALB → Streamlit → FastAPI → LangGraph → Bedrock KB → OpenSearch → Claude → streamed answer with citations.

Key learning: "Serverless" doesn't mean "zero configuration." The Confluence connector needed exact secret format (`{"username":"...","password":"..."}`), the API token had a truncated suffix, and the filter regex needed tuning. Managed services save ops work but still require correct configuration.

#### M4: Confluence Deep-Dive & Debugging

The Confluence connector was the hardest source to get working:

| Issue | Root Cause | Fix |
|-------|------------|-----|
| "Failed to connect" | API token truncated (missing `=ABA7B279` suffix) | Copy full token |
| Still "Failed to connect" | Secret had extra `confluenceUrl` field | Exactly 2 keys only |
| Wrong pages indexed | Filter `.*ET.*` matched space key in URLs | Use specific title patterns |
| 58 scanned vs 8 expected | Connector scans entire space, filters during indexing | Expected behavior — extra pages don't hurt |

Key learning: Managed connectors are opaque. When they fail, the error messages are generic ("Failed to connect"). You debug by eliminating variables one at a time: test the token with `curl`, check the secret format against docs, verify the filter regex.

#### M5: Architecture Evolution — Removing the Router

This was the most important design decision of the entire project.

**The problem**: The router LLM classified "can you check" as an incident, sending it down the rigid incident_triage pipeline. The pipeline then crashed because import names differed between local and AWS (`db_tool` vs `dynamodb_tool`).

**The insight**: We had **two brains fighting** — a router LLM (sees only the message text) and a tool-calling LLM (sees system prompt + message + tool descriptions). The router was a worse version of what the ReAct loop already does.

**The fix**: Remove the router entirely. Single ReAct loop:

```
BEFORE: START → router → [general_qa | incident_triage] → ...
AFTER:  START → llm → [should_continue] → tools → llm → ... → END
```

**Result**: 0% error rate (was ~20%), all query types work, simpler code, easier to debug.

```python
# The key insight: tool descriptions ARE the routing logic
"rag_search": "ALWAYS use this tool first before answering ANY question..."
"assess_incident": "ONLY use when the user reports a SPECIFIC, ACTIVE infrastructure problem..."
```

Key learning: **Simpler architectures win.** A single LLM with well-described tools outperforms a complex router + workflow system. The router adds a failure mode without adding capability. Vector search handles content-type routing naturally — "Karpenter" finds the blog post, "Azure AD" finds the PDF, "pipeline design" finds the Confluence page. No router needed.

#### M6: Validation, Cost Analysis & Teardown

**15-test E2E validation** across all 3 sources:

| Source | Tests | Avg Score | Best |
|--------|-------|-----------|------|
| S3 (PDF/MD) | 4 | 57.5% | 65.4% |
| Web (blog) | 5 | 69.8% | 87.2% |
| Confluence | 4 | 49.6% | 59.6% |
| Cross-source | 2 | 60.6% | 64.3% |

100% pass rate, zero errors, zero empty responses. Keyword accuracy: 95%.

**Concurrency test**: 5 simultaneous requests all succeeded (FastAPI async handles concurrent users).

**Cost analysis**: ~$1,034/month idle, 94% from OpenSearch Serverless (4 OCU minimum). Decision: destroy and rebuild on demand (30-45 min with the playbook).

---

## Part 3: What We Learned — The Knowledge Map

### RAG Fundamentals

| Concept | What We Learned | Where |
|---------|----------------|-------|
| **Chunking** | 500-token chunks with 10-20% overlap is the sweet spot | Local Step 2 |
| **Embedding** | Titan V2 (1024d) works well for mixed English content | Both |
| **Vector search** | Semantic, not keyword — finds related concepts, misses exact terms | Both |
| **Hybrid search** | Vector + BM25 keyword search would improve exact matching | AWS comparison doc |
| **Re-ranking** | Cross-encoder second pass improves precision 10-20% | AWS comparison doc |
| **Source attribution** | Every chunk carries metadata (title, URL, source_type) for citations | Both |

### Agentic Workflows (LangGraph)

| Concept | What We Learned | Where |
|---------|----------------|-------|
| **ReAct pattern** | LLM reasons → acts (calls tools) → observes results → reasons again | Local Step 4 |
| **Tool descriptions** | They ARE the routing logic — invest design effort here | AWS M5 |
| **State management** | `TypedDict` with `add_messages` reducer — immutable, append-only | Both |
| **Loop protection** | Always cap iterations — LLMs can loop forever | Local Step 7 |
| **Router vs ReAct** | Single ReAct loop beats router + workflow for most use cases | AWS M5, Step 18 |
| **Structured workflows** | Good for well-defined processes, bad for open-ended questions | Local Step 6 |

### AWS Managed Services

| Service | What We Learned | Gotcha |
|---------|----------------|--------|
| **Bedrock KB** | Auto-chunk, auto-embed, auto-index — saves weeks of work | Default chunking is basic (~300 tokens, no overlap) |
| **OpenSearch Serverless** | Zero ops vector DB | $975/month MINIMUM (4 OCUs always-on) |
| **Bedrock Web Crawler** | HTTP-only, no JavaScript rendering | Blog infinite scroll = older posts not indexed |
| **Bedrock Confluence** | Native connector, 30-min setup | Exact secret format required, scans entire space |
| **ECS Fargate** | No servers to manage, rolling deploys | Need `--platform linux/amd64` on Apple Silicon |
| **ALB** | Public URL, path-based routing, health checks | `idle_timeout=120s` needed for SSE streaming |
| **IAM Task Roles** | No credentials in containers | Must remove all `profile_name` references |
| **EFS** | Persistent storage across container restarts | Cheaper than DynamoDB for chat history |

### AWS Managed vs Local RAG

| Dimension | AWS Managed | Local |
|-----------|-------------|-------|
| **Setup time** | Hours | Days to weeks |
| **Chunking control** | 5 strategies (can use Lambda for full custom) | Unlimited |
| **Image/table handling** | Limited | Full (OCR, Vision, Camelot) |
| **Web crawling** | HTTP-only | Playwright/Puppeteer (full JS) |
| **Hybrid search** | ❌ Not available | ✅ Weaviate, Elasticsearch |
| **Re-ranking** | ❌ Not available | ✅ Cohere, cross-encoders |
| **Scaling** | Automatic | Manual cluster management |
| **Cost (idle)** | ~$1,034/month | ~$0 (your laptop) |
| **Vendor lock-in** | High | Low |

**Bottom line**: AWS managed RAG gets you to **80% quality with 20% of the effort**. The last 20% requires custom components.

### Production Debugging

| Issue | Key Takeaway |
|-------|-------------|
| Empty frontend response | Always check backend logs first — frontend masks HTTP 500s |
| Import name mismatches | Local ≠ cloud — `db_tool` vs `dynamodb_tool`, field names differ |
| Router misclassification | One LLM call deciding the entire path = single point of failure |
| Confluence "Failed to connect" | Eliminate variables one at a time: token → format → filter |
| Blog posts missing | JavaScript rendering ≠ HTTP crawling — know your crawler's limits |

---

## Part 4: What We Shipped — The Deliverables

### Code

| Component | Files | Lines (approx) |
|-----------|-------|-----------------|
| **Local agent-backend** | 15+ Python files | ~2,500 |
| **Local frontend** | 1 Python file | ~200 |
| **Local ingestion** | 4 Python files | ~600 |
| **AWS agent-backend** | 12+ Python files (adapted) | ~2,000 |
| **AWS frontend** | 1 Python file | ~200 |
| **Terraform** | 13 HCL files | ~800 |
| **Lambda** | 1 Python file | ~50 |
| **Docker** | 4 Dockerfiles + 1 compose | ~100 |

### Documentation (28 files)

| Category | Files | Content |
|----------|-------|---------|
| **Local tutorials** | Steps 01-08 | Infrastructure → ingestion → RAG → agent → multi-tool → workflow → production patterns → streaming UX |
| **AWS tutorials** | Steps 09-18 | Architecture → Terraform → Bedrock KB → Lambda → IAM/ECS → backend code → frontend code → deploy/test → routing debug → routing design |
| **Design docs** | 6 files | Context, existing architecture, blueprint, local architecture, goals, implementation plan |
| **Operations** | 5 files | Session handoff, troubleshooting (14 issues), operations guide, rebuild playbook, cleanup & re-spin |
| **Analysis** | 2 files | AWS managed vs local RAG comparison, E2E validation report |

### Git History

**Local repo** (`platform-health-agent/`): 14 commits
```
fa90f87 → Session handoff
d436449 → Step 1: Infrastructure
7e6f2cf → Step 2: Data ingestion (198 chunks)
b15c878 → Step 3: RAG tool (semantic search)
35ce7e1 → Step 4: LangGraph agent
f9753ae → Step 5: Multi-tool agent
f46b541 → Step 6: Eligibility workflow
366f46b → Step 7: Production patterns
382103c → Step 8: Complete tutorials
9d9410e → Platform Health reskin
c240612 → Streaming UX
9e22843 → Final docs update
```

**AWS repo** (`aws-deploy/`): 10 commits
```
461d1a9 → Step 1: Scaffold AWS deployment
6fd20f8 → Steps 2-4: Terraform (49 resources)
47ce6b3 → Steps 6-9: Docker deploy + data sync + E2E
1fe1368 → Tutorials + ops guide + Confluence fix
fa0107e → Step 14: Backend code walkthrough
a346331 → Fix routing + imports + step-17 debugging
5e0d260 → Step 18: Routing design patterns
8fd52c2 → M5: Single ReAct loop + RAG comparison doc
c8c34ba → E2E validation (15 tests, 100% pass)
1271568 → M6: Teardown + cleanup guide
```

---

## Part 5: Skills Demonstrated

This project demonstrates hands-on experience with:

### AI / ML Engineering
- ✅ RAG pipeline design (chunking, embedding, retrieval, generation)
- ✅ Agentic workflows with LangGraph (ReAct, routing, multi-step)
- ✅ Tool-calling LLM patterns (descriptions as routing logic)
- ✅ Prompt engineering (system prompts, router prompts, tool descriptions)
- ✅ Multi-source knowledge integration (S3, web, Confluence)
- ✅ Evaluation & quality measurement (relevance scores, keyword accuracy, E2E tests)

### Cloud Architecture
- ✅ Infrastructure-as-Code (Terraform — 49 resources, 13 files)
- ✅ Containerised deployment (Docker, ECR, ECS Fargate)
- ✅ Serverless patterns (Lambda, DynamoDB, OpenSearch Serverless)
- ✅ AWS Bedrock (Knowledge Base, LLM inference, embeddings)
- ✅ Networking (ALB, security groups, Cloud Map service discovery)
- ✅ IAM design (task roles, execution roles, cross-service policies)

### Software Engineering
- ✅ FastAPI backend with async/streaming (SSE)
- ✅ Streamlit frontend with real-time token display
- ✅ Docker Compose multi-service orchestration
- ✅ Production patterns (logging, observability, error handling, loop protection)
- ✅ Architecture evolution (router → ReAct, documenting why)
- ✅ Comprehensive documentation (tutorials, troubleshooting, operations)

### DevOps / Operations
- ✅ CI/CD-ready Docker builds (`--platform linux/amd64`)
- ✅ Rolling ECS deployments with health checks
- ✅ CloudWatch log analysis and debugging
- ✅ Cost analysis and optimisation ($1,034/month → $0 with destroy/rebuild)
- ✅ Disaster recovery playbook (30-45 min full rebuild)

---

## Part 6: How to Resume

Everything is preserved locally. To continue or demo:

```bash
# LOCAL (immediate, free)
cd platform-health-agent
docker compose up -d
# Open http://localhost:8501

# AWS (30-45 min, ~$1,034/month while running)
cd aws-deploy
# Follow CLEANUP-AND-RESPIN.md phases 1-8
```

All tutorials, docs, and code are committed and ready. The knowledge is in the code, the docs, and this wrap-up.

---

*Built with: Python, FastAPI, LangGraph, Streamlit, AWS Bedrock, Terraform, Docker, Weaviate, OpenSearch Serverless, ECS Fargate, and a lot of debugging.*
