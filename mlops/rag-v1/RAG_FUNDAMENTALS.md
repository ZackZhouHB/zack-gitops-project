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

**Interview Answer:**
> "We implement the ReAct pattern for agentic queries. The agent reasons about what tools to use, executes them, observes results, and iterates until it can answer. This enables multi-step tasks like 'find all documents about AWS and summarize the key points' that pure RAG can't handle."

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
