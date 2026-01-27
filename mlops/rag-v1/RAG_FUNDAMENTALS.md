# RAG Fundamentals & Your Solution Explained

## Part 1: Why RAG Exists

### The Problem with Pure LLMs
- **Hallucinations** - makes up facts confidently
- **Knowledge cutoff** - doesn't know recent info
- **No private data access** - can't see your company docs
- **Can't cite sources** - no traceability

### How RAG Solves This
```
User Question → Search YOUR docs → Feed relevant chunks to LLM → Grounded answer
```

**RAG = Retrieval-Augmented Generation**
- Retrieval: Find relevant documents
- Augmented: Add them to the prompt
- Generation: LLM generates answer using that context

---

## Part 2: Core RAG Components

### 2.1 Document Processing Pipeline
```
Raw Docs → Load → Chunk → Embed → Store in Vector DB
```

**Your Implementation:**
| Component | What You Use | Why |
|-----------|--------------|-----|
| Loader | S3 + file upload | Store docs centrally |
| Chunker | `RecursiveCharacterTextSplitter(1000, 200)` | Split docs into searchable pieces |
| Embeddings | Amazon Titan Embed | Convert text to vectors |
| Vector DB | Weaviate | Store and search vectors |

### 2.2 Query Pipeline
```
User Query → Embed → Vector Search → Top-K chunks → LLM + Context → Answer
```

**Your Implementation:**
| Component | What You Use | Why |
|-----------|--------------|-----|
| Embeddings | Amazon Titan Embed | Same model as indexing |
| Retriever | Weaviate similarity search | Find relevant chunks |
| LLM | Claude 3.5 Haiku via Bedrock | Generate answers |
| Chain | `ConversationalRetrievalChain` | Combines retrieval + generation |

---

## Part 3: Your Architecture Explained

### Components in Your Solution

**1. Weaviate (Vector Database)**
- Stores document chunks as vectors
- Enables semantic similarity search
- "Find documents SIMILAR to this question"

**2. Amazon Bedrock**
- Titan Embeddings: text → 1024-dim vector
- Claude Haiku: generates answers from context

**3. LangChain**
- Framework that connects all pieces
- Handles: chunking, embedding, retrieval, prompting

**4. Session Memory (`ConversationBufferWindowMemory`)**
- Remembers last 20 turns per user
- Enables follow-up questions: "What about the second point?"

**5. S3**
- Stores original documents
- Source of truth for uploads

---

## Part 4: Key Concepts to Explain in Interviews

### Chunking
**What:** Breaking documents into smaller pieces
**Why:** 
- LLMs have token limits
- Smaller chunks = more precise retrieval
- Your setting: 1000 chars with 200 overlap

**Interview Answer:**
> "I use RecursiveCharacterTextSplitter with 1000 token chunks and 200 overlap. The overlap ensures we don't lose context at chunk boundaries. For production, I'd consider semantic chunking based on document structure."

### Embeddings
**What:** Converting text to numerical vectors
**Why:** Enables semantic search (meaning, not just keywords)

**Interview Answer:**
> "I use Amazon Titan embeddings which produce 1024-dimensional vectors. The key is using the SAME embedding model for both indexing and querying - otherwise similarity scores are meaningless."

### Vector Search
**What:** Finding similar vectors using distance metrics
**Why:** "What documents are semantically similar to this question?"

**Interview Answer:**
> "Weaviate uses cosine similarity to find the top-K most relevant chunks. I retrieve 5 chunks by default - enough context without overwhelming the LLM's context window."

### Retrieval Chain
**What:** LangChain's `ConversationalRetrievalChain`
**Why:** Combines retrieval + memory + generation

**Interview Answer:**
> "The chain first retrieves relevant chunks, then combines them with conversation history, and sends everything to Claude. This enables contextual follow-up questions."

---

## Part 5: Interview Q&A Cheat Sheet

### Q: "Walk me through your RAG architecture"
> "Documents are uploaded to S3, chunked into 1000-token pieces with overlap, embedded using Titan, and stored in Weaviate. When a user queries, I embed the question, do vector similarity search to get top-5 chunks, then pass those to Claude via Bedrock to generate a grounded answer. I use LangChain's ConversationalRetrievalChain which also maintains session memory for follow-up questions."

### Q: "Why Weaviate over Pinecone/Chroma?"
> "Weaviate is open-source and can be self-hosted on EKS, giving us full control over data residency - critical for enterprise clients. It also supports hybrid search combining vector and keyword matching."

### Q: "Why Bedrock over direct OpenAI?"
> "Bedrock keeps data within AWS, important for compliance. It also provides access to multiple models (Claude, Titan, Llama) through a single API, avoiding vendor lock-in."

### Q: "How do you handle conversation context?"
> "I use LangChain's ConversationBufferWindowMemory with a 20-turn window per session. This lets users ask follow-up questions while preventing memory from growing unbounded. Sessions auto-expire after 60 minutes."

---

*Continue in Part 2: Advanced Patterns & Enterprise Gaps*


---

## Part 6: Advanced RAG Patterns (What You're Missing)

| Pattern | What It Does | Your Gap |
|---------|--------------|----------|
| **Hybrid Search** | Vector + keyword (BM25) | You only do vector |
| **Reranking** | Re-score results with cross-encoder | No reranking |
| **Query Expansion** | Generate query variations | Single query only |
| **CRAG** | Validate retrieval, fallback if bad | No validation |

### Hybrid Search Explained
```
Query → [Vector Search: semantic] + [BM25: exact keywords] → Merge → Top-K
```
**Why:** Vector misses exact terms like "SKU-12345" or "Error Code 500"

### Reranking Explained
```
Query → Retrieve Top-20 → Cross-Encoder Rerank → Return Top-5
```
**Why:** Vector search optimizes for recall, reranker optimizes for precision

---

## Part 7: Agents vs RAG

| Capability | RAG | Agents |
|------------|-----|--------|
| Answer from docs | ✅ | ✅ |
| Call APIs | ❌ | ✅ |
| Multi-step reasoning | ❌ | ✅ |
| Create/update data | ❌ | ✅ |

**When to use Agents:**
- Need to DO things (create ticket, send email)
- Multi-step tasks ("find issue, then update status")
- Dynamic tool selection

**Your Gap:** No agent capabilities yet - pure RAG only

---

## Part 8: Enterprise Gaps in Your Solution

| Gap | Business Risk | How to Fix |
|-----|---------------|------------|
| No access control | Users see all docs | Add metadata filtering |
| No auth | Anyone can query | Add OAuth/JWT |
| No audit logs | Can't trace who asked what | Add structured logging |
| No PII filtering | May leak sensitive data | Add output guardrails |
| Single model | High cost at scale | Add model routing |

---

## Part 9: Framework Comparison

| Framework | Best For | Your Use |
|-----------|----------|----------|
| **LangChain** | General RAG, chains | ✅ Using |
| **LangGraph** | Agentic workflows, state machines | ❌ Not using |
| **CrewAI** | Multi-agent teams | ❌ Not using |
| **Bedrock Agents** | Managed AWS agents | ❌ Not using |

---

## Part 10: Your Tech Stack Summary

```
┌─────────────────────────────────────────────────────┐
│                    Frontend (React)                  │
└─────────────────────┬───────────────────────────────┘
                      │ HTTP/REST
┌─────────────────────▼───────────────────────────────┐
│              FastAPI Backend (Python)                │
│  ┌─────────────────────────────────────────────┐    │
│  │           LangChain Framework               │    │
│  │  - ConversationalRetrievalChain             │    │
│  │  - RecursiveCharacterTextSplitter           │    │
│  │  - ConversationBufferWindowMemory           │    │
│  └─────────────────────────────────────────────┘    │
└──────┬──────────────┬──────────────┬────────────────┘
       │              │              │
┌──────▼─────┐ ┌──────▼─────┐ ┌──────▼─────┐
│  Weaviate  │ │  Bedrock   │ │    S3      │
│ Vector DB  │ │Claude+Titan│ │  Storage   │
└────────────┘ └────────────┘ └────────────┘
       │              │              │
└──────────────┴──────────────┴──────────────┘
                    EKS Cluster
```

**Key Talking Points:**
1. "Fully containerized on EKS for scalability"
2. "Weaviate self-hosted for data control"
3. "Bedrock for managed LLM without ops overhead"
4. "LangChain for rapid development and flexibility"
