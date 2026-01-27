# RAG Fundamentals - Complete Interview Guide

## Part 1: Why RAG Exists

### The Problem with Pure LLMs
- **Hallucinations** - Makes up facts confidently
- **Knowledge cutoff** - Doesn't know recent info
- **No private data access** - Can't see your company docs
- **Can't cite sources** - No traceability

### How RAG Solves This
```
User Question → Search YOUR docs → Feed relevant chunks to LLM → Grounded answer
```

**RAG = Retrieval-Augmented Generation**
- **Retrieval**: Find relevant documents
- **Augmented**: Add them to the prompt
- **Generation**: LLM generates answer using that context

---

## Part 2: Core RAG Pipeline

### 2.1 Ingestion Pipeline
```
Raw Docs → Load → Chunk → Embed → Store in Vector DB
```

| Stage | What Happens | Our Implementation |
|-------|--------------|-------------------|
| Load | Parse PDF/DOCX/TXT/images | Multi-format loader |
| Chunk | Split into searchable pieces | `RecursiveCharacterTextSplitter(1000, 200)` |
| Embed | Convert text to vectors | Amazon Titan Embed (1536-dim) |
| Store | Index for search | Weaviate with metadata |

### 2.2 Query Pipeline
```
User Query → Embed → Search → Retrieve → Rerank → Generate → Answer
```

| Stage | What Happens | Our Implementation |
|-------|--------------|-------------------|
| Embed | Query to vector | Same Titan model |
| Search | Find similar chunks | Hybrid (vector + BM25) |
| Retrieve | Get top-K candidates | Top 10 candidates |
| Rerank | Re-score for precision | LLM-based reranking |
| Generate | Create answer | Claude 3 Haiku |

---

## Part 3: Hybrid Search (Vector + Keyword)

### The Problem with Vector-Only Search
```
Query: "Error code SKU-12345"
Vector search: Finds docs about "errors" and "products" (semantic)
Misses: Exact match for "SKU-12345" (literal)
```

### Hybrid Search Solution
```
Query → [Vector Search] + [BM25 Keyword] → Merge with alpha → Top-K
```

| Alpha | Behavior | Use Case |
|-------|----------|----------|
| 0.0 | Pure keyword (BM25) | Exact matches, codes, IDs |
| 0.5 | Balanced (default) | General queries |
| 1.0 | Pure vector | Semantic/conceptual queries |

**Interview Answer:**
> "We use hybrid search combining vector similarity with BM25 keyword matching. The alpha parameter controls the blend - 0.5 for balanced, lower for exact matches like error codes, higher for conceptual questions. This catches both semantic meaning AND exact terms that vector search might miss."

---

## Part 4: Reranking

### Why Rerank?
```
Initial retrieval (recall-focused): Get 20 candidates
Reranking (precision-focused): Score and return top 5
```

| Stage | Optimizes For | Method |
|-------|---------------|--------|
| Retrieval | Recall (don't miss relevant) | Fast vector search |
| Reranking | Precision (most relevant first) | LLM cross-attention |

### Our Implementation
```python
# Retrieve more candidates than needed
docs = retriever.search(query, top_k=10)

# Rerank with LLM
reranked = reranker.rerank(query, docs, top_k=5)
```

**Interview Answer:**
> "We over-retrieve 10 candidates then use LLM-based reranking to select the top 5. The initial retrieval optimizes for recall - not missing relevant docs. The reranker optimizes for precision - putting the most relevant first. This two-stage approach significantly improves answer quality."

---

## Part 5: Source-Aware Retrieval

### The Problem
```
User: "What is blog 148 about?"
Vector search: Finds semantically similar content, NOT post 148
```

### Solution: Auto-Detect Source References
```python
# Regex detects: "blog 148", "post 148", "document #123"
match = re.search(r'(?:blog|post|document)\s*#?(\d+)', question)
if match:
    source_filter = f"post/{match.group(1)}"
```

**Interview Answer:**
> "When users reference documents by ID like 'blog 148', semantic search fails because '148' isn't in the content. We auto-detect these patterns and apply source filtering before retrieval. This is critical for enterprise systems where users reference tickets, documents, or records by ID."

---

## Part 6: Security Layers

### Defense in Depth
```
User → Auth → Rate Limit → Input Validation → RAG → PII Filter → Response
```

| Layer | What It Does | Our Implementation |
|-------|--------------|-------------------|
| Authentication | Verify identity | JWT tokens |
| Authorization | Check permissions | Row-level access control |
| Rate Limiting | Prevent abuse | 30 req/min per user |
| Input Validation | Block attacks | Prompt injection detection |
| PII Filtering | Protect sensitive data | Regex patterns |
| Audit Logging | Track everything | JSONL audit trail |

### Row-Level Access Control
```python
# Documents have allowed_groups metadata
doc.metadata = {"allowed_groups": ["engineering", "admin"]}

# Query filters by user's groups
if "engineering" in user.groups:
    # Can see engineering docs
```

**Interview Answer:**
> "We implement defense in depth: JWT authentication, row-level access control on documents, rate limiting to prevent abuse, input validation for prompt injection, and PII filtering on outputs. Every query is audit-logged for compliance. In production, we'd add AWS Bedrock Guardrails for managed content filtering."

---

## Part 7: Production Patterns

### Response Caching
```
Query → Hash → Check Cache → Hit? Return cached : Execute & Cache
```
- **Result**: 4000ms → 8ms for repeated queries
- **Key**: Hash includes query + parameters (top_k, search_type)

### Model Routing
```
Query → Classify Complexity → Route to Model
Simple: "What is X?" → Claude Haiku (fast, cheap)
Complex: "Compare A vs B with analysis" → Claude Sonnet (smart)
```

### Token Tracking
```python
tracker.track(user_id, model, input_tokens, output_tokens)
# Returns: {"requests": 10, "estimated_cost": "$0.05"}
```

**Interview Answer:**
> "We implement response caching with query hashing - repeated questions return in 8ms instead of 4 seconds. Model routing automatically selects Haiku for simple queries and Sonnet for complex analysis, optimizing cost. Token tracking monitors usage per user for cost allocation and abuse detection."

---

## Part 8: Conversation Memory

### The Challenge
```
User: "What is RAG?"
Assistant: "RAG is..."
User: "Tell me more about the retrieval part"  ← Needs context!
```

### Our Implementation
```python
class ConversationMemory:
    max_turns = 10        # Cap history size
    prompt_turns = 3      # Only send last 3 to LLM
    timeout = 60 min      # Auto-cleanup
```

| Feature | Why |
|---------|-----|
| Session isolation | Each user has separate history |
| History limit | Prevent unbounded growth |
| Prompt limit | Control token costs |
| Auto-cleanup | Free memory for idle sessions |

### Scaling Sessions (Production)
```
Local: In-memory dict (single instance)
Production: Redis (horizontal scaling, persistence)
```

**Interview Answer:**
> "We maintain conversation memory per session with a 10-turn limit. Only the last 3 turns are sent to the LLM to control token costs. Sessions auto-expire after 60 minutes. For production, we'd use Redis instead of in-memory storage to support horizontal scaling and persistence across restarts."

---

## Part 9: Data Pipeline Patterns

### Real-World Ingestion
```
┌─────────────────────────────────────────────────────────┐
│  S3 Upload → EventBridge → SQS → Lambda → Vector DB    │
└─────────────────────────────────────────────────────────┘
```

| Pattern | How It Works | When to Use |
|---------|--------------|-------------|
| Event-Driven | S3 trigger → Lambda | Real-time ingestion |
| Scheduled | Cron → Poll sources | Batch updates |
| CDC | DB triggers | Database sync |
| Webhook | Source pushes | External integrations |

### Our Implementation
```bash
# Create scheduled sync job
POST /pipeline/jobs
{"name": "blog-sync", "source_type": "web", "source_config": {...}}

# Manual trigger
POST /pipeline/jobs/blog-sync/run
```

**Interview Answer:**
> "We support both event-driven and scheduled ingestion. For real-time, S3 uploads trigger processing via EventBridge and SQS. For batch, we have scheduled jobs that poll sources like internal wikis. Change detection via content hashing ensures we don't re-ingest unchanged documents. Failed items go to a dead-letter queue for investigation."

---

## Part 10: Agent Pattern (ReAct)

### RAG vs Agents
| Capability | RAG | Agents |
|------------|-----|--------|
| Answer from docs | ✅ | ✅ |
| Call APIs/tools | ❌ | ✅ |
| Multi-step reasoning | ❌ | ✅ |
| Create/update data | ❌ | ✅ |

### ReAct Pattern
```
Thought: I need to find information about X
Action: search_documents("X")
Observation: Found 3 relevant documents...
Thought: Now I can answer the question
Action: generate_answer(context)
```

### Our Implementation (5 Tools)

| Tool | Description | Trigger |
|------|-------------|---------|
| `search_docs` | RAG search | what, how, why, explain |
| `list_sources` | List documents | list, all documents |
| `calculate` | Math operations | numbers with +/-/*// |
| `get_date` | Current date/time | today, date, now |
| `compare_docs` | Compare docs | compare, versus |

```bash
# Test agent
curl -X POST http://localhost:8001/agent \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is todays date?"}'
# Result: tools_used: ["get_date", "search_docs", "answer"]

curl -X POST http://localhost:8001/agent \
  -d '{"query": "Calculate 25 * 4"}'
# Result: tools_used: ["calculate", "answer"], answer: "100"
```

### Enterprise Agent Patterns

**Multi-Tool Agents:**
```
Agent Tools: search_docs, query_database, call_api, 
             send_email, create_ticket, human_handoff
```

**Multi-Agent Systems:**
```
Router Agent → Specialist Agents (Finance, HR, IT Support)
```

**AWS Bedrock Agents (Managed):**
```
Knowledge Base (RAG) + Action Groups (Lambda) + Guardrails
```

### Cloud Deployment Options

| Approach | Pros | Cons |
|----------|------|------|
| Custom (EKS) | Full control | Maintain code |
| Bedrock Agent | Managed, guardrails | Less flexibility |

**Interview Answer:**
> "We implement the ReAct pattern with 5 tools: search, list, calculate, date, and compare. For production, I'd consider Bedrock Agents which provide managed orchestration, built-in guardrails, and Lambda-based action groups for external integrations like ticket creation or API calls."

See `AGENT.md` for full documentation.

---

## Part 11: LangChain Usage

### What We Use vs Don't Use
| Component | LangChain? | Why |
|-----------|------------|-----|
| Text Splitter | ✅ Yes | Well-tested chunking |
| Embeddings | ❌ Direct boto3 | More control |
| LLM calls | ❌ Direct boto3 | Better debugging |
| Chains | ❌ Custom | No hidden abstractions |
| Agents | ❌ Custom ReAct | Demonstrate understanding |
| Vector Store | ❌ Direct Weaviate | No wrapper overhead |

**Interview Answer:**
> "We use LangChain's text splitter because it's well-tested, but we use direct boto3 calls for Bedrock. This gives us more control over parameters, clearer error traces, and avoids LangChain's frequent API changes. In production, you might use LangChain more heavily if your team is familiar with it, but I wanted to show the underlying mechanics."

---

## Part 12: Interview Q&A Cheat Sheet

### "Walk me through your RAG architecture"
> "Documents are uploaded, chunked with overlap, embedded using Titan, and stored in Weaviate with metadata. Queries go through hybrid search combining vector and BM25, then LLM reranking for precision. Results are passed to Claude with conversation history for contextual answers. We have JWT auth, row-level access control, rate limiting, and audit logging throughout."

### "How do you improve retrieval quality?"
> "Three techniques: First, hybrid search combines semantic vectors with BM25 keyword matching - catches both meaning and exact terms. Second, we over-retrieve then rerank with an LLM for precision. Third, source filtering auto-detects document references like 'blog 148' that semantic search would miss."

### "How do you handle security?"
> "Defense in depth: JWT authentication, row-level document permissions, rate limiting per user, input validation for prompt injection, PII filtering on outputs, and comprehensive audit logging. In production, we'd add Bedrock Guardrails for managed content filtering."

### "How do you control costs?"
> "Four mechanisms: Response caching reduces repeated query costs by 99%. Model routing sends simple queries to Haiku, complex to Sonnet. Token tracking monitors usage per user. Rate limiting prevents abuse."

### "How do you scale?"
> "Stateless backend scales horizontally. Sessions would move to Redis. Job queue would use SQS. Vector DB would use OpenSearch Serverless. Ingestion would use Lambda for auto-scaling."

### "Why not just use LangChain for everything?"
> "LangChain is great for prototyping but adds abstraction that can hide issues. We use it for text splitting but direct boto3 for Bedrock calls. This gives us more control, clearer debugging, and avoids breaking changes in LangChain's API."

---

## Part 13: Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                 │
│                    React + localStorage                          │
│         [Login] [Chat] [Upload] [Documents] [New Chat]          │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│                      BACKEND API                                 │
│                  FastAPI + JWT Auth                              │
│                                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │   RAG    │ │  Agent   │ │ Security │ │ Pipeline │           │
│  │ Service  │ │ (ReAct)  │ │          │ │          │           │
│  │          │ │          │ │• JWT     │ │• Async   │           │
│  │• Hybrid  │ │• Tools   │ │• RBAC    │ │• Jobs    │           │
│  │• Rerank  │ │• Reason  │ │• Audit   │ │• Sync    │           │
│  │• Cache   │ │          │ │• PII     │ │• Web     │           │
│  │• Memory  │ │          │ │• Rate    │ │          │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
└──────┬──────────────────────────────┬───────────────────────────┘
       │                              │
┌──────▼──────┐                ┌──────▼──────┐
│  Weaviate   │                │   Bedrock   │
│  Vector DB  │                │             │
│             │                │• Titan Embed│
│• Hybrid     │                │• Claude 3   │
│• BM25       │                │             │
└─────────────┘                └─────────────┘
```

---

## Part 14: Quick Reference Card

| Topic | Key Points |
|-------|------------|
| **Hybrid Search** | Vector + BM25, alpha parameter (0=keyword, 1=vector) |
| **Reranking** | Over-retrieve 10, rerank to 5, improves precision |
| **Source Filter** | Auto-detect "blog 148", filter before search |
| **Security** | JWT, RBAC, rate limit, input validation, PII filter, audit |
| **Caching** | Query hash, 4s→8ms, include params in key |
| **Model Routing** | Simple→Haiku, Complex→Sonnet |
| **Memory** | 10 turns max, 3 to LLM, 60min timeout, Redis for prod |
| **Pipeline** | Event-driven or scheduled, change detection, DLQ |
| **Agent** | ReAct pattern, thought→action→observation loop |
| **LangChain** | Only text splitter, direct boto3 for control |

---

## Part 15: What's NOT Implemented (Production Gaps)

| Feature | Why Skipped | Production Solution |
|---------|-------------|---------------------|
| Bedrock Guardrails | Requires AWS setup | Enable in console |
| PII Tokenization | Needs Vault | HashiCorp Vault |
| Redis Sessions | Extra container | AWS ElastiCache |
| Real Connectors | Needs API keys | OAuth + REST |
| Kubernetes | Infra scope | EKS + Helm |
| CI/CD | DevOps scope | CodePipeline |
| Observability | Extra setup | CloudWatch + X-Ray |

**Interview Answer:**
> "This demo covers the RAG patterns. For production, I'd add Bedrock Guardrails for content filtering, Redis for session scaling, real OAuth for connectors, and full observability with CloudWatch and X-Ray. The architecture is designed to swap these in without changing the core logic."


---

## Part 16: Cloud Deployment (AWS Production)

### Local vs Cloud Architecture

```
LOCAL (rag-v1)                    CLOUD (rag-cloud)
─────────────────                 ─────────────────
Docker Compose          →         EKS (Kubernetes)
Weaviate (1536-dim)     →         OpenSearch Serverless (1024-dim)
In-memory queue         →         SQS
In-memory cache         →         Redis on EKS
Nginx container         →         S3 + CloudFront
localhost               →         ALB + CloudFront
Mock JWT                →         Cognito (optional)
```

### Cloud Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              USERS                                       │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────────────┐
│                           CloudFront                                     │
│                      (CDN + HTTPS + Caching)                            │
└──────────────┬──────────────────────────────────────┬───────────────────┘
               │                                      │
┌──────────────▼──────────────┐        ┌──────────────▼──────────────┐
│      S3 (Frontend)          │        │         ALB                 │
│   React Static Assets       │        │   Application Load Balancer │
└─────────────────────────────┘        └──────────────┬──────────────┘
                                                      │
┌─────────────────────────────────────────────────────▼───────────────────┐
│                              EKS Cluster                                 │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐    │ │
│  │  │ Backend Pod     │  │ Worker Pod      │  │ Redis (Helm)    │    │ │
│  │  │ (FastAPI)       │  │ (SQS Consumer)  │  │ (Cache)         │    │ │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘    │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└──────┬──────────────────┬──────────────────┬────────────────────────────┘
       │                  │                  │
┌──────▼──────┐    ┌──────▼──────┐    ┌──────▼──────┐    ┌─────────────┐
│ OpenSearch  │    │   Bedrock   │    │     S3      │    │     SQS     │
│ Serverless  │    │             │    │  Documents  │    │ Ingest Queue│
│ (1024-dim)  │    │• Titan v2   │    │             │    │             │
│             │    │• Claude 3   │    │             │    │             │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### Key Technical Differences

| Aspect | Local (rag-v1) | Cloud (rag-cloud) |
|--------|----------------|-------------------|
| Vector DB | Weaviate (1536-dim) | OpenSearch Serverless (1024-dim) |
| Embedding | Titan v1 | Titan v2 |
| Search | `script_score` + cosine | Native kNN (no script_score) |
| Doc IDs | Custom IDs allowed | Auto-generated only |
| Queue | In-memory | SQS |
| Frontend | Nginx container | S3 + CloudFront |

### OpenSearch Serverless Gotchas

**1. No script_score with cosineSimilarity**
```python
# ❌ Doesn't work in Serverless
"script_score": {"script": {"source": "cosineSimilarity(params.query_vector, 'vector')"}}

# ✅ Use native kNN instead
"knn": {"vector": {"vector": query_vector, "k": top_k}}
```

**2. No custom document IDs**
```python
# ❌ Doesn't work
self.client.index(index=name, id=doc_id, body=body)

# ✅ Let OpenSearch generate ID
self.client.index(index=name, body=body)
```

**3. Different embedding dimensions**
```python
# Local: Titan v1 = 1536 dimensions
# Cloud: Titan v2 = 1024 dimensions
def create_index(self, dimension: int = 1024):  # Changed from 1536
```

### Cost Analysis (ap-southeast-2)

| Service | Monthly Cost |
|---------|--------------|
| EKS Control Plane | $73 |
| EC2 (t3.large node) | $61 |
| OpenSearch Serverless (2 OCUs) | $86 |
| NAT Gateway | $32 |
| ALB | $16 |
| S3, SQS, DynamoDB | ~$5 |
| **Infrastructure Total** | **~$272** |
| Bedrock (moderate usage) | ~$28 |
| **Grand Total** | **~$300/month** |

### Cost Optimization Options

1. **Spot Instances** for EKS nodes (-60-70%)
2. **Schedule OpenSearch** off-hours (50% savings)
3. **Remove NAT Gateway** if public subnets acceptable
4. **Aggressive CloudFront caching** to reduce Bedrock calls

### Deployment Steps (Summary)

```bash
# 1. Infrastructure (Terraform)
cd terraform && terraform apply

# 2. Configure kubectl
aws eks update-kubeconfig --name rag-cloud-dev

# 3. Build & push images
docker build -t rag-cloud-backend ./backend
docker push <ecr-url>/rag-cloud-dev-backend:latest

# 4. Create IAM roles (IRSA)
aws iam create-role --role-name rag-cloud-backend-role ...

# 5. Deploy to K8s
kubectl apply -f k8s/

# 6. Install ALB controller
helm install aws-load-balancer-controller eks/aws-load-balancer-controller

# 7. Deploy frontend
npm run build && aws s3 sync dist/ s3://frontend-bucket/
```

### Interview Answer: "How would you deploy this to production?"

> "I'd use EKS for container orchestration, OpenSearch Serverless for managed vector search, and S3+CloudFront for the frontend. Key changes from local: Titan v2 embeddings (1024-dim), native kNN instead of script_score, SQS for async processing. IAM roles via IRSA for pod-level permissions. The architecture costs ~$300/month for dev, with options to optimize using Spot instances and scheduled scaling."

### Cleanup Order (Important!)

```bash
# 1. CloudFront (disable first, wait, then delete)
# 2. K8s resources (removes ALB)
# 3. IAM roles (created outside Terraform)
# 4. Empty S3 buckets
# 5. Terraform destroy
```

**Why this order?** CloudFront takes 5+ minutes to disable. K8s ingress creates ALB that must be deleted before VPC. S3 buckets must be empty before Terraform can delete them.

---

## Part 17: Complete Feature Matrix

All 26 features work in both local and cloud deployments:

| # | Feature | Local | Cloud | Notes |
|---|---------|-------|-------|-------|
| 1 | Health Check | ✅ | ✅ | Same |
| 2 | JWT Auth | ✅ | ✅ | Same |
| 3 | RBAC | ✅ | ✅ | Same |
| 4 | Sync Upload | ✅ | ✅ | Same |
| 5 | Async Upload | ✅ | ✅ | SQS-backed |
| 6 | Vector Search | ✅ | ✅ | Different backend |
| 7 | Hybrid Search | ✅ | ✅ | Adapted query |
| 8 | Reranking | ✅ | ✅ | Same |
| 9 | Query | ✅ | ✅ | Same |
| 10 | Streaming | ✅ | ✅ | Same |
| 11 | Model Routing | ✅ | ✅ | Same |
| 12 | Memory | ✅ | ✅ | Same |
| 13 | ReAct Agent | ✅ | ✅ | Same |
| 14 | Caching | ✅ | ✅ | Redis |
| 15 | Rate Limiting | ✅ | ✅ | Same |
| 16 | Audit Logs | ✅ | ✅ | Same |
| 17 | Usage Tracking | ✅ | ✅ | Same |
| 18 | Web Connector | ✅ | ✅ | Same |
| 19 | Pipelines | ✅ | ✅ | Same |
| 20 | Source Filter | ✅ | ✅ | Same |
| 21 | Chat History | ✅ | ✅ | localStorage |
| 22 | Delete Docs | ✅ | ✅ | Same |
| 23 | Markdown Render | ✅ | ✅ | Same |
| 24 | Multi-chat | ✅ | ✅ | Same |
| 25 | PII Filter | ✅ | ✅ | Same |
| 26 | Input Validation | ✅ | ✅ | Same |
