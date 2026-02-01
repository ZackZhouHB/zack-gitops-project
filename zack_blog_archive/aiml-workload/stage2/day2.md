# Day 2 - Stage 2 Progress

> **Date:** 2026-02-01 (Sunday)  
> **Session Start:** 09:00 AEDT  
> **Focus:** Environment recovery, gateway design review, observability planning

---

## Morning: Environment Recovery

### Issue: Minikube Was Stopped
After overnight, minikube was in stopped state. Recovery steps:

```bash
# Start minikube with GPU
minikube start --driver=docker --gpus=all --force

# NVIDIA device plugin needed restart to register GPU
kubectl rollout restart daemonset nvidia-device-plugin-daemonset -n kube-system

# Result: 1 GPU allocatable
```

### Issue: vLLM DNS Resolution Failure
New vLLM pod couldn't reach HuggingFace (DNS issue after minikube restart).

**Solution:** Restart CoreDNS + recreate vLLM pod
```bash
kubectl rollout restart deployment coredns -n kube-system
kubectl delete pod -n ai-platform <vllm-pod> --force
```

**Good news:** Model loaded from PVC cache in ~1.8 seconds (vs 10+ min download)

### Final Startup Timeline
- Model weights: 1.8s (from cache)
- torch.compile: 42s
- CUDA graph capture: 2.5s
- Total cold start: ~3.5 min

### Verified Working
```
ai-platform namespace:
├── vllm-69df57bfc9-54qz6      1/1 Running (Qwen2.5-3B-Instruct)
├── ai-gateway-76f9789bc4-89sfn 1/1 Running
├── llm-server:8000            (vLLM service)
├── ai-gateway:8080            (gateway service)
├── model-cache PVC            50Gi Bound
└── aws-credentials secret     (for Bedrock)
```

---

## AI Gateway Design Explanation

Zack asked: "Explain the design logic for the API gateway - the 3 ways to route, how they work, and how they compare to enterprise patterns."

### The 3 Backend Paths

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        AI GATEWAY (FastAPI in K8s)                          │
│                                                                             │
│   POST /v1/chat/completions?backend=vllm|ollama|bedrock                    │
│   POST /v1/chat/smart  (auto-selects best available)                       │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                     ROUTING LOGIC                                    │  │
│   │                                                                      │  │
│   │   backend == "vllm":                                                │  │
│   │       → HTTP to http://llm-server:8000 (K8s internal DNS)           │  │
│   │       → OpenAI-compatible API                                       │  │
│   │       → Runs on YOUR GPU, FREE                                      │  │
│   │                                                                      │  │
│   │   backend == "ollama":                                              │  │
│   │       → HTTP to http://192.168.50.61:11434 (WSL host IP)            │  │
│   │       → Ollama native API                                           │  │
│   │       → Runs on YOUR GPU, FREE                                      │  │
│   │                                                                      │  │
│   │   backend == "bedrock":                                             │  │
│   │       → boto3 AWS SDK call                                          │  │
│   │       → Claude/Anthropic API format                                 │  │
│   │       → COSTS MONEY per token                                       │  │
│   │                                                                      │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│   FALLBACK: vLLM fails → automatically try Bedrock                         │
│   SMART:    Try vLLM → Ollama → Bedrock (cost priority)                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Code Logic Summary

**1. vLLM (K8s internal):**
```python
# Uses K8s DNS - llm-server resolves to vLLM pod
response = await client.post(f"{VLLM_URL}/v1/chat/completions", json={...})
```

**2. Ollama (External to K8s):**
```python
# Calls WSL host IP directly (outside K8s network)
response = await client.post(f"{OLLAMA_URL}/api/generate", json={...})
```

**3. Bedrock (AWS Cloud):**
```python
# AWS SDK call over internet
client = boto3.client("bedrock-runtime")
response = client.invoke_model(modelId=model, body=json.dumps(body))
```

### Comparison to Enterprise Patterns

| Your Gateway | Enterprise Equivalent | Match % |
|--------------|----------------------|---------|
| FastAPI routing | Kong/Istio/API Gateway | 70% |
| `backend` query param | Feature flags, path-based routing | 60% |
| `backend_health` dict | Circuit breaker (Istio) | 40% |
| Fallback to Bedrock | Multi-provider failover | 80% |
| Smart routing (cost-based) | AI Gateway routing rules | 85% |
| Latency tracking | Prometheus metrics | 50% |

### What's Achieved vs Enterprise

| Enterprise Pattern | Status |
|-------------------|--------|
| Multi-backend routing (vLLM + Ollama + Bedrock) | ✅ ACHIEVED |
| Fallback/failover | ✅ ACHIEVED |
| Cost-based routing (smart endpoint) | ✅ ACHIEVED |
| Health tracking | ⚠️ PARTIAL (simple dict) |
| Rate limiting | ❌ MISSING |
| Authentication | ❌ MISSING |
| Observability (metrics) | ❌ MISSING |
| Circuit breaker | ⚠️ PARTIAL |

---

## Production Features Analysis

Zack asked: "Which features are worth adding locally vs too complex/enterprise-only?"

### Recommendation Matrix

| Feature | Local Value | Complexity | Decision |
|---------|-------------|------------|----------|
| **Prometheus Metrics** | HIGH | LOW | ✅ DO IT |
| **Structured Logging** | HIGH | LOW | ✅ DO IT |
| Rate Limiting | LOW (single user) | LOW | ⚠️ Skip |
| Circuit Breaker | MEDIUM | MEDIUM | ⚠️ Skip (fallback is enough) |
| Auth/API Keys | ZERO (local only) | LOW | ❌ Skip |
| OpenTelemetry/Tracing | LOW | HIGH | ❌ Skip (overkill) |

### Why Skip Some Features

| Feature | Reason to Skip |
|---------|----------------|
| Rate limiting | Already built `RateLimiter` in Stage 1 `bedrock_client.py` - same concept proven |
| Circuit breaker | Current fallback logic demonstrates the pattern sufficiently |
| Auth | No value locally, trivial to add if needed |
| OpenTelemetry | Designed for distributed tracing across 20+ services - overkill for 2 services |

### Why Do Prometheus + Grafana

1. **Portfolio value** - Visual dashboards showing AI platform metrics
2. **Interview talking point** - "I built observability for LLM workloads"
3. **LLM-specific metrics** - Latency per backend, token throughput, error rates
4. **Low complexity** - ~30 lines of code + helm install

### Expected Dashboard

```
┌─────────────────────────────────────────────────────────────────┐
│                    GRAFANA DASHBOARD                            │
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ Requests/min    │  │ Avg Latency     │  │ Error Rate      │ │
│  │     ████████    │  │   vLLM: 1.2s    │  │     0.5%        │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐                      │
│  │ Backend Usage   │  │ GPU Memory      │                      │
│  │  vLLM: 70%      │  │   ████████ 85%  │                      │
│  │  Ollama: 20%    │  │                 │                      │
│  │  Bedrock: 10%   │  │                 │                      │
│  └─────────────────┘  └─────────────────┘                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Observability Implementation

### Design Decision: What to Add vs Skip

| Feature | Local Value | Complexity | Decision |
|---------|-------------|------------|----------|
| **Prometheus Metrics** | HIGH | LOW | ✅ DO IT |
| **Structured Logging** | HIGH | LOW | ✅ DO IT |
| Rate Limiting | LOW (single user) | LOW | ⚠️ Skip (proven in Stage 1) |
| Circuit Breaker | MEDIUM | MEDIUM | ⚠️ Skip (fallback is enough) |
| Auth/API Keys | ZERO (local only) | LOW | ❌ Skip |
| OpenTelemetry/Tracing | LOW | HIGH | ❌ Skip (overkill for 2 services) |

### Gateway Metrics Implementation

Added `prometheus_client` to the AI Gateway. Key metrics:

```python
from prometheus_client import Counter, Histogram, Gauge

# 1. Request counter - track success/error by backend
REQUEST_COUNT = Counter(
    'ai_gateway_requests_total', 
    'Total requests to AI Gateway',
    ['backend', 'status']  # Labels: backend=vllm|ollama|bedrock, status=success|error
)

# 2. Latency histogram - track response time distribution
REQUEST_LATENCY = Histogram(
    'ai_gateway_request_latency_seconds',
    'Request latency in seconds',
    ['backend'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0]  # LLM-appropriate buckets
)

# 3. Backend health gauge - real-time health status
BACKEND_HEALTH = Gauge(
    'ai_gateway_backend_healthy',
    'Backend health status (1=healthy, 0=unhealthy)',
    ['backend']
)

# 4. Token counter - approximate tokens generated
TOKENS_GENERATED = Counter(
    'ai_gateway_tokens_generated_total',
    'Approximate tokens generated',
    ['backend']
)
```

**Metrics endpoint:** `GET /metrics` - Prometheus scrapes this every 15s

### Why These KPIs?

| Metric | Why It Matters | Enterprise Use |
|--------|----------------|----------------|
| `requests_total` | Track usage per backend, error rates | Capacity planning, SLA monitoring |
| `request_latency_seconds` | Identify slow backends, p95/p99 latency | Performance SLOs, alerting |
| `backend_healthy` | Real-time health visibility | Auto-failover decisions, dashboards |
| `tokens_generated_total` | Cost estimation, throughput | FinOps, billing, capacity |

### Prometheus Configuration

```yaml
# prometheus.yml - scrape config
scrape_configs:
  - job_name: 'ai-gateway'
    static_configs:
      - targets: ['ai-gateway.ai-platform.svc.cluster.local:8080']
    metrics_path: /metrics
    scrape_interval: 15s
```

### Grafana Dashboard Design

Pre-configured dashboard with 7 panels:

| Panel | Type | Query | Purpose |
|-------|------|-------|---------|
| Requests/sec | Time series | `rate(ai_gateway_requests_total[1m])` | Traffic volume by backend |
| Latency p95 | Time series | `histogram_quantile(0.95, rate(..._bucket[5m]))` | Performance monitoring |
| Backend Health | Stat | `ai_gateway_backend_healthy` | At-a-glance health |
| Requests by Backend | Pie chart | `sum(...) by (backend)` | Usage distribution |
| Tokens Generated | Time series | `rate(ai_gateway_tokens_generated_total[1m])` | Throughput |
| Error Rate | Stat | `sum(rate(...{status="error"}[5m])) / sum(rate(...[5m]))` | Reliability |
| Latency Heatmap | Heatmap | `sum(rate(..._bucket[1m])) by (le)` | Latency distribution |

### Access Setup (WSL + Windows)

Since Minikube runs inside WSL, accessing Grafana from Windows requires:

1. **In WSL:** Port-forward with external binding
   ```bash
   kubectl port-forward -n monitoring svc/grafana 3000:3000 --address 0.0.0.0
   ```

2. **In Windows (PowerShell Admin):** Forward to WSL IP
   ```powershell
   netsh interface portproxy add v4tov4 listenport=3000 listenaddress=0.0.0.0 connectport=3000 connectaddress=172.29.34.203
   ```

3. **Browser:** http://localhost:3000 (admin/admin)

### Test Results

Generated traffic and observed in Grafana:

```
vLLM 1: 45ms
vLLM 2: 59ms
vLLM 3: 81ms
vLLM 4: 106ms
vLLM 5: 137ms
Bedrock 1: 354ms
Bedrock 2: 438ms
```

**Observations:**
- vLLM (local GPU): ~50-140ms latency
- Bedrock (AWS API): ~350-450ms latency
- vLLM is 3-5x faster for simple queries (no network round-trip)

---

## Architecture After Day 2

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MINIKUBE CLUSTER                                    │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    ai-platform namespace                             │   │
│  │  ┌─────────────────┐  ┌─────────────────┐                           │   │
│  │  │   AI Gateway    │  │     vLLM        │                           │   │
│  │  │   (FastAPI)     │  │   (GPU Pod)     │                           │   │
│  │  │                 │  │                 │                           │   │
│  │  │ - /v1/chat/*    │  │ Qwen2.5-3B      │                           │   │
│  │  │ - /metrics ◀────┼──│                 │                           │   │
│  │  │ - /health       │  │ RTX 5070 Ti     │                           │   │
│  │  └────────┬────────┘  └─────────────────┘                           │   │
│  │           │                                                          │   │
│  └───────────┼──────────────────────────────────────────────────────────┘   │
│              │                                                              │
│  ┌───────────┼──────────────────────────────────────────────────────────┐   │
│  │           │         monitoring namespace                              │   │
│  │           ▼                                                           │   │
│  │  ┌─────────────────┐  ┌─────────────────┐                            │   │
│  │  │   Prometheus    │  │    Grafana      │                            │   │
│  │  │                 │  │                 │                            │   │
│  │  │ Scrapes /metrics│  │ AI Gateway      │                            │   │
│  │  │ every 15s       │──│ Dashboard       │                            │   │
│  │  │                 │  │                 │                            │   │
│  │  └─────────────────┘  └─────────────────┘                            │   │
│  └───────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
   ┌───────────┐                 ┌───────────┐
   │  Ollama   │                 │  Bedrock  │
   │  (WSL)    │                 │  (AWS)    │
   └───────────┘                 └───────────┘
```

---

## Files Created/Modified

| File | Change |
|------|--------|
| `src/gateway/main.py` | Added Prometheus metrics + structured logging |
| `src/gateway/requirements.txt` | Added `prometheus-client==0.19.0` |
| `k8s-manifests/ai-gateway.yaml` | Updated to image `ai-gateway:v4` |
| `k8s-manifests/monitoring/prometheus.yaml` | New - Prometheus deployment |
| `k8s-manifests/monitoring/grafana.yaml` | New - Grafana with pre-configured dashboard |

---

## Commands Reference

```bash
# SSH to WSL
ssh -p 2222 root@192.168.50.61

# Check cluster status
kubectl get pods -n ai-platform

# Test gateway
kubectl exec -n ai-platform deploy/ai-gateway -- python -c "
import httpx
r = httpx.post('http://localhost:8080/v1/chat/completions', 
    json={'messages': [{'role': 'user', 'content': 'Hello'}], 'backend': 'vllm'},
    timeout=60)
print(r.json())
"
```


---

## Afternoon: Stage 3 RAG Integration

> **Continued from Stage 2 into Stage 3**

### RAG System Deployed

Added RAG capabilities to the AI platform:

1. **Weaviate Vector Database**
   - Deployed to `ai-platform` namespace
   - 10Gi PVC for persistent storage
   - Service: `weaviate:8080`

2. **RAG Backend**
   - Simplified from `mlops/rag-v1`
   - Uses vLLM for generation, Ollama for embeddings
   - Service: `rag-backend:8001`

3. **AI Gateway Extended**
   - Added `/v1/rag/query`, `/v1/rag/upload`, `/v1/rag/documents`
   - Proxies to RAG backend
   - Updated to `ai-gateway:v6`

4. **Grafana Dashboard Updated**
   - Added RAG-specific panels
   - Metrics: `rag_queries_total`, `rag_query_latency_seconds`, `rag_documents_indexed_total`

### Final Architecture

```
ai-platform namespace:
├── vllm (GPU)           - Qwen2.5-3B-Instruct
├── ai-gateway v6        - Multi-backend routing + RAG routes
├── weaviate             - Vector database (10Gi PVC)
├── rag-backend          - RAG API
└── Services: llm-server:8000, ai-gateway:8080, weaviate:8080, rag-backend:8001

monitoring namespace:
├── prometheus           - Scraping ai-gateway, rag-backend, vllm
└── grafana              - AI Gateway + RAG dashboard
```

### Test Results

```bash
# Upload document
curl -X POST http://localhost:8080/v1/rag/upload -F "file=@/tmp/k8s-intro.txt"
# {"status":"ok","filename":"k8s-intro.txt","chunks":1}

# Query
curl -X POST http://localhost:8080/v1/rag/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Kubernetes?"}'
# {"answer":"Kubernetes is an open-source container orchestration platform...","latency_ms":421}
```

**Metrics:**
- 10 successful RAG queries
- 2 documents indexed
- Average latency: ~1.1s per query

---

## Day 2 Summary

| Component | Status | Notes |
|-----------|--------|-------|
| vLLM (GPU) | ✅ Running | Cold start ~3.5min, warm ~50ms latency |
| AI Gateway | ✅ v6 | 3 LLM backends + RAG routes |
| Prometheus | ✅ Running | Scraping gateway, RAG, vLLM |
| Grafana | ✅ Running | AI Gateway + RAG dashboard |
| Weaviate | ✅ Running | 10Gi PVC, vector storage |
| RAG Backend | ✅ Running | vLLM + Ollama embeddings |

**Stage 2 + Stage 3 Part 1 COMPLETE** ✅
