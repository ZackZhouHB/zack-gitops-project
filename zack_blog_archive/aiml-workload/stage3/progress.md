# Stage 3 Progress

> **Last Updated:** 2026-02-01 10:45 AEDT

---

## Part 1: Infrastructure Adaptation ✅ COMPLETE

### Tasks

- [x] Deploy Weaviate to K8s
- [x] Adapt RAG backend for local vLLM
- [x] Build and deploy RAG backend image
- [x] End-to-end test ✅
- [x] Update AI Gateway with RAG routes ✅
- [x] Add RAG metrics to Prometheus ✅
- [x] Add RAG panels to Grafana dashboard ✅

### Part 1 COMPLETE ✅

---

## Session Log

### 2026-02-01 (Sunday) - Part 1 Core Complete

**What We Built:**

1. **Weaviate Vector Database**
   - Deployed as K8s Deployment with PVC (10Gi)
   - Service: `weaviate:8080`
   - No external vectorizer (we handle embeddings ourselves)

2. **RAG Backend (Simplified from rag-v1)**
   - Multi-backend LLM support: vLLM, Ollama, Bedrock
   - Multi-backend embeddings: Ollama, Bedrock
   - Prometheus metrics: `rag_queries_total`, `rag_query_latency_seconds`, `rag_documents_indexed_total`
   - Endpoints: `/upload`, `/query`, `/documents`, `/health`, `/metrics`

3. **Configuration**
   ```
   LLM_BACKEND=vllm        → http://llm-server:8000
   EMBED_BACKEND=ollama    → http://192.168.50.61:11434
   EMBED_MODEL=nomic-embed-text
   WEAVIATE_URL=http://weaviate:8080
   ```

4. **Test Results**
   ```
   Upload: test.txt → 1 chunk indexed
   Query: "What is Kubernetes?" 
   Answer: Correct response from context
   Latency: 421ms (embed: ~50ms, search: ~10ms, generate: ~360ms)
   ```

**Architecture:**
```
┌─────────────────────────────────────────────────────────────────┐
│                      ai-platform namespace                       │
│                                                                  │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌───────────┐ │
│  │   vLLM     │  │  Weaviate  │  │    RAG     │  │    AI     │ │
│  │   (GPU)    │  │  (Vector)  │  │  Backend   │  │  Gateway  │ │
│  │            │  │            │  │            │  │           │ │
│  │ Qwen2.5-3B │  │ Documents  │  │ /upload    │  │ /v1/chat  │ │
│  │ :8000      │  │ :8080      │  │ /query     │  │ /metrics  │ │
│  └─────▲──────┘  └─────▲──────┘  │ :8001      │  │ :8080     │ │
│        │               │         └──────┬─────┘  └───────────┘ │
│        │               │                │                       │
│        └───────────────┴────────────────┘                       │
│                    RAG Backend orchestrates                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                        ┌───────────┐
                        │  Ollama   │  Embeddings
                        │  (WSL)    │  nomic-embed-text
                        │  :11434   │
                        └───────────┘
```

**Files Created:**
| File | Purpose |
|------|---------|
| `stage3/README.md` | Stage 3 overview and plan |
| `stage3/progress.md` | This file |
| `stage3/k8s-manifests/weaviate.yaml` | Weaviate deployment |
| `stage3/k8s-manifests/rag-backend.yaml` | RAG backend deployment |
| `stage3/src/rag-backend/` | Simplified RAG backend code |

**Key Differences from rag-v1:**
| Aspect | rag-v1 | Stage 3 RAG |
|--------|--------|-------------|
| LLM | Bedrock Claude | vLLM (local GPU) |
| Embeddings | Bedrock Titan | Ollama nomic-embed-text |
| Deployment | Docker Compose | Kubernetes |
| Complexity | Full features | Simplified core |
| Cost | ~$0.003/query | $0 (local) |

---

## Current Cluster State

```bash
kubectl get pods -n ai-platform
NAME                           READY   STATUS    
ai-gateway-cbfcf5c7d-lwlm7     1/1     Running   
rag-backend-6bd6db58c9-zxnzx   1/1     Running   
vllm-69df57bfc9-54qz6          1/1     Running   
weaviate-768f7d4f98-hsqwc      1/1     Running   

kubectl get svc -n ai-platform
NAME          TYPE        PORT(S)
ai-gateway    ClusterIP   8080
llm-server    ClusterIP   8000
rag-backend   ClusterIP   8001
weaviate      ClusterIP   8080
```

---

## Next: Remaining Part 1 Tasks

~~1. **Update AI Gateway** - Add `/v1/rag/*` routes to proxy RAG backend~~
~~2. **Add RAG metrics to Grafana** - Query latency, documents indexed~~

All Part 1 tasks complete!

---

## Grafana RAG Dashboard Panels

Added RAG-specific panels to AI Gateway Dashboard:

| Panel | Metric | Purpose |
|-------|--------|---------|
| RAG Queries Total | `rag_queries_total` | Total queries by status |
| RAG Query Rate | `rate(rag_queries_total[1m])` | Queries per second |
| Documents Indexed | `rag_documents_indexed_total` | Total docs in system |
| RAG Success Rate | success/total * 100 | Query success percentage |
| RAG Query Latency (p50/p95/p99) | `histogram_quantile()` | Latency percentiles |
| RAG Latency Distribution | Heatmap | Latency distribution over time |

**Test Results (10 queries):**
- `rag_queries_total{status="success"}`: 10
- `rag_documents_indexed_total`: 2
- Average latency: ~1.1s per query
- Latency distribution: 50% under 1s, 90% under 2s

---

## Part 2: AI Engineer Tasks (Future)

These are deferred to a future stage focused on RAG quality:

- [ ] Advanced chunking strategies (LangChain RecursiveCharacterTextSplitter)
- [ ] RAG evaluation metrics (RAGAS)
- [ ] Conversation memory
- [ ] Hybrid search (keyword + vector)
- [ ] Re-ranking
