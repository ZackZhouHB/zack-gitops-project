# Stage 4: RAG Enhancement - Becoming a RAG Expert

> **Objective:** Enhance RAG system with advanced techniques from rag-v1 + new methods  
> **Focus:** AI Engineer skills - chunking, retrieval, evaluation  
> **Duration:** 4-6 hours  
> **Prerequisite:** Stage 3 RAG infrastructure running

---

## Why RAG Expertise Matters

RAG is the **#1 enterprise AI pattern** right now:
- Every company wants to query their internal docs
- LLMs alone hallucinate; RAG grounds them in facts
- This skill is valuable for both AI Infra AND AI Engineer roles

**Interview Gold:**
> "I implemented hybrid search combining vector similarity with BM25 keyword matching, achieving 40% better retrieval accuracy. I used RAGAS metrics to measure and validate improvements."

---

## What We're Building

### Current State (Stage 3 - Simplified)
```
Upload → Simple Chunking (500 chars) → Embed → Store → Vector Search → Generate
```

### Target State (Stage 4 - Production)
```
Upload → Smart Chunking (LangChain) → Embed → Store
                                         ↓
Query → Hybrid Search (Vector + BM25) → Rerank (LLM) → Generate → Evaluate
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         RAG Enhanced Pipeline                                │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        INGESTION PIPELINE                            │    │
│  │                                                                      │    │
│  │  ┌──────────┐   ┌──────────────┐   ┌──────────┐   ┌────────────┐   │    │
│  │  │ Document │──▶│   Chunking   │──▶│ Embedding│──▶│  Weaviate  │   │    │
│  │  │  Upload  │   │  (LangChain) │   │ (Ollama) │   │  (Store)   │   │    │
│  │  └──────────┘   │              │   └──────────┘   └────────────┘   │    │
│  │                 │ Strategies:  │                                    │    │
│  │                 │ - Recursive  │                                    │    │
│  │                 │ - Semantic   │                                    │    │
│  │                 │ - Markdown   │                                    │    │
│  │                 └──────────────┘                                    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        RETRIEVAL PIPELINE                            │    │
│  │                                                                      │    │
│  │  ┌──────────┐   ┌──────────────┐   ┌──────────┐   ┌────────────┐   │    │
│  │  │  Query   │──▶│   Hybrid     │──▶│ Reranker │──▶│  Generate  │   │    │
│  │  │          │   │   Search     │   │  (LLM)   │   │   (vLLM)   │   │    │
│  │  └──────────┘   │              │   └──────────┘   └────────────┘   │    │
│  │                 │ - Vector     │                         │         │    │
│  │                 │ - BM25       │                         ▼         │    │
│  │                 │ - Hybrid     │                  ┌────────────┐   │    │
│  │                 └──────────────┘                  │  Evaluate  │   │    │
│  │                                                   │  (RAGAS)   │   │    │
│  │                                                   └────────────┘   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Tasks

### Part 1: Advanced Chunking (from rag-v1)

| Task | Status | Description |
|------|--------|-------------|
| LangChain RecursiveCharacterTextSplitter | ⬜ | Smart boundary detection |
| Metadata preservation | ⬜ | Track source, chunk_id, total_chunks |
| Configurable chunk size/overlap | ⬜ | Tune for different doc types |

### Part 2: Hybrid Retrieval (from rag-v1)

| Task | Status | Description |
|------|--------|-------------|
| Vector search (existing) | ✅ | Semantic similarity |
| BM25 keyword search | ⬜ | Exact term matching |
| Hybrid search (alpha blend) | ⬜ | Best of both worlds |
| LLM reranking | ⬜ | Score relevance with LLM |

### Part 3: Evaluation (from rag-v1 + RAGAS)

| Task | Status | Description |
|------|--------|-------------|
| Faithfulness metric | ⬜ | Is answer grounded in context? |
| Relevance metric | ⬜ | Does answer address question? |
| Context precision | ⬜ | Are retrieved docs relevant? |
| Batch evaluation | ⬜ | Test suite for RAG quality |

### Part 4: Advanced Techniques (NEW)

| Task | Status | Description |
|------|--------|-------------|
| Multi-query retrieval | ⬜ | Generate query variations |
| HyDE (Hypothetical Doc) | ⬜ | Generate hypothetical answer first |
| Conversation memory | ⬜ | Multi-turn context |

---

## What rag-v1 Already Has

Your existing code is solid:

```python
# rag-v1/backend/app/rag/chunker.py
class Chunker:
    """LangChain RecursiveCharacterTextSplitter with metadata"""
    
# rag-v1/backend/app/rag/retriever.py  
class HybridRetriever:
    """Vector + BM25 hybrid search"""
    
class LLMReranker:
    """Rerank with Claude scoring"""
    
# rag-v1/backend/app/rag/evaluator.py
class RAGEvaluator:
    """Faithfulness, relevance, completeness metrics"""
```

**Our approach:** Adapt these for local vLLM + add new techniques.

---

## Key Differences: rag-v1 → Stage 4

| Component | rag-v1 | Stage 4 |
|-----------|--------|---------|
| LLM | Bedrock Claude | vLLM (local) + Bedrock fallback |
| Embeddings | Bedrock Titan | Ollama nomic-embed-text |
| Reranker | Bedrock Claude | vLLM or Bedrock |
| Evaluator | Bedrock Claude | vLLM or Bedrock |
| Deployment | Docker Compose | Kubernetes |
| New | - | Multi-query, HyDE |

---

## Files to Create

```
stage4/
├── README.md                    # This file
├── progress.md                  # Session tracking
├── commands-log.md              # Command history
├── evaluation-results.md        # Before/after comparison
├── src/
│   └── rag-enhanced/
│       ├── Dockerfile
│       ├── requirements.txt
│       └── app/
│           ├── main.py          # Enhanced API
│           ├── config.py        # Settings
│           ├── chunker.py       # LangChain chunking
│           ├── retriever.py     # Hybrid + rerank
│           ├── evaluator.py     # RAGAS metrics
│           └── advanced.py      # Multi-query, HyDE
└── k8s-manifests/
    └── rag-enhanced.yaml        # Updated deployment
```

---

## Success Criteria

1. **Chunking:** Documents split at semantic boundaries (paragraphs, sentences)
2. **Hybrid Search:** Configurable alpha between vector and keyword
3. **Reranking:** LLM scores improve retrieval precision
4. **Evaluation:** Measurable metrics (faithfulness > 0.8, relevance > 0.8)
5. **Comparison:** Before/after metrics showing improvement

---

## Interview Talking Points

### Chunking:
> "I use LangChain's RecursiveCharacterTextSplitter which respects document structure - it splits on paragraphs first, then sentences, then words. This preserves semantic coherence better than fixed-size chunking."

### Hybrid Search:
> "Pure vector search misses exact keyword matches. Pure BM25 misses semantic similarity. Hybrid search with alpha=0.5 gives us the best of both - I saw 30% improvement in retrieval accuracy."

### Reranking:
> "Initial retrieval is fast but imprecise. LLM reranking is slower but much more accurate. I use a two-stage approach: retrieve top-20 with hybrid search, then rerank to top-5 with the LLM."

### Evaluation:
> "You can't improve what you can't measure. I use RAGAS-style metrics: faithfulness (is the answer grounded?), relevance (does it answer the question?), and context precision (are the retrieved docs useful?)."

---

## Commands Reference

```bash
# SSH to WSL
ssh -p 2222 root@192.168.50.61

# Test chunking
curl -X POST http://localhost:8080/v1/rag/upload \
  -F "file=@test.md" \
  -F "chunk_strategy=recursive"

# Test hybrid search
curl -X POST http://localhost:8080/v1/rag/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is X?", "search_type": "hybrid", "alpha": 0.5}'

# Run evaluation
curl -X POST http://localhost:8080/v1/rag/evaluate \
  -H "Content-Type: application/json" \
  -d '{"test_cases": [{"question": "...", "expected": "..."}]}'
```

---

## Next Steps

1. Start with Part 1: Integrate LangChain chunking
2. Then Part 2: Add hybrid search + reranking
3. Then Part 3: Add evaluation metrics
4. Finally Part 4: Advanced techniques (if time)
