# Progress & Context (For Session Recovery)

> **Purpose:** Help AI assistant catch up when disconnected or context overflows  
> **Last Updated:** 2026-01-31 23:08 AEDT

---

## Who You Are

**Name:** Zack  
**Current Role:** Senior Cloud Engineer at NSW Education Standards Authority (NESA)  
**Target Role:** AI Infrastructure Engineer / AI Platform Engineer  
**Location:** Sydney, Australia

---

## Your Background & Skills

### Strong (Existing)
- AWS (10+ years, Solutions Architect Professional)
- Kubernetes (EKS, kubeadm, Karpenter, Helm, Argo CD)
- Terraform, Ansible, CloudFormation
- Python (Boto3, automation)
- CI/CD, GitOps

### Learning (This Project)
- GPU workload scheduling on K8s
- LLM serving (vLLM, Ollama)
- Vector databases (Qdrant, pgvector)
- AI observability
- Hybrid LLM routing patterns

---

## Your Hardware

### Desktop PC (Primary - Everything Runs Here)
| Component | Spec |
|-----------|------|
| CPU | Intel i7-12700KF (12C/20T) |
| RAM | 64GB |
| GPU | **RTX 5070 Ti (16GB VRAM)** |
| Storage | 8TB SSD |
| OS | Windows 11 + WSL2 (Ubuntu 24.04) |
| IP | 192.168.50.61 |

### MacBook Pro M4 (Thin Client Only)
| Component | Spec |
|-----------|------|
| RAM | 16GB |
| Role | SSH, kubectl, browser |

---

## Current Environment Status

### WSL2
- SSH accessible: `ssh -p 2222 root@192.168.50.61`
- GPU working: `nvidia-smi` shows RTX 5070 Ti
- Docker: v28.5.1
- Ollama: Running, accessible at port 11434

### Minikube (K8s)
- Version: v1.35.0, K8s v1.32.0
- Driver: Docker
- GPU: NVIDIA device plugin installed
- Status: **Running with 1 GPU allocatable**

### AI Platform Namespace
- vLLM: Running with Qwen2.5-3B-Instruct (GPU)
- AI Gateway: Running (routes to vLLM/Ollama/Bedrock)
- PVC: model-cache (50Gi) mounted at /model-cache
- Secret: aws-credentials (for Bedrock access)
- Services: llm-server:8000, ai-gateway:8080

### Cleaned Up
- Removed: rag-backend, rag-frontend (default namespace)
- Removed: weaviate namespace

### Ollama Models Available
- qwen3-coder:latest (30.5B)
- gpt-oss-gpu:latest (20.9B)
- gpt-oss:latest (20.9B)

---

## Project Goal

Build a **local AI platform** that simulates 3 enterprise patterns:

1. **Managed LLM** - Bedrock API calls (done in Stage 1)
2. **Self-hosted LLM** - vLLM on K8s with GPU (Stage 2)
3. **Hybrid** - Routing between self-hosted and managed (Stage 2)

**Purpose:** Gain AI Infra skills + build portfolio for job applications

---

## What's Been Completed

### Stage 1 ✅
- [x] Bedrock client with production patterns (`bedrock_client.py`)
- [x] Unified LLM client for backend switching (`llm_client.py`)
- [x] Ollama remote access from MacBook
- [x] Documentation: local vs enterprise patterns
- [x] CV rewrite guidance for AI Infra focus

### Stage 2 (In Progress)
- [x] SSH access from MacBook to WSL (passwordless)
- [x] GPU validation in WSL
- [x] Minikube started with GPU support
- [x] NVIDIA device plugin confirmed working
- [x] vLLM deployment with Qwen2.5-3B-Instruct ✅
- [x] PVC for model cache (50Gi) ✅
- [x] Cleaned up old weaviate/rag deployments ✅
- [x] AI Gateway deployed ✅
- [x] Gateway routing to vLLM tested ✅
- [x] Gateway routing to Ollama tested ✅ (fixed num_predict issue)
- [x] Gateway routing to Bedrock tested ✅ (AWS creds via K8s secret)
- [x] Smart routing endpoint working ✅
- [ ] Observability (Prometheus/Grafana)
- [ ] Vector database (deferred to RAG stage)

---

## Key Files Created

### Stage 1
| File | Purpose |
|------|---------|
| `stage1/bedrock_client.py` | Enterprise Bedrock patterns |
| `stage1/llm_client.py` | Backend switching (Bedrock/Ollama) |
| `stage1/ollama-remote-setup.md` | Network setup guide |
| `stage1/local-vs-enterprise-ai-patterns.md` | Architecture comparison |
| `stage1/cv-ai-infra-rewrite.md` | CV guidance |

### Stage 2
| File | Purpose |
|------|---------|
| `stage2/README.md` | Objectives and tasks |
| `stage2/progress.md` | This file |
| `stage2/commands-log.md` | Command history |

### Root
| File | Purpose |
|------|---------|
| `ai-infra-learning-path.md` | Full 12-week plan |

---

## Network Setup

```
MacBook (192.168.50.x)
    │
    │ SSH (port 2222)
    ▼
Windows PC (192.168.50.61)
    │
    ├── WSL2 (172.29.34.203 internal)
    │   ├── Ollama (port 11434, forwarded)
    │   ├── Minikube (Docker driver)
    │   └── SSH server (port 22, forwarded to 2222)
    │
    └── Port forwards:
        ├── 2222 → WSL:22 (SSH)
        └── 11434 → WSL:11434 (Ollama)
```

---

## Commands to Verify Environment

```bash
# From MacBook - SSH to WSL
ssh -p 2222 root@192.168.50.61

# Check GPU
ssh -p 2222 root@192.168.50.61 "PATH=\$PATH:/usr/lib/wsl/lib nvidia-smi"

# Check Minikube
ssh -p 2222 root@192.168.50.61 "minikube status"

# Check K8s GPU
ssh -p 2222 root@192.168.50.61 "kubectl get node -o jsonpath='{.items[0].status.allocatable.nvidia\.com/gpu}'"

# Check Ollama
curl http://192.168.50.61:11434/api/tags
```

---

## Next Steps

1. Deploy vLLM on Minikube with GPU
2. Test inference performance
3. Deploy Qdrant vector database
4. Build AI Gateway with routing logic
5. Add observability (Prometheus/Grafana)

---

## Important Context for AI Assistant

- User prefers **Desktop PC for all workloads** (MacBook is thin client only)
- User wants to **maximize local environment** to avoid cloud GPU costs
- User's goal is **AI Infra Engineer role**, not AI/ML Engineer
- Focus on **infrastructure patterns**, not application development
- User has existing K8s/Terraform skills - leverage them
- VMware was considered but **Minikube in WSL is working** - use that instead
