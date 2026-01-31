# AI Platform Engineer - Final Learning Path (2025-2026)

> **Goal:** Transition from Senior Cloud Engineer to AI Platform Engineer  
> **Philosophy:** "Build Systems, Not Scripts." Focus on Reliability, Evaluation, and Scale.  
> **Resume Keywords:** *Agentic Workflows, Hybrid Search, Eval-Driven Development, MCP, Type-Safe Agents*

---

## The 2026 AI Engineer Reality

| What HR Wants | How You'll Prove It |
|---------------|---------------------|
| Agentic Workflows | LangGraph + CrewAI + Google ADK (not just one framework) |
| Production RAG | LlamaIndex + Hybrid Search + Re-ranking + Ragas eval scores |
| Type-Safe Systems | PydanticAI with validated I/O |
| LLMOps | Phoenix tracing, cost monitoring, CI/CD evals |
| Standards Awareness | MCP servers, OpenTelemetry |
| Cloud + Self-Hosted | Bedrock for prod, vLLM/Ollama for dev |

---

## Your Infrastructure Lab

| Resource | Specs | Role |
|----------|-------|------|
| **MacBook Pro M4** | 16GB RAM | **Control Plane:** Code, Docker, LangGraph logic, LiteLLM router, all frameworks |
| **Desktop PC** | RTX 5070 Ti | **Compute Plane:** vLLM (production inference), Qdrant, Ragas eval jobs |
| **AWS Account** | Personal | **Prod Environment:** Bedrock, Knowledge Bases, EKS validation, Terraform state |

---

## Month 1: Modern AI Frameworks + Data Strategy

**Theme:** Master the tools on every job posting + smart model routing

### Week 1: Unified Model Interface (LiteLLM + LlamaIndex)

**Concept:** Enterprises never rely on one model. They use routers.

**LiteLLM (The Router):**
- [ ] Install LiteLLM: `pip install litellm`
- [ ] Configure to route `gpt-4` → Bedrock Claude, `gpt-3.5` → Ollama
- [ ] Write code that swaps models via config, not code changes

**LlamaIndex (The Data Framework):**
- [ ] `pip install llama-index llama-index-llms-bedrock llama-index-embeddings-bedrock`
- [ ] Build RAG: load → chunk → embed → query
- [ ] Implement **Hierarchical Indexing** on a complex PDF:
  - Summary index for high-level questions
  - Vector chunks for specific details
- [ ] Add `CitationQueryEngine` for source attribution

**Deliverable:** LlamaIndex RAG with LiteLLM routing, comparing "Basic Chunking" vs "Hierarchical Retrieval"

### Week 2: Agentic Workflows (LangGraph)

**Concept:** "Chains" are dead. Agents that loop and self-correct are the standard.

**Tasks:**
- [ ] `pip install langgraph langchain-aws`
- [ ] Understand graph paradigm: nodes, edges, state
- [ ] Build a "Researcher Agent":
  1. Search Wikipedia (Tool)
  2. LLM checks: "Is this info sufficient?"
  3. If No → Loop back, search Google
  4. If Yes → Summarize
- [ ] Implement human-in-the-loop approval flow
- [ ] Add checkpointing for long-running agents

**Deliverable:** LangGraph StateGraph diagram + working agent with loop logic

### Week 3: Type-Safe Agents (PydanticAI)

**Concept:** Production agents need validated I/O, not string parsing.

**Why PydanticAI:**
- Created by Pydantic team (FastAPI validation)
- Type-safe inputs/outputs - errors at dev time, not runtime
- OpenTelemetry native
- Dependency injection for tools

**Tasks:**
- [ ] `pip install pydantic-ai`
- [ ] Build agent with structured Pydantic output models
- [ ] Implement tool with dependency injection
- [ ] Add retry logic with validation
- [ ] Compare: PydanticAI vs raw Bedrock invoke

**Deliverable:** Type-safe agent returning validated JSON, not strings

### Week 4: Multi-Agent Systems (Google ADK + CrewAI)

**Concept:** Different paradigms for multi-agent orchestration.

**Google ADK:**
- [ ] `pip install google-adk`
- [ ] Build multi-agent workflow: researcher → writer → reviewer
- [ ] Implement callbacks for lifecycle control
- [ ] Add session/memory for stateful conversations

**CrewAI (Comparison):**
- [ ] `pip install crewai`
- [ ] Build same workflow with role-based crew
- [ ] Compare: ADK (orchestration) vs CrewAI (delegation)

**Deliverable:** Same task implemented in both frameworks + comparison notes

---

## Month 2: Production AI Infrastructure

**Theme:** Latency, Throughput, Search Engineering, and the "AI Gateway" Pattern

### Week 5: Advanced Search Engineering (Hybrid + Rerank)

**Concept:** Semantic search fails on keywords (SKUs, names). You need Hybrid.

**Tasks:**
- [ ] **Qdrant** on Desktop: `docker run -p 6333:6333 qdrant/qdrant`
- [ ] Implement **Hybrid Search:**
  - Sparse Vectors (BM25/Keyword) + Dense Vectors (Embeddings)
- [ ] **2-Stage Retrieval:**
  - Retrieve 50 docs → Re-rank top 5 with Cross-Encoder (`BAAI/bge-reranker`)
- [ ] Benchmark: latency, recall@k, MRR

**Resume Win:** "Implemented Hybrid Search with Cross-Encoder Reranking, improving retrieval precision by 40%"

**Deliverable:** Hybrid search pipeline with benchmark report

### Week 6: Production Inference (vLLM) + AI Gateway

**Concept:** Ollama = dev. vLLM = production. Gateway = control.

**vLLM (Desktop GPU):**
- [ ] Run Llama-3-8B with vLLM: `docker run --gpus all vllm/vllm-openai --model meta-llama/Llama-3-8B-Instruct`
- [ ] Enable **PagedAttention** to maximize batch size
- [ ] Benchmark with `locust`: vLLM vs Ollama tokens/sec

**AI Gateway Pattern:**
- [ ] Build middleware (Kong or custom FastAPI):
  1. Cache identical queries (Redis)
  2. Rate limit users (10 req/min)
  3. Log every prompt/response for auditing
  4. Route to vLLM or Bedrock based on load

**Deliverable:** Benchmark report + API that rejects spam requests

### Week 7: MCP (Model Context Protocol)

**Concept:** The emerging standard for AI tool integration.

**Why MCP:**
- Anthropic's open standard (Nov 2024), adopted by OpenAI, Google
- "USB for AI" - standardized tool integration
- Every major AI IDE supports it (Cursor, Claude Desktop)

**Tasks:**
- [ ] Understand MCP architecture: clients, servers, tools, resources
- [ ] Build MCP server exposing your RAG as a tool
- [ ] Create MCP server for AWS queries (S3, DynamoDB)
- [ ] Test with Claude Desktop or Cursor
- [ ] Implement OAuth2 for production auth

**Deliverable:** MCP server that lets any AI assistant query your knowledge base

### Week 8: Capstone - The "Air-Gapped" Platform

**Concept:** Simulating high-security Government/Bank deployment.

**Stack (All on Desktop, Docker Compose):**
```
┌─────────────────────────────────────────────┐
│           Air-Gapped AI Platform            │
├─────────────────────────────────────────────┤
│  Frontend:    Streamlit                     │
│  Backend:     FastAPI + LangGraph           │
│  Vector DB:   Qdrant (local volume)         │
│  Inference:   vLLM (GPU)                    │
│  Router:      LiteLLM                       │
│  Gateway:     Rate limiting + caching       │
└─────────────────────────────────────────────┘
```

**Constraint:** Pull the ethernet cable. Must work 100% offline.

**Deliverable:** Working offline platform + docker-compose.yml

---

## Month 3: LLMOps, Evaluation & Portfolio

**Theme:** "How do you know it works?" - The #1 Interview Question

### Week 9: Eval-Driven Development (EDD)

**Concept:** Unit tests for AI. This is the senior differentiator.

**Tasks:**
- [ ] `pip install ragas deepeval`
- [ ] Create "Golden Dataset" (20 Q&A pairs with ground truth)
- [ ] Score RAG on:
  - **Faithfulness** (did it hallucinate?)
  - **Answer Relevance** (did it answer the question?)
  - **Context Precision** (did it retrieve the right docs?)
- [ ] **CI/CD Integration:** Fail build if Faithfulness < 0.8
- [ ] Compare: naive RAG vs hybrid search vs re-ranking scores

**Resume Win:** "Integrated Ragas for automated CI/CD evaluation, maintaining 0.85 faithfulness score"

**Deliverable:** Eval pipeline that blocks bad deployments

### Week 10: LLMOps Observability + Security

**Observability:**
- [ ] Set up Arize Phoenix: `pip install arize-phoenix`
- [ ] Trace: prompt → LLM → tool calls → response
- [ ] Monitor: latency, token usage, error rates, cost
- [ ] Build dashboard showing RAG pipeline health

**Security & Guardrails:**
- [ ] Configure Bedrock Guardrails or NeMo Guardrails:
  1. Block political/sensitive topics
  2. Redact PII before sending to LLM
  3. Prevent jailbreaks ("Ignore previous instructions")

**Deliverable:** Observable, guarded AI pipeline

### Week 11: GitOps + AWS Native RAG

**Prompts as Code:**
- [ ] Move all prompts and RAG configs to Git repo
- [ ] GitHub Action: on push to `prompts.yaml` → run Ragas eval → deploy if pass

**AWS Bedrock Knowledge Bases (Terraform):**
- [ ] Deploy serverless RAG via IaC:
  - Data Source: S3
  - Vector Store: OpenSearch Serverless
  - Model: Claude 3.5 Sonnet
- [ ] `terraform apply` → test → `terraform destroy` (don't leave running!)

**Deliverable:** Terraform scripts + GitOps pipeline

### Week 12: System Design & Interview Prep

**Design Challenges:**
- [ ] "Design RAG for 10K concurrent users"
  → vLLM auto-scaling, semantic caching, Qdrant read-replicas
- [ ] "Handle a 100-page PDF"
  → LlamaIndex Hierarchical Node Parser + Parent Document Retriever
- [ ] "Reduce LLM costs by 50%"
  → Caching, smaller models for simple queries, batch inference

**Mock Interview:** Explain Air-Gapped Capstone using STAR method

---

## Resume Weapons (Final Skills List)

```
Languages:        Python (Advanced), SQL
Orchestration:    LangGraph, LiteLLM, CrewAI, Google ADK
Data Frameworks:  LlamaIndex (Hierarchical Retrieval), PydanticAI
Vector Databases: Qdrant, pgvector (Hybrid Search + Reranking)
Inference:        vLLM (PagedAttention), Ollama, AWS Bedrock
LLMOps:           Ragas (Evaluation), Arize Phoenix (Tracing), MCP
Security:         Bedrock Guardrails, NeMo Guardrails, PII Redaction
Infrastructure:   AWS (EKS, Lambda, Bedrock), Terraform, Docker, K8s
```

---

## Resume Bullets (Before → After)

| Before | After |
|--------|-------|
| Built RAG with Python | Engineered production RAG with LlamaIndex Hierarchical Retrieval, achieving 0.85 faithfulness via Ragas CI/CD evaluation |
| Used LangChain | Designed agentic workflows using LangGraph with self-correction loops, human-in-the-loop approval, and checkpoint recovery |
| Called Bedrock API | Built type-safe AI agents with PydanticAI, integrated via MCP protocol for standardized tool access |
| Deployed to AWS | Implemented AI Gateway pattern with semantic caching and rate limiting, reducing inference costs by 40% |
| Set up vector database | Implemented Hybrid Search with Cross-Encoder Reranking, improving retrieval precision by 40% |

---

## Framework Comparison Cheat Sheet

| Framework | Best For | Key Concept | When to Use |
|-----------|----------|-------------|-------------|
| **LlamaIndex** | RAG, data ingestion | Hierarchical indexing, query engines | Complex document retrieval |
| **LangGraph** | Complex agents | Stateful graphs, checkpoints, loops | Self-correcting workflows |
| **PydanticAI** | Type-safe agents | Validated I/O, dependency injection | Production reliability |
| **Google ADK** | Multi-agent | Sequential/parallel orchestration | Google ecosystem |
| **CrewAI** | Team agents | Roles, delegation | Role-based collaboration |
| **LiteLLM** | Model routing | Unified API, fallbacks | Multi-model strategy |
| **MCP** | Tool integration | Standardized protocol | Universal tool access |
| **Ragas** | RAG evaluation | Faithfulness, relevancy | CI/CD quality gates |
| **vLLM** | Production inference | PagedAttention, batching | High-throughput serving |

---

## Cost Strategy

| Item | Cost | Strategy |
|------|------|----------|
| **LiteLLM Router** | Free | Default to Ollama (free), route to Bedrock only for final checks |
| **vLLM** | Free | Run on Desktop GPU, saves ~$1.50/hr vs AWS g5.xlarge |
| **Bedrock API** | ~$20-50/mo | Use sparingly via router |
| **Knowledge Bases** | ~$700/mo idle | Terraform create → test → destroy immediately |
| **Phoenix/Ragas** | Free | Self-hosted, open source |
| **LangSmith** | Free tier | 5K traces/month |
| **Total** | **~$30/month** | Local-first, cloud for validation |

---

## Weekly Quick Reference

| Week | Focus | Key Tool | Deliverable |
|------|-------|----------|-------------|
| 1 | Model Routing + RAG | LiteLLM + LlamaIndex | Hierarchical RAG with routing |
| 2 | Agentic Workflows | LangGraph | Self-correcting agent |
| 3 | Type Safety | PydanticAI | Validated JSON outputs |
| 4 | Multi-Agent | ADK + CrewAI | Framework comparison |
| 5 | Search Engineering | Qdrant + Reranker | Hybrid search pipeline |
| 6 | Production Inference | vLLM + Gateway | Benchmark + rate limiting |
| 7 | Tool Integration | MCP | RAG-as-MCP-server |
| 8 | Capstone | Docker Compose | Air-gapped platform |
| 9 | Evaluation | Ragas | CI/CD quality gates |
| 10 | Observability | Phoenix + Guardrails | Traced, secured pipeline |
| 11 | GitOps + AWS | Terraform | IaC + prompt versioning |
| 12 | Interview | System Design | STAR method prep |

---

## What Makes This Path Different

1. **Framework Breadth** - LangGraph + CrewAI + ADK + PydanticAI (not just "I used LangChain")
2. **Measurable Outcomes** - Ragas scores, latency benchmarks, precision improvements
3. **Production Patterns** - AI Gateway, caching, rate limiting, hybrid search
4. **Standards Awareness** - MCP, OpenTelemetry (where industry is heading)
5. **Cost-Conscious** - Local-first with LiteLLM routing, cloud for validation only
6. **Security Built-In** - Guardrails, PII redaction, air-gapped deployment

---

## Start This Week

1. **Day 1-2:** Set up LiteLLM router (Ollama + Bedrock)
2. **Day 3-4:** Migrate your RAG to LlamaIndex with Hierarchical Indexing
3. **Day 5:** Add Ragas evaluation (instant quality metrics)
4. **Day 6-7:** Set up Phoenix tracing

You'll have a measurably better RAG in one week.

Ready to start with Week 1?
