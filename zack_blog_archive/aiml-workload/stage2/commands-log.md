# Commands Log & Troubleshooting

> **Purpose:** Document all commands executed, why, and what they achieve  
> **Last Updated:** 2026-01-31 23:08 AEDT

---

## Session: 2026-01-31

### Objective
Set up SSH access from MacBook to WSL, validate GPU and Minikube for AI workloads.

---

## Phase 2.1: Environment Validation

### 1. Test SSH Connection to WSL

**Command:**
```bash
ssh -p 2222 -o ConnectTimeout=5 -o StrictHostKeyChecking=no root@192.168.50.61 "hostname && uname -a"
```

**Why:** Verify MacBook can reach WSL through Windows port forwarding.

**Result:** ✅ Success
```
zack
Linux zack 5.15.167.4-microsoft-standard-WSL2 ...
```

**Enterprise Pattern:** This simulates accessing remote servers/VMs in a corporate environment. In production, you'd SSH to bastion hosts or use AWS SSM.

---

### 2. Setup Passwordless SSH

**Command:**
```bash
ssh-copy-id -p 2222 -o StrictHostKeyChecking=no root@192.168.50.61
```

**Why:** Enable automation - scripts and tools need passwordless access.

**Result:** ✅ Success - SSH key added to WSL authorized_keys

**Enterprise Pattern:** Production systems use SSH keys, never passwords. Often managed via AWS Secrets Manager or HashiCorp Vault.

---

### 3. Check GPU Access in WSL

**Command:**
```bash
ssh -p 2222 root@192.168.50.61 "nvidia-smi"
```

**Initial Result:** ❌ `command not found`

**Troubleshooting:**
```bash
# Check if GPU device exists
ls /dev/dxg  # ✅ Exists

# Check WSL GPU libraries
ls /usr/lib/wsl/lib/  # ✅ libcuda.so exists

# nvidia-smi is in WSL lib path, not standard PATH
export PATH=$PATH:/usr/lib/wsl/lib
nvidia-smi  # ✅ Works
```

**Fixed Command:**
```bash
ssh -p 2222 root@192.168.50.61 "PATH=\$PATH:/usr/lib/wsl/lib nvidia-smi"
```

**Result:** ✅ Success
```
NVIDIA GeForce RTX 5070 Ti
16303MiB VRAM
CUDA Version: 13.1
```

**Enterprise Pattern:** GPU access in containers/VMs requires proper driver setup. In EKS, this is handled by the EKS-optimized AMI with NVIDIA drivers pre-installed.

---

### 4. Check Docker and Minikube Installation

**Command:**
```bash
ssh -p 2222 root@192.168.50.61 "docker --version && minikube version"
```

**Result:** ✅ Success
```
Docker version 28.5.1
minikube version: v1.35.0
```

**Enterprise Pattern:** Container runtime is the foundation. Production uses containerd (EKS default) or Docker.

---

### 5. Start Minikube with GPU Support

**Command (first attempt):**
```bash
ssh -p 2222 root@192.168.50.61 "minikube start --driver=docker --gpus=all"
```

**Result:** ❌ Failed - "docker driver should not be used with root privileges"

**Fixed Command:**
```bash
ssh -p 2222 root@192.168.50.61 "minikube start --driver=docker --gpus=all --force"
```

**Result:** ✅ Success
```
Starting "minikube" primary control-plane node
Using image nvcr.io/nvidia/k8s-device-plugin:v0.17.0
Enabled addons: nvidia-device-plugin
Done! kubectl is now configured to use "minikube" cluster
```

**Enterprise Pattern:** In production, you'd use EKS with managed node groups or Karpenter for GPU nodes. The `--gpus=all` flag is equivalent to configuring GPU instance types in EKS.

---

### 6. Verify GPU Visible in Kubernetes

**Command:**
```bash
ssh -p 2222 root@192.168.50.61 "kubectl get node minikube -o jsonpath='{.status.allocatable}'"
```

**Initial Result:** `nvidia.com/gpu: 0` ❌

**Troubleshooting:**
```bash
# Check NVIDIA device plugin pod
kubectl get pods -n kube-system | grep nvidia
# nvidia-device-plugin-daemonset-s7f4z   1/1     Running

# Check plugin logs
kubectl logs -n kube-system nvidia-device-plugin-daemonset-s7f4z
# "Registered device plugin for 'nvidia.com/gpu' with Kubelet"
```

**Result after plugin restart:** ✅ `nvidia.com/gpu: 1`

**Enterprise Pattern:** The NVIDIA device plugin is a DaemonSet that runs on every GPU node. It:
1. Discovers GPUs on the node
2. Reports them to kubelet as allocatable resources
3. Handles GPU assignment to pods

In EKS, you install this via Helm or include it in your node bootstrap.

---

## Environment Summary

| Component | Status | Command to Verify |
|-----------|--------|-------------------|
| SSH Access | ✅ | `ssh -p 2222 root@192.168.50.61 "echo ok"` |
| GPU in WSL | ✅ | `ssh ... "PATH=\$PATH:/usr/lib/wsl/lib nvidia-smi"` |
| Docker | ✅ | `ssh ... "docker --version"` |
| Minikube | ✅ | `ssh ... "minikube status"` |
| K8s GPU | ✅ | `ssh ... "kubectl get node -o jsonpath='{.items[0].status.allocatable.nvidia\.com/gpu}'"` |

---

## How This Maps to Enterprise

| Local Setup | Enterprise Equivalent |
|-------------|----------------------|
| WSL2 | EC2 instance / EKS node |
| Minikube | EKS cluster |
| Docker driver | containerd runtime |
| `--gpus=all` | g5/p4d instance types |
| NVIDIA device plugin | Same (installed via Helm) |
| Port forwarding (2222) | VPC networking / bastion |
| `nvidia.com/gpu: 1` | Same resource request |

---

## Next Commands (Phase 2.2: vLLM Deployment)

```bash
# Create namespace
kubectl create namespace ai-platform

# Deploy vLLM (will create manifest first)
kubectl apply -f k8s-manifests/vllm-deployment.yaml

# Check pod status
kubectl get pods -n ai-platform -w

# Check GPU allocation
kubectl describe pod -n ai-platform <vllm-pod>

# Test inference
kubectl exec -n ai-platform <vllm-pod> -- curl localhost:8000/v1/models
```

---

## Troubleshooting Reference

### SSH Connection Refused
```bash
# Check Windows port forwarding
netsh interface portproxy show all

# Check WSL SSH service
wsl -d Ubuntu -u root service ssh status
```

### GPU Not Visible in K8s
```bash
# Restart device plugin
kubectl rollout restart daemonset nvidia-device-plugin-daemonset -n kube-system

# Check plugin logs
kubectl logs -n kube-system -l app.kubernetes.io/component=nvidia-device-plugin
```

### Minikube Won't Start
```bash
# Delete and recreate
minikube delete
minikube start --driver=docker --gpus=all --force

# Check Docker is running
docker ps
```


---

## Phase 2.2: vLLM Deployment

### 1. Check Available GPU Memory

**Command:**
```bash
ssh -p 2222 root@192.168.50.61 "PATH=\$PATH:/usr/lib/wsl/lib nvidia-smi --query-gpu=memory.free --format=csv,noheader"
```

**Result:** 14428 MiB free (~14GB)

**Decision:** Use Qwen2.5-3B-Instruct (small model, ~6GB) for initial testing. Can upgrade to larger models later.

---

### 2. Create Namespace

**Command:**
```bash
kubectl create namespace ai-platform
```

**Result:** ✅ namespace/ai-platform created

**Enterprise Pattern:** Namespaces isolate workloads. In production, you'd have `ai-platform-dev`, `ai-platform-prod`, etc.

---

### 3. Deploy vLLM

**Manifest:** `k8s-manifests/vllm-deployment.yaml`

**Key Configuration:**
```yaml
resources:
  limits:
    nvidia.com/gpu: 1    # Request 1 GPU
    memory: "16Gi"
  requests:
    nvidia.com/gpu: 1
    memory: "12Gi"

args:
- --model=Qwen/Qwen2.5-3B-Instruct  # Small model for testing
- --gpu-memory-utilization=0.85     # Use 85% of GPU memory
- --max-model-len=4096              # Context window
- --dtype=half                      # FP16 for memory efficiency
```

**Command:**
```bash
kubectl apply -f k8s-manifests/vllm-deployment.yaml
```

**Result:** ✅ deployment.apps/vllm created, service/vllm created

**Enterprise Pattern:** 
- GPU resource requests ensure pod lands on GPU node
- Memory limits prevent OOM
- Readiness/liveness probes ensure traffic only goes to healthy pods
- Service provides stable internal DNS name

---

### 4. Monitor Deployment

**Command:**
```bash
kubectl get pods -n ai-platform -w
```

**Status:** ContainerCreating (pulling vllm/vllm-openai:latest ~8GB image)

**Note:** First pull takes several minutes. Subsequent deployments will be faster due to image caching.


---

### 5. Troubleshooting: Service Name Conflict

**Issue:** Pod crash-looping with error:
```
ValueError: VLLM_PORT 'tcp://10.110.26.171:8000' appears to be a URI. 
This may be caused by a Kubernetes service discovery issue
```

**Root Cause:** K8s auto-injects environment variables for services. A service named `vllm` creates `VLLM_PORT=tcp://...` which conflicts with vLLM's internal env var.

**Fix:** Rename service from `vllm` to `llm-server`

**Command:**
```bash
kubectl delete deployment vllm -n ai-platform
kubectl delete service vllm -n ai-platform
# Update manifest: service name vllm → llm-server
kubectl apply -f k8s-manifests/vllm-deployment.yaml
```

**Result:** ✅ Pod now starting correctly

**Enterprise Pattern:** This is a real production gotcha. Service names should avoid conflicts with application env vars. Common practice: prefix service names (e.g., `svc-vllm`, `llm-server`).

---

### 6. Model Loading

**Status:** vLLM is downloading Qwen/Qwen2.5-3B-Instruct from HuggingFace (~6GB)

**First-time behavior:**
- Downloads model weights to container
- Takes 3-5 minutes depending on network
- Subsequent restarts use cached weights (if PVC configured)

**Logs showing progress:**
```
INFO Starting to load model Qwen/Qwen2.5-3B-Instruct...
INFO Using FLASH_ATTN attention backend
```

**Enterprise Pattern:** In production, you'd:
1. Pre-pull models to a shared PVC or S3
2. Use init containers to download before main container starts
3. Or bake models into custom container images


---

### 7. Model Download Issue (In Progress)

**Problem:** Model downloads from HuggingFace on every pod restart (~6GB, takes 5-10 min)

**Root Cause:** No persistent volume for model cache. Each new pod starts fresh.

**Current Status:**
- Pod is Running (1/1)
- Model downloading from HuggingFace
- Takes ~10 minutes for first startup

**Solutions for Production:**
1. Add PersistentVolumeClaim for `/root/.cache/huggingface`
2. Pre-download model to a shared volume
3. Bake model into custom container image
4. Use init container to download before main container

**Next Session:**
- Wait for model to fully load
- Test inference via kubectl port-forward
- Add PVC for model caching
- Benchmark performance

---

## Session End: 2026-01-31 23:17 AEDT

**Status:** vLLM pod running, model downloading. Need to wait ~10 min for full startup.

**To Resume:**
```bash
# Check if vLLM is ready
ssh -p 2222 root@192.168.50.61 "kubectl get pods -n ai-platform"
ssh -p 2222 root@192.168.50.61 "kubectl logs -n ai-platform -l app=vllm 2>&1 | grep -E 'Uvicorn|Application startup'"

# Test inference
ssh -p 2222 root@192.168.50.61 "kubectl port-forward -n ai-platform svc/llm-server 8000:8000 &"
curl http://localhost:8000/v1/models
```


---

### 8. vLLM Successfully Running! ✅

**Time:** 2026-02-01 00:22 AEDT

**Final Status:**
```
NAME                    READY   STATUS    RESTARTS   AGE
vllm-76569d955c-kx9kx   1/1     Running   0          ~15m
```

**Test Results:**
```bash
# Models endpoint
curl localhost:8000/v1/models
# Returns: Qwen/Qwen2.5-3B-Instruct

# Chat completion
curl -X POST localhost:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model": "Qwen/Qwen2.5-3B-Instruct", "messages": [{"role": "user", "content": "What is Kubernetes?"}]}'
# Returns: "Kubernetes is an open-source system for automating deployment, scaling, and management of containerized applications."
```

**Startup Timeline:**
- Model download: ~10 min (5.8GB from HuggingFace)
- torch.compile: ~45 sec
- CUDA graph capture: ~3 sec
- Total cold start: ~12-15 min

**Enterprise Pattern:** This long cold start is why production systems:
1. Use persistent storage for model cache
2. Pre-warm pods before adding to load balancer
3. Use init containers for model download
4. Keep minimum replicas always running

---

### 9. Added Persistent Volume for Model Cache

**Created:** `model-cache-pvc.yaml`
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: model-cache
  namespace: ai-platform
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 50Gi
```

**Updated deployment** to mount PVC at `/model-cache` with `HF_HOME=/model-cache`

**Result:** Next pod restart will use cached model, reducing startup from ~15 min to ~2 min

**Enterprise Pattern:** In production:
- Use EFS for shared model storage across nodes
- Or S3 with s3fs-fuse for cost-effective storage
- Or bake models into custom container images


---

## Phase 2.4: AI Gateway

### 10. AI Gateway Deployment

**Created files:**
- `src/gateway/main.py` - FastAPI routing service
- `src/gateway/Dockerfile` - Container image
- `src/gateway/requirements.txt` - Dependencies
- `k8s-manifests/ai-gateway.yaml` - K8s deployment

**Features:**
- Routes to 3 backends: vLLM (K8s), Ollama (WSL), Bedrock (AWS)
- `/v1/chat/completions` - Explicit backend selection
- `/v1/chat/smart` - Auto-routing (tries vLLM → Ollama → Bedrock)
- `/health` - Health check with backend status
- Fallback logic when primary backend fails

**Build & Deploy:**
```bash
# Build image
cd /tmp/gateway
docker build -t ai-gateway:v3 .

# Load into Minikube
minikube image load ai-gateway:v3

# Deploy
kubectl apply -f k8s-manifests/ai-gateway.yaml
```

---

### 11. Troubleshooting: Ollama Empty Response

**Issue:** Ollama returning empty content through gateway

**Debug steps:**
```bash
# Direct curl works
curl http://192.168.50.61:11434/api/generate -d '{"model":"gpt-oss-gpu:latest","prompt":"Hello","stream":false}'
# Returns content ✓

# With num_predict option - EMPTY
curl ... -d '{"options":{"num_predict":50}}'
# Returns empty response
```

**Root cause:** The `num_predict` option conflicts with this specific model (gpt-oss-gpu)

**Fix:** Removed `options` from Ollama API call in gateway code

---

### 12. AWS Credentials for Bedrock

**Created K8s secret:**
```bash
kubectl create secret generic aws-credentials -n ai-platform \
  --from-literal=AWS_ACCESS_KEY_ID=xxx \
  --from-literal=AWS_SECRET_ACCESS_KEY=xxx \
  --from-literal=AWS_DEFAULT_REGION=ap-southeast-2
```

**Updated deployment to use secret:**
```yaml
env:
- name: AWS_ACCESS_KEY_ID
  valueFrom:
    secretKeyRef:
      name: aws-credentials
      key: AWS_ACCESS_KEY_ID
```

**Enterprise Pattern:** In production, use:
- IAM Roles for Service Accounts (IRSA) on EKS
- Or AWS Secrets Manager with external-secrets operator
- Never hardcode credentials in manifests

---

### 13. Final Test Results

| Backend | Endpoint | Latency | Status |
|---------|----------|---------|--------|
| vLLM | `/v1/chat/completions?backend=vllm` | ~1s (warm) | ✅ |
| Ollama | `/v1/chat/completions?backend=ollama` | ~8s | ✅ |
| Bedrock | `/v1/chat/completions?backend=bedrock` | ~0.5s | ✅ |
| Smart | `/v1/chat/smart` | varies | ✅ |

**Test commands:**
```bash
# Test vLLM
kubectl exec -n ai-platform deploy/ai-gateway -- python -c "
import httpx
resp = httpx.post('http://localhost:8080/v1/chat/completions', json={
    'messages': [{'role': 'user', 'content': 'What is K8s?'}],
    'backend': 'vllm'
}, timeout=60)
print(resp.json())
"

# Test smart routing (auto-selects best backend)
kubectl exec -n ai-platform deploy/ai-gateway -- python -c "
import httpx
resp = httpx.post('http://localhost:8080/v1/chat/smart', json={
    'messages': [{'role': 'user', 'content': 'What is Terraform?'}]
}, timeout=60)
print(resp.json())
"
```

---

## Current Cluster State

```
ai-platform namespace:
├── Deployments
│   ├── vllm (1 replica, GPU)
│   └── ai-gateway (1 replica)
├── Services
│   ├── llm-server:8000 (vLLM)
│   └── ai-gateway:8080 (Gateway)
├── PVC
│   └── model-cache (50Gi)
└── Secrets
    └── aws-credentials

default namespace:
└── kubernetes service only (clean)
```

---

## Session End: 2026-02-01 00:49 AEDT

**Completed:**
- vLLM on K8s with GPU ✅
- AI Gateway with 3-backend routing ✅
- Smart routing with fallback ✅
- AWS credentials configured ✅

**Next:**
- Observability (Prometheus/Grafana)
- Or call it a night
