# Stage 3 Commands Log

> **Purpose:** Document all commands executed for RAG integration  
> **Last Updated:** 2026-02-01 10:46 AEDT

---

## Session: 2026-02-01 (Sunday)

### Objective
Integrate RAG system with local AI platform (vLLM + Weaviate on K8s)

---

## Phase 3.1: Weaviate Deployment

### 1. Deploy Weaviate Vector Database

**Manifest:** `k8s-manifests/weaviate.yaml`

**Key Configuration:**
```yaml
# PVC for persistence
storage: 10Gi

# Weaviate settings
AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED: "true"
DEFAULT_VECTORIZER_MODULE: "none"  # We provide vectors externally
PERSISTENCE_DATA_PATH: "/var/lib/weaviate"

# Resources
requests: 512Mi RAM, 200m CPU
limits: 1Gi RAM, 500m CPU
```

**Command:**
```bash
ssh -p 2222 root@192.168.50.61 "kubectl apply -f stage3/k8s-manifests/weaviate.yaml"
```

**Result:** ✅ Weaviate running at `weaviate:8080`

**Difference from rag-v1:**
- rag-v1: Docker named volume (ephemeral)
- Stage 3: K8s PVC with 10Gi (persistent across restarts)

---

## Phase 3.2: RAG Backend Deployment

### 2. Pull Embedding Model to Ollama

**Command:**
```bash
ssh -p 2222 root@192.168.50.61 "curl http://localhost:11434/api/pull -d '{\"name\":\"nomic-embed-text\"}'"
```

**Result:** ✅ nomic-embed-text model available

**Why nomic-embed-text:**
- 768 dimensions (good balance of quality/speed)
- Fast inference (~50ms per embedding)
- Free (vs Bedrock Titan ~$0.0001/1K tokens)

---

### 3. Build RAG Backend Image

**Files created:**
- `src/rag-backend/app/main.py` - Simplified RAG API
- `src/rag-backend/app/config.py` - Multi-backend configuration
- `src/rag-backend/Dockerfile`
- `src/rag-backend/requirements.txt`

**Command:**
```bash
ssh -p 2222 root@192.168.50.61 "
cd /path/to/stage3/src/rag-backend
docker build -t rag-backend:v1 .
minikube image load rag-backend:v1
"
```

**Result:** ✅ Image loaded into Minikube

---

### 4. Deploy RAG Backend

**Manifest:** `k8s-manifests/rag-backend.yaml`

**Environment Configuration:**
```yaml
LLM_BACKEND: vllm
VLLM_URL: http://llm-server:8000
EMBED_BACKEND: ollama
OLLAMA_URL: http://192.168.50.61:11434
EMBED_MODEL: nomic-embed-text
WEAVIATE_URL: http://weaviate:8080
```

**Command:**
```bash
ssh -p 2222 root@192.168.50.61 "kubectl apply -f stage3/k8s-manifests/rag-backend.yaml"
```

**Result:** ✅ RAG backend running at `rag-backend:8001`

---

### 5. End-to-End Test

**Upload Document:**
```bash
echo "Kubernetes is an open-source container orchestration platform." > /tmp/test.txt
curl -X POST http://localhost:8080/v1/rag/upload -F "file=@/tmp/test.txt"
# Result: {"status":"ok","filename":"test.txt","chunks":1}
```

**Query:**
```bash
curl -X POST http://localhost:8080/v1/rag/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Kubernetes?"}'
# Result: {"answer":"Kubernetes is an open-source container orchestration platform...","sources":[...],"latency_ms":421}
```

**Result:** ✅ Full RAG pipeline working

---

## Phase 3.3: AI Gateway Integration

### 6. Update AI Gateway with RAG Routes

**Added to `stage2/src/gateway/main.py`:**
```python
RAG_BACKEND_URL = os.getenv("RAG_BACKEND_URL", "http://rag-backend:8001")

@app.post("/v1/rag/query")
async def rag_query(request: RAGQueryRequest):
    # Proxy to RAG backend
    
@app.post("/v1/rag/upload")
async def rag_upload(file: UploadFile):
    # Proxy file upload
    
@app.get("/v1/rag/documents")
async def rag_documents():
    # List indexed documents
```

**Rebuild & Deploy:**
```bash
ssh -p 2222 root@192.168.50.61 "
cd stage2/src/gateway
docker build -t ai-gateway:v6 .
minikube image load ai-gateway:v6
kubectl set image deployment/ai-gateway ai-gateway=ai-gateway:v6 -n ai-platform
"
```

**Result:** ✅ AI Gateway v6 with RAG routes

---

## Phase 3.4: Observability

### 7. Add RAG Backend to Prometheus

**Updated `stage2/k8s-manifests/monitoring/prometheus.yaml`:**
```yaml
scrape_configs:
  - job_name: 'rag-backend'
    static_configs:
      - targets: ['rag-backend.ai-platform.svc.cluster.local:8001']
    metrics_path: /metrics
```

**Command:**
```bash
ssh -p 2222 root@192.168.50.61 "kubectl apply -f stage2/k8s-manifests/monitoring/prometheus.yaml"
```

**Result:** ✅ Prometheus scraping RAG metrics

---

### 8. Add RAG Panels to Grafana Dashboard

**Updated `stage2/k8s-manifests/monitoring/grafana.yaml`:**

Added 6 new panels:
| Panel | Query |
|-------|-------|
| RAG Queries Total | `rag_queries_total` |
| RAG Query Rate | `rate(rag_queries_total[1m])` |
| Documents Indexed | `rag_documents_indexed_total` |
| RAG Success Rate | `sum(rag_queries_total{status="success"}) / sum(rag_queries_total) * 100` |
| RAG Latency (p50/p95/p99) | `histogram_quantile(0.95, rate(rag_query_latency_seconds_bucket[5m]))` |
| RAG Latency Heatmap | `sum(rate(rag_query_latency_seconds_bucket[1m])) by (le)` |

**Command:**
```bash
ssh -p 2222 root@192.168.50.61 "
kubectl apply -f stage2/k8s-manifests/monitoring/grafana.yaml
kubectl rollout restart deployment grafana -n monitoring
"
```

**Result:** ✅ Grafana dashboard with RAG section

---

### 9. Generate Test Workload

**Command:**
```bash
ssh -p 2222 root@192.168.50.61 '
# Upload test document
echo "Kubernetes is an open-source container orchestration platform..." > /tmp/k8s-intro.txt
curl -X POST http://localhost:8080/v1/rag/upload -F "file=@/tmp/k8s-intro.txt"

# Run queries
for i in {1..5}; do
  curl -X POST http://localhost:8080/v1/rag/query \
    -H "Content-Type: application/json" \
    -d "{\"question\": \"What is Kubernetes?\"}"
  sleep 2
done
'
```

**Metrics After Test:**
```
rag_queries_total{status="success"}: 10
rag_documents_indexed_total: 2
rag_query_latency_seconds_sum: 11.2s (avg ~1.1s/query)
```

**Result:** ✅ Metrics visible in Grafana

---

## Final Cluster State

```bash
kubectl get pods -n ai-platform
NAME                           READY   STATUS    RESTARTS   AGE
ai-gateway-5fbbbf76c6-qqbvj    1/1     Running   0          30m
rag-backend-6bd6db58c9-zxnzx   1/1     Running   0          37m
vllm-69df57bfc9-54qz6          1/1     Running   0          103m
weaviate-768f7d4f98-hsqwc      1/1     Running   0          40m

kubectl get pods -n monitoring
NAME                          READY   STATUS    RESTARTS   AGE
grafana-6566bdc97-6cxgj       1/1     Running   0          5m
prometheus-7cbbb7c845-hfc2b   1/1     Running   0          29m
```

---

## Key Learnings

### 1. Weaviate Vectorizer Setting
Set `DEFAULT_VECTORIZER_MODULE: "none"` because we generate embeddings externally (Ollama). Weaviate just stores vectors.

### 2. Simplified vs Production RAG
Stage 3 RAG backend is intentionally simplified:
- No security layer (auth handled at gateway)
- Simple chunking (500 chars) vs LangChain recursive
- No evaluator, no agents
- Focus: prove infrastructure works

### 3. Multi-Backend Pattern
RAG backend supports multiple LLM/embedding backends via config:
```python
if settings.llm_backend == "vllm":
    return _generate_vllm(prompt, context)
elif settings.llm_backend == "ollama":
    return _generate_ollama(prompt, context)
else:
    return _generate_bedrock(prompt, context)
```

### 4. Gateway as Proxy
AI Gateway proxies RAG requests rather than reimplementing:
- Keeps RAG logic in one place
- Gateway handles metrics, health tracking
- Single entry point for all AI operations

---

## Troubleshooting Reference

### Weaviate Not Ready
```bash
kubectl logs -n ai-platform deploy/weaviate
kubectl describe pod -n ai-platform -l app=weaviate
```

### RAG Query Fails
```bash
# Check RAG backend logs
kubectl logs -n ai-platform deploy/rag-backend

# Test Weaviate directly
kubectl exec -n ai-platform deploy/rag-backend -- curl -s http://weaviate:8080/v1/.well-known/ready

# Test vLLM directly
kubectl exec -n ai-platform deploy/rag-backend -- curl -s http://llm-server:8000/v1/models
```

### Embeddings Fail
```bash
# Check Ollama is reachable from cluster
kubectl exec -n ai-platform deploy/rag-backend -- curl -s http://192.168.50.61:11434/api/tags

# Verify nomic-embed-text is pulled
curl http://192.168.50.61:11434/api/tags | jq '.models[].name'
```

---

## Session End: 2026-02-01 10:46 AEDT

**Status:** Stage 3 Part 1 COMPLETE ✅

**Summary:**
- Weaviate deployed with persistent storage
- RAG backend adapted for local vLLM + Ollama embeddings
- AI Gateway extended with RAG routes
- Full observability in Prometheus + Grafana
- End-to-end RAG pipeline tested and working
