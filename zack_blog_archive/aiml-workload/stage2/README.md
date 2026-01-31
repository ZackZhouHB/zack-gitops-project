# Stage 2: AI Infrastructure on Kubernetes

> **Objective:** Deploy production-like AI infrastructure on local K8s with GPU  
> **Environment:** WSL2 + Minikube + RTX 5070 Ti (16GB VRAM)  
> **Duration:** Weeks 2-8 of learning path

---

## What We're Building

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    LOCAL AI PLATFORM (Minikube on WSL2)                      │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                         Minikube Cluster                                 ││
│  │                         K8s v1.32.0 + GPU                                ││
│  │                                                                          ││
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐               ││
│  │  │    vLLM       │  │    Qdrant     │  │   FastAPI     │               ││
│  │  │  (GPU Pod)    │  │  (Vector DB)  │  │  (AI Gateway) │               ││
│  │  │               │  │               │  │               │               ││
│  │  │ Llama-3-8B    │  │ Embeddings    │  │ - Routing     │               ││
│  │  │ nvidia.com/   │  │ RAG Search    │  │ - Rate limit  │               ││
│  │  │ gpu: 1        │  │               │  │ - Fallback    │               ││
│  │  └───────────────┘  └───────────────┘  └───────────────┘               ││
│  │                                                                          ││
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐               ││
│  │  │  Prometheus   │  │   Grafana     │  │    Redis      │               ││
│  │  │  (Metrics)    │  │ (Dashboards)  │  │   (Cache)     │               ││
│  │  └───────────────┘  └───────────────┘  └───────────────┘               ││
│  │                                                                          ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
│  External Connections:                                                       │
│  ├── AWS Bedrock (Claude) - for hybrid routing / fallback                   │
│  └── Ollama (WSL) - for quick dev testing                                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Enterprise Patterns Being Simulated

| Local Component | Enterprise Equivalent | Pattern |
|-----------------|----------------------|---------|
| vLLM on Minikube | vLLM on EKS g5 nodes | Self-hosted LLM |
| Qdrant | OpenSearch / Pinecone | Vector database |
| FastAPI Gateway | API Gateway + Lambda | AI routing |
| Prometheus/Grafana | CloudWatch | Observability |
| Redis | ElastiCache | Response caching |
| Bedrock fallback | Multi-provider routing | Hybrid architecture |

---

## Tasks & Phases

### Phase 2.1: Environment Validation ✅ COMPLETED
- [x] SSH access from MacBook to WSL
- [x] GPU accessible in WSL (`nvidia-smi`)
- [x] Minikube running with GPU support
- [x] NVIDIA device plugin working (`nvidia.com/gpu: 1`)

### Phase 2.2: vLLM Deployment ✅ COMPLETED
- [x] Create ai-platform namespace
- [x] Create vLLM deployment manifest
- [x] Fix service name conflict (vllm → llm-server)
- [x] Increase probe timeouts for model loading
- [x] Model fully loaded and serving (Qwen2.5-3B-Instruct)
- [x] Test inference endpoint
- [x] Add PVC for model caching (50Gi)

### Phase 2.3: Vector Database (Deferred)
- Moved to RAG stage - not required for AI Infra core skills

### Phase 2.4: AI Gateway ✅ COMPLETED
- [x] FastAPI gateway with 3-backend routing
- [x] vLLM routing tested
- [x] Ollama routing tested (fixed num_predict issue)
- [x] Bedrock routing tested (AWS creds via K8s secret)
- [x] Smart routing endpoint (auto-selects best backend)
- [x] Fallback pattern implemented

### Phase 2.5: Observability (Next)
- [ ] Deploy Prometheus + Grafana
- [ ] Create LLM-specific metrics
- [ ] Build dashboard for AI workloads
- [ ] Set up alerting rules

### Phase 2.4: AI Gateway
- [ ] Build FastAPI routing service
- [ ] Implement backend switching (vLLM / Bedrock / Ollama)
- [ ] Add rate limiting, health checks
- [ ] Implement circuit breaker pattern

### Phase 2.5: Observability
- [ ] Deploy Prometheus + Grafana
- [ ] Create LLM-specific metrics
- [ ] Build dashboard for AI workloads
- [ ] Set up alerting rules

### Phase 2.6: RAG Pipeline
- [ ] Document ingestion pipeline
- [ ] Embedding generation
- [ ] Retrieval + generation flow
- [ ] End-to-end testing

---

## Hardware Specs

| Resource | Spec | Notes |
|----------|------|-------|
| CPU | Intel i7-12700KF (12C/20T) | 20 cores visible in K8s |
| RAM | 64GB | 32GB allocated to Minikube |
| GPU | RTX 5070 Ti (16GB VRAM) | ≈ AWS g5.xlarge (A10G 24GB) |
| Storage | 8TB SSD | Plenty for models |
| K8s | Minikube v1.35.0, K8s v1.32.0 | Single node with GPU |

---

## Access Methods

| Target | Command |
|--------|---------|
| WSL SSH | `ssh -p 2222 root@192.168.50.61` |
| kubectl | Via SSH: `ssh -p 2222 root@192.168.50.61 kubectl ...` |
| Ollama | `curl http://192.168.50.61:11434/api/tags` |
| Minikube services | `minikube service <name> --url` |

---

## Files in This Stage

| File | Purpose |
|------|---------|
| `README.md` | This file - objectives and tasks |
| `progress.md` | Session context and progress tracking |
| `commands-log.md` | Commands executed and troubleshooting |
| `k8s-manifests/` | Kubernetes deployment files |
| `src/` | Application code (gateway, etc.) |

---

## Success Criteria

By end of Stage 2, you will have:
1. vLLM serving real models on GPU in K8s
2. Vector database for RAG
3. AI Gateway with hybrid routing
4. Full observability stack
5. Portfolio-ready documentation

This demonstrates **AI Infrastructure Engineer** skills, not just AI application development.
