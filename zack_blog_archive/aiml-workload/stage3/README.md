# Stage 3: RAG on Local AI Platform

> **Objective:** Integrate existing RAG system with local AI infrastructure  
> **Source:** Adapt `mlops/rag-v1` to run on Minikube with vLLM  
> **Duration:** Part 1 (2-3 hours), Part 2 (4-6 hours optional)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MINIKUBE CLUSTER                                    │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    ai-platform namespace                             │   │
│  │                                                                      │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │   │
│  │  │ AI Gateway  │  │    vLLM     │  │  Weaviate   │  │ RAG Backend│ │   │
│  │  │             │  │   (GPU)     │  │ (Vector DB) │  │  (FastAPI) │ │   │
│  │  │ Routes:     │  │             │  │             │  │            │ │   │
│  │  │ /v1/chat/*  │  │ Qwen2.5-3B  │  │ Embeddings  │  │ From       │ │   │
│  │  │ /v1/rag/*   │──│             │  │ + Documents │  │ rag-v1     │ │   │
│  │  │ /metrics    │  │ :8000       │  │ :8080       │  │ :8001      │ │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘ │   │
│  │                                                                      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    monitoring namespace                               │   │
│  │  ┌─────────────┐  ┌─────────────┐                                    │   │
│  │  │ Prometheus  │  │  Grafana    │  ← Now includes RAG metrics        │   │
│  │  └─────────────┘  └─────────────┘                                    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
   ┌───────────┐                 ┌───────────┐
   │  Ollama   │                 │  Bedrock  │
   │  (WSL)    │                 │  (AWS)    │
   │ Fallback  │                 │ Fallback  │
   └───────────┘                 └───────────┘
```

---

## Part 1: Infrastructure Adaptation (AI Infra Focus) ✅ COMPLETE

### Tasks

| Task | Status | Description |
|------|--------|-------------|
| Deploy Weaviate to K8s | ✅ | Deployment with 10Gi PVC |
| Adapt RAG backend config | ✅ | Point to vLLM + Ollama embeddings |
| Build RAG backend image | ✅ | rag-backend:v1 |
| Deploy RAG backend to K8s | ✅ | Deployment + Service |
| Update AI Gateway routing | ✅ | Added `/v1/rag/*` routes |
| Add RAG metrics to Grafana | ✅ | 6 RAG-specific panels |
| Test end-to-end | ✅ | Upload doc → Query → Response |

### Component Changes

| Component | rag-v1 (Docker) | Local K8s | Change |
|-----------|-----------------|-----------|--------|
| LLM | Bedrock Claude | vLLM Qwen | `LLM_BACKEND=vllm` |
| Embeddings | Bedrock Titan | Ollama/vLLM | `EMBED_BACKEND=ollama` |
| Vector DB | Weaviate :8080 | Weaviate K8s svc | `WEAVIATE_URL=http://weaviate:8080` |
| Frontend | React :3000 | Skip for now | Focus on API |

### Files to Create

```
stage3/
├── README.md                    # This file
├── progress.md                  # Session tracking
├── k8s-manifests/
│   ├── weaviate.yaml           # Weaviate StatefulSet
│   └── rag-backend.yaml        # RAG backend Deployment
└── src/
    └── rag-backend/            # Adapted from rag-v1
        ├── Dockerfile
        ├── requirements.txt
        └── app/                # Modified config
```

---

## Part 2: RAG Enhancement (AI Engineer Focus) - OPTIONAL

### Topics to Explore

| Topic | Description | Complexity |
|-------|-------------|------------|
| Semantic Chunking | Split by meaning, not fixed size | MEDIUM |
| Recursive Chunking | LangChain RecursiveCharacterTextSplitter | LOW |
| HyDE | Generate hypothetical doc for better retrieval | MEDIUM |
| Multi-Query | Generate multiple queries for broader retrieval | MEDIUM |
| Reranking | LLM-based reranking (already in rag-v1) | ✅ Done |
| RAGAS Evaluation | Measure retrieval quality | HIGH |
| LangChain LCEL | Modern chain composition | MEDIUM |
| Agents | Tool-using agents (already in rag-v1) | ✅ Done |

### What rag-v1 Already Has

Your existing RAG is quite advanced:
- ✅ Hybrid search (vector + BM25)
- ✅ LLM reranking
- ✅ ReAct agent with tools
- ✅ Conversation memory
- ✅ Response caching
- ✅ Async processing

### What Could Be Enhanced

| Current | Enhancement | Benefit |
|---------|-------------|---------|
| Fixed chunking | Semantic chunking | Better context boundaries |
| Single query | Multi-query retrieval | Higher recall |
| No evaluation | RAGAS metrics | Measurable quality |
| Custom agent | LangChain agents | Industry standard |

---

## Success Criteria

### Part 1 Complete When:
1. Weaviate running in K8s with persistent storage
2. RAG backend deployed, using vLLM for generation
3. Can upload document via API
4. Can query and get response with sources
5. Metrics visible in Grafana

### Part 2 Complete When:
1. Implemented at least 2 new retrieval techniques
2. Added evaluation metrics (RAGAS or custom)
3. Documented improvements with before/after comparison

---

## Interview Talking Points

### Part 1 (AI Infra):
> "I migrated a production RAG system from AWS (Bedrock + Weaviate on Docker) to local Kubernetes (vLLM on GPU + Weaviate StatefulSet), demonstrating infrastructure portability and hybrid cloud patterns."

### Part 2 (AI Engineer):
> "I enhanced the RAG pipeline with semantic chunking and HyDE retrieval, improving retrieval accuracy by X%. I used RAGAS to measure and validate improvements."

---

## Commands Reference

```bash
# SSH to WSL
ssh -p 2222 root@192.168.50.61

# Check all pods
kubectl get pods -n ai-platform

# Test RAG endpoint
curl -X POST http://<gateway>/v1/rag/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is in my documents?"}'

# Check Weaviate
kubectl exec -n ai-platform deploy/weaviate -- curl -s localhost:8080/v1/meta
```
