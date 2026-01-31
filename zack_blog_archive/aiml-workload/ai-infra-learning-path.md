# AI Infrastructure Engineer - Local-First Learning Path (Final)

> **Goal:** Transition from Senior Cloud Engineer to AI Platform/Infra Engineer  
> **Strategy:** Maximize local Desktop PC to simulate all 3 enterprise AI patterns  
> **Last Updated:** 2026-01-31

---

## Hardware Setup (Revised)

### Primary Platform: Desktop PC (Everything Runs Here)

| Component | Spec | Role |
|-----------|------|------|
| CPU | Intel i7-12700KF (12C/20T) | VM host, heavy compute |
| RAM | **64GB** | Run 3-node K8s cluster + WSL |
| Storage | **8TB SSD** | Models, data, VMs |
| GPU | **RTX 5070 Ti (16GB VRAM)** | LLM inference (≈ AWS g5.xlarge) |
| OS | Windows + VMware + WSL2 | Virtualization platform |

### Secondary: MacBook Pro M4 (Thin Client Only)

| Component | Spec | Role |
|-----------|------|------|
| RAM | 16GB | Not enough for AI workloads |
| Role | SSH, kubectl, browser | Access Desktop services |

---

## Desktop PC Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                      DESKTOP PC (Windows Host)                                │
│                      i7-12700KF / 64GB RAM / 8TB SSD / RTX 5070 Ti           │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                      VMware Workstation                                  │ │
│  │                      (Multi-Node K8s Cluster)                            │ │
│  │                                                                          │ │
│  │  ┌──────────────┐  ┌───────────────┐  ┌────────────────────────────┐   │ │
│  │  │ k8s-master   │  │ k8s-worker1   │  │ k8s-worker2 (GPU)          │   │ │
│  │  │              │  │               │  │                            │   │ │
│  │  │ Ubuntu 22.04 │  │ Ubuntu 22.04  │  │ Ubuntu 22.04               │   │ │
│  │  │ 4 vCPU       │  │ 4 vCPU        │  │ 4 vCPU                     │   │ │
│  │  │ 8GB RAM      │  │ 16GB RAM      │  │ 24GB RAM                   │   │ │
│  │  │ 100GB disk   │  │ 200GB disk    │  │ 200GB disk                 │   │ │
│  │  │              │  │               │  │ GPU: RTX 5070 Ti           │   │ │
│  │  │ Components:  │  │ Components:   │  │ (passthrough)              │   │ │
│  │  │ - API server │  │ - Qdrant      │  │                            │   │ │
│  │  │ - etcd       │  │ - Redis       │  │ Components:                │   │ │
│  │  │ - scheduler  │  │ - Prometheus  │  │ - vLLM (Llama-3-8B)        │   │ │
│  │  │ - Traefik    │  │ - Grafana     │  │ - NVIDIA device plugin     │   │ │
│  │  │              │  │ - FastAPI     │  │ - GPU workloads            │   │ │
│  │  └──────────────┘  └───────────────┘  └────────────────────────────┘   │ │
│  │         │                 │                      │                      │ │
│  │         └─────────────────┴──────────────────────┘                      │ │
│  │                      K8s Cluster Network (Calico)                       │ │
│  │                                                                          │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                               │
│  ┌─────────────────────┐                                                     │
│  │ WSL2 (Quick Dev)    │  ← Keep Ollama for fast iteration                  │
│  │ - Ollama            │                                                     │
│  │ - 8GB RAM allocated │                                                     │
│  │ - 192.168.50.61     │                                                     │
│  └─────────────────────┘                                                     │
│                                                                               │
│  Windows Host: 8GB RAM reserved for VMware management                        │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
                │
                │ SSH / kubectl / Web UI (port forward)
                ▼
┌────────────────────────┐          ┌─────────────────────┐
│ MacBook (Thin Client)  │          │ AWS (Minimal Use)   │
│                        │          │                     │
│ - VS Code Remote SSH   │          │ - Bedrock API only  │
│ - kubectl              │          │ - No GPU instances  │
│ - Browser for UIs      │          │ - Validation only   │
└────────────────────────┘          └─────────────────────┘
```

---

## Resource Allocation (64GB Total)

| Component | vCPU | RAM | Disk | Purpose |
|-----------|------|-----|------|---------|
| k8s-master | 4 | 8GB | 100GB | Control plane |
| k8s-worker1 | 4 | 16GB | 200GB | Apps, DBs, monitoring |
| k8s-worker2 (GPU) | 4 | 24GB | 200GB | vLLM, GPU workloads |
| WSL2 (Ollama) | shared | 8GB | 50GB | Quick dev/testing |
| Windows Host | shared | 8GB | - | VMware, management |
| **Total** | **12** | **64GB** | **550GB** | |

---

## What This Simulates (3 Enterprise Patterns)

| Pattern | How You Simulate It | Enterprise Equivalent |
|---------|--------------------|-----------------------|
| **1. Managed LLM** | FastAPI → Bedrock API calls | Lambda → Bedrock |
| **2. Self-hosted vLLM** | vLLM on k8s-worker2 (GPU) | vLLM on EKS g5 nodes |
| **3. Hybrid** | FastAPI routes to vLLM OR Bedrock | AI Gateway pattern |

---

## Updated Learning Path

### Phase 1: Foundation ✅ COMPLETED (Week 1)

| Task | Status | Deliverable |
|------|--------|-------------|
| Bedrock client patterns | ✅ Done | `bedrock_client.py` |
| Ollama remote access | ✅ Done | `ollama-remote-setup.md` |
| Backend switching | ✅ Done | `llm_client.py` |
| Enterprise patterns doc | ✅ Done | `local-vs-enterprise-ai-patterns.md` |

---

### Phase 2: Local K8s Cluster Setup (Week 2)

**Goal:** Build multi-node K8s cluster with GPU support

| Day | Task | Details |
|-----|------|---------|
| Day 1 | VM Setup | Create 3 Ubuntu 22.04 VMs in VMware |
| Day 1 | GPU Passthrough | Configure RTX 5070 Ti passthrough to worker2 |
| Day 2 | K8s Install | Reuse your `k8s-on-ec2-with-ansible` playbooks |
| Day 2 | CNI + GPU Plugin | Install Calico + NVIDIA device plugin |
| Day 3 | Validation | `kubectl get nodes`, verify GPU visible |

**Deliverables:**
- [ ] 3-node K8s cluster running on VMware
- [ ] GPU node with `nvidia.com/gpu: 1` allocatable
- [ ] Ansible playbooks updated for local VMs
- [ ] `k8s-local-cluster-setup.md` documentation

**Key Commands:**
```bash
# On master
kubeadm init --pod-network-cidr=10.244.0.0/16

# On workers
kubeadm join <master-ip>:6443 --token <token> --discovery-token-ca-cert-hash <hash>

# Install NVIDIA device plugin
kubectl apply -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.14.0/nvidia-device-plugin.yml

# Verify GPU
kubectl describe node k8s-worker2 | grep nvidia.com/gpu
```

---

### Phase 3: AI Workloads on K8s (Week 3-4)

**Goal:** Deploy production-like AI infrastructure

| Component | Node | K8s Resource | Purpose |
|-----------|------|--------------|---------|
| vLLM | worker2 (GPU) | Deployment + Service | LLM inference |
| Qdrant | worker1 | StatefulSet + PVC | Vector database |
| Redis | worker1 | Deployment + Service | Response caching |
| FastAPI | worker1 | Deployment + Service | AI Gateway |
| Prometheus | worker1 | Deployment | Metrics |
| Grafana | worker1 | Deployment | Dashboards |
| Traefik | master | DaemonSet | Ingress + rate limiting |

**Deliverables:**
- [ ] vLLM serving Llama-3-8B on GPU node
- [ ] Qdrant with sample embeddings
- [ ] FastAPI gateway with routing logic
- [ ] Prometheus + Grafana monitoring
- [ ] All K8s manifests in `k8s-manifests/` folder

**vLLM Deployment Example:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-llama3
  namespace: ai-platform
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vllm
  template:
    metadata:
      labels:
        app: vllm
    spec:
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        args:
        - --model=meta-llama/Meta-Llama-3-8B-Instruct
        - --gpu-memory-utilization=0.9
        resources:
          limits:
            nvidia.com/gpu: 1
            memory: "20Gi"
          requests:
            nvidia.com/gpu: 1
            memory: "16Gi"
        ports:
        - containerPort: 8000
      nodeSelector:
        kubernetes.io/hostname: k8s-worker2
      tolerations:
      - key: "nvidia.com/gpu"
        operator: "Exists"
        effect: "NoSchedule"
```

---

### Phase 4: Hybrid AI Gateway (Week 5-6)

**Goal:** Build routing logic that simulates enterprise hybrid pattern

```python
# ai_gateway.py - Routes between local vLLM, Ollama, and Bedrock
class AIGateway:
    def __init__(self):
        self.vllm_url = "http://vllm-service.ai-platform:8000"
        self.ollama_url = "http://192.168.50.61:11434"
        self.bedrock = BedrockClient()
    
    def route(self, request: Request) -> Response:
        """
        Routing logic simulating enterprise patterns:
        - Privacy-sensitive → vLLM (stays in cluster)
        - Quick dev/test → Ollama (fast, free)
        - Best quality needed → Bedrock Claude
        - Fallback on failure → Bedrock
        """
        if request.requires_privacy:
            return self._call_vllm(request)
        elif request.is_dev_mode:
            return self._call_ollama(request)
        elif request.needs_best_quality:
            return self._call_bedrock(request)
        else:
            # Cost optimization: try local first
            try:
                return self._call_vllm(request)
            except ServiceUnavailable:
                return self._call_bedrock(request)  # Fallback
```

**Deliverables:**
- [ ] FastAPI gateway with routing logic
- [ ] Health checks for all backends
- [ ] Circuit breaker pattern
- [ ] Request/response logging
- [ ] Cost tracking per backend

---

### Phase 5: Observability & Production Patterns (Week 7-8)

**Goal:** Add enterprise-grade observability

| Component | Tool | Simulates |
|-----------|------|-----------|
| Metrics | Prometheus | CloudWatch Metrics |
| Dashboards | Grafana | CloudWatch Dashboards |
| Tracing | Jaeger | X-Ray |
| Logging | Loki | CloudWatch Logs |
| Alerting | Alertmanager | CloudWatch Alarms |

**Key Metrics to Track:**
- Tokens per second (throughput)
- Request latency (p50, p95, p99)
- GPU utilization
- Queue depth
- Error rate by backend
- Cost per request (estimated)

**Deliverables:**
- [ ] Grafana dashboard for AI platform
- [ ] Alerts for high latency, errors
- [ ] Jaeger tracing integration
- [ ] `observability-setup.md` documentation

---

### Phase 6: RAG Pipeline (Week 9-10)

**Goal:** Complete RAG system on local K8s

```
┌─────────────────────────────────────────────────────────────────┐
│                    RAG Pipeline on Local K8s                     │
│                                                                  │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────────┐ │
│  │ Document │──▶│ Chunking │──▶│ Embedding│──▶│   Qdrant     │ │
│  │ Upload   │   │ (LangCh) │   │ (vLLM or │   │   (Vector    │ │
│  │ (S3/MinIO│   │          │   │  Bedrock)│   │    Store)    │ │
│  └──────────┘   └──────────┘   └──────────┘   └──────────────┘ │
│                                                      │          │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐        │          │
│  │ Response │◀──│ Generate │◀──│ Retrieve │◀───────┘          │
│  │          │   │ (vLLM/   │   │ (Qdrant) │                    │
│  │          │   │  Bedrock)│   │          │                    │
│  └──────────┘   └──────────┘   └──────────┘                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Deliverables:**
- [ ] Document ingestion pipeline
- [ ] Embedding generation (local or Bedrock Titan)
- [ ] Qdrant vector search
- [ ] RAG query endpoint
- [ ] Evaluation metrics (retrieval accuracy)

---

### Phase 7: Portfolio & Interview Prep (Week 11-12)

**Goal:** Package everything for job applications

**GitHub Repository Structure:**
```
ai-platform-local/
├── README.md                    # Architecture overview
├── docs/
│   ├── architecture.md          # Detailed design
│   ├── local-vs-enterprise.md   # How this maps to production
│   └── cost-analysis.md         # Bedrock vs self-hosted
├── ansible/
│   └── k8s-cluster/             # Cluster setup playbooks
├── k8s-manifests/
│   ├── vllm/
│   ├── qdrant/
│   ├── gateway/
│   └── monitoring/
├── src/
│   ├── gateway/                 # FastAPI AI Gateway
│   ├── rag/                     # RAG pipeline
│   └── clients/                 # LLM clients
├── terraform/                   # AWS deployment (design only)
│   ├── eks-gpu/
│   └── bedrock/
└── dashboards/
    └── grafana/                 # Dashboard JSON exports
```

**Interview Talking Points:**
1. "I built a multi-node K8s cluster with GPU passthrough to simulate EKS"
2. "Here's my hybrid routing logic - local vLLM for privacy, Bedrock for quality"
3. "This is the cost breakeven: X tokens/day = self-host, below that = Bedrock"
4. "My observability setup tracks tokens/sec, latency p99, GPU utilization"
5. "The K8s manifests are production-ready - just change node selectors for EKS"

---

## Timeline Summary

| Week | Phase | Focus | Deliverable |
|------|-------|-------|-------------|
| 1 | ✅ Done | Bedrock + Ollama basics | Scripts, docs |
| 2 | Cluster Setup | VMware + K8s + GPU | 3-node cluster |
| 3-4 | AI Workloads | vLLM, Qdrant, Gateway | K8s manifests |
| 5-6 | Hybrid Gateway | Routing logic | FastAPI gateway |
| 7-8 | Observability | Prometheus, Grafana | Dashboards |
| 9-10 | RAG Pipeline | End-to-end RAG | Working demo |
| 11-12 | Portfolio | Documentation | GitHub repo |

---

## Cost Summary

| Resource | Cost | Notes |
|----------|------|-------|
| Desktop PC | $0 | Already owned |
| VMware Workstation | $0 or ~$200 | May have license, or use free Player |
| Bedrock API | ~$5-10/month | Light usage for testing |
| AWS EKS | $0 | Not needed - local simulation |
| **Total** | **~$5-10/month** | 95% free |

---

## Files to Create

| File | Location | Purpose |
|------|----------|---------|
| `k8s-local-cluster-setup.md` | stage2/ | VMware + K8s setup guide |
| `vllm-deployment.yaml` | k8s-manifests/ | vLLM on GPU node |
| `ai-gateway/` | src/ | FastAPI routing service |
| `docker-compose.dev.yml` | root | Quick local dev stack |
| `grafana-dashboard.json` | dashboards/ | AI platform metrics |

---

## Next Steps

1. **Immediate:** Set up VMware VMs and K8s cluster (Phase 2)
2. **This week:** Deploy vLLM on GPU node
3. **Next week:** Build AI Gateway with routing logic

Ready to start with the VMware + K8s cluster setup?
