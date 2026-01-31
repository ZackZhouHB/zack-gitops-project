# Local Learning Setup vs Enterprise AI Patterns

> **Date:** 2026-01-31  
> **Purpose:** Understand how local practice maps to real corporate AI infrastructure  
> **Context:** Comparing `bedrock_client.py`, `llm_client.py`, and Ollama setup to production patterns

---

## Part 1: Your Scripts vs Real Corporate Patterns

### bedrock_client.py - What Transfers to Production

| Your Code | Production Equivalent | Transfer % |
|-----------|----------------------|------------|
| `RateLimiter` class (token bucket) | API Gateway Usage Plans, Kong rate limiting | **95%** - Same algorithm |
| `invoke_with_retry()` (exponential backoff) | Lambda/ECS code, AWS SDK built-in retry | **95%** - Industry standard |
| `Usage` dataclass (token tracking) | CloudWatch Custom Metrics, cost allocation tags | **90%** - Same data, different storage |
| `smart_route()` (Haiku vs Sonnet) | Feature flags, ML classifier for routing | **70%** - Concept same, implementation differs |
| `invoke_stream()` (streaming) | Same pattern in Lambda/ECS | **95%** - Identical |
| `GUARDRAIL_ID` config | Bedrock Guardrails (same service) | **100%** - Identical |
| `estimate_workload_cost()` | FinOps dashboards, AWS Cost Explorer | **80%** - Same math, better visualization |

**What's missing from bedrock_client.py for production:**
- Observability (X-Ray tracing, structured logging)
- Secrets management (Secrets Manager, not hardcoded)
- Multi-tenant isolation (separate configs per customer)
- Circuit breaker pattern (stop calling failing service)

---

### llm_client.py - What Transfers to Production

| Your Code | Production Equivalent | Transfer % |
|-----------|----------------------|------------|
| `Backend` enum (OLLAMA, BEDROCK) | Feature flags (LaunchDarkly, AWS AppConfig) | **70%** - Same concept |
| `LLMClient` abstraction | Internal AI SDK / AI Gateway service | **85%** - This is exactly what corps build |
| Environment variable switching | Config maps, SSM Parameter Store | **60%** - Prod uses more sophisticated config |
| `health_check()` method | K8s liveness/readiness probes, ALB health checks | **80%** - Same concept |
| `stream()` generator pattern | Same pattern, wrapped in WebSocket/SSE | **90%** - Identical |

**The abstraction pattern is highly valuable:**
```python
# Your code
client = LLMClient(backend="ollama")  # or "bedrock"
response = client.generate(prompt)

# Production code - same pattern
client = AIGateway(config_from_ssm)
response = client.generate(prompt)  # Routes to vLLM, Bedrock, or OpenAI based on config
```

---

### Ollama Remote Setup - What Transfers to Production

| Your Setup | Production Equivalent | Transfer % |
|------------|----------------------|------------|
| Ollama serving models | vLLM or TGI serving models | **60%** - Different software, same concept |
| WSL port forwarding | VPC networking, private endpoints | **10%** - Completely different |
| Single GPU (RTX 5070 Ti) | GPU node pools (g5, p4d instances) | **40%** - Same hardware concept, different scale |
| Manual `ollama serve` | K8s Deployment with replicas, HPA | **20%** - Manual vs orchestrated |
| `curl` to test | ALB + health checks + monitoring | **30%** - Same validation, different tooling |

**What's valuable from Ollama practice:**
- Understanding model serving APIs (OpenAI-compatible)
- GPU memory management concepts
- Inference latency expectations
- The idea of "private inference" (data stays on your network)

---

## Part 2: Architecture Comparison

### Your Local Setup (Learning)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         YOUR HOME NETWORK                                │
│                                                                          │
│  ┌──────────────┐         home WiFi          ┌───────────────────────┐  │
│  │  MacBook Pro │ ─────────────────────────▶ │  Windows PC + WSL2    │  │
│  │  M4 16GB     │    curl/python requests    │                       │  │
│  │              │                            │  ┌─────────────────┐  │  │
│  │  - VS Code   │                            │  │ Ollama          │  │  │
│  │  - Python    │                            │  │ - gpt-oss-gpu   │  │  │
│  │  - boto3     │                            │  │ - qwen3-coder   │  │  │
│  │              │                            │  │                 │  │  │
│  └──────┬───────┘                            │  │ GPU: RTX 5070Ti │  │  │
│         │                                    │  │ VRAM: 16GB      │  │  │
│         │ boto3                              │  └─────────────────┘  │  │
│         ▼                                    │                       │  │
│  ┌──────────────┐                            │  IP: 172.29.34.203    │  │
│  │ AWS Bedrock  │                            │  (WSL internal)       │  │
│  │ (Sydney)     │                            │                       │  │
│  │              │                            │  Windows forwards     │  │
│  │ - Claude 3.5 │                            │  192.168.50.61:11434  │  │
│  │ - Haiku      │                            └───────────────────────┘  │
│  │ - Guardrails │                                                       │
│  └──────────────┘                                                       │
│                                                                          │
│  CHARACTERISTICS:                                                        │
│  ├── No authentication                                                   │
│  ├── No load balancing                                                   │
│  ├── No auto-scaling                                                     │
│  ├── No observability                                                    │
│  ├── Single point of failure                                             │
│  └── Manual everything                                                   │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### Real Corporate: Managed LLM (Bedrock Only)

**When companies choose this:**
- Faster time to market
- No GPU expertise needed
- Data can leave the network (not regulated industry)
- Variable/unpredictable traffic

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              AWS ACCOUNT                                            │
│                                                                                     │
│  ┌──────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌────────────────┐  │
│  │ CloudFront│───▶│  API Gateway    │───▶│  Lambda         │───▶│  Bedrock       │  │
│  │ (CDN)     │    │                 │    │                 │    │                │  │
│  └──────────┘    │  - WAF attached │    │  - Your code    │    │  - Claude      │  │
│       ▲          │  - Throttling   │    │  - bedrock_     │    │  - Titan       │  │
│       │          │  - API keys     │    │    client.py    │    │  - Guardrails  │  │
│  ┌──────────┐    │  - Usage plans  │    │    patterns     │    │                │  │
│  │  Users   │    └─────────────────┘    └────────┬────────┘    └────────────────┘  │
│  │  (App)   │                                    │                                  │
│  └──────────┘                                    ▼                                  │
│                                          ┌─────────────────┐                        │
│       ┌──────────────────────────────────│  DynamoDB       │                        │
│       │                                  │  - Chat history │                        │
│       │                                  │  - Rate limits  │                        │
│       │                                  │  - Usage logs   │                        │
│       ▼                                  └─────────────────┘                        │
│  ┌─────────────────┐    ┌─────────────────┐                                        │
│  │  CloudWatch     │    │  X-Ray          │                                        │
│  │  - Metrics      │    │  - Traces       │                                        │
│  │  - Alarms       │    │  - Latency      │                                        │
│  │  - Dashboards   │    │  - Errors       │                                        │
│  └─────────────────┘    └─────────────────┘                                        │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘

COMPONENT RESPONSIBILITIES:

API Gateway:
├── Rate limiting      → Your RateLimiter class, but managed
├── API key validation → Who can call this API
├── Usage plans        → Free tier: 100 req/day, Pro: 10K req/day
├── WAF integration    → Block SQL injection, bad IPs
└── Throttling         → Burst: 500, Steady: 100 req/sec

Lambda:
├── Your bedrock_client.py patterns
├── Retry logic        → invoke_with_retry()
├── Cost tracking      → Log to CloudWatch Metrics
├── Smart routing      → Haiku vs Sonnet based on task
└── Guardrails call    → PII filtering before/after

Bedrock:
├── No infra to manage
├── Pay per token
├── Auto-scales infinitely
└── ~$3/1M tokens (Sonnet)
```

---

### Real Corporate: Self-Hosted vLLM on EKS

**When companies choose this:**
- Regulated industry (banking, healthcare, government)
- Data cannot leave network
- High volume (>1M tokens/day - cheaper to self-host)
- Need specific models (fine-tuned, open-source)
- Predictable traffic (can right-size GPU fleet)

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              AWS ACCOUNT - PRODUCTION VPC                               │
│                                                                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│  │                           EKS CLUSTER                                            │   │
│  │                                                                                  │   │
│  │   ┌─────────────────────────────────────────────────────────────────────────┐   │   │
│  │   │                    SYSTEM NODE GROUP (CPU)                               │   │   │
│  │   │                    m5.large x 3 (multi-AZ)                               │   │   │
│  │   │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                   │   │   │
│  │   │  │ Istio        │  │ Kong/NGINX   │  │ Karpenter    │                   │   │   │
│  │   │  │ Ingress GW   │  │ Ingress      │  │ Controller   │                   │   │   │
│  │   │  │              │  │              │  │              │                   │   │   │
│  │   │  │ - mTLS       │  │ - Rate limit │  │ - Watches    │                   │   │   │
│  │   │  │ - Routing    │  │ - Auth       │  │   pending    │                   │   │   │
│  │   │  │ - Retry      │  │ - API keys   │  │   pods       │                   │   │   │
│  │   │  └──────────────┘  └──────────────┘  │ - Provisions │                   │   │   │
│  │   │                                       │   GPU nodes  │                   │   │   │
│  │   │                                       └──────────────┘                   │   │   │
│  │   └─────────────────────────────────────────────────────────────────────────┘   │   │
│  │                                                                                  │   │
│  │   ┌─────────────────────────────────────────────────────────────────────────┐   │   │
│  │   │                    GPU NODE GROUP (Karpenter Managed)                    │   │   │
│  │   │                    g5.2xlarge (1x A10G 24GB) - scales 0 to N             │   │   │
│  │   │                                                                          │   │   │
│  │   │  ┌─────────────────────────────────────────────────────────────────┐    │   │   │
│  │   │  │                 vLLM Deployment                                  │    │   │   │
│  │   │  │                 replicas: 2-10 (HPA)                             │    │   │   │
│  │   │  │  ┌───────────┐  ┌───────────┐  ┌───────────┐                    │    │   │   │
│  │   │  │  │ vLLM Pod  │  │ vLLM Pod  │  │ vLLM Pod  │ ◀── Scale based   │    │   │   │
│  │   │  │  │           │  │           │  │           │     on queue depth │    │   │   │
│  │   │  │  │ Llama-3   │  │ Llama-3   │  │ Llama-3   │                    │    │   │   │
│  │   │  │  │ 70B       │  │ 70B       │  │ 70B       │                    │    │   │   │
│  │   │  │  │           │  │           │  │           │                    │    │   │   │
│  │   │  │  │ GPU: 1    │  │ GPU: 1    │  │ GPU: 1    │                    │    │   │   │
│  │   │  │  │ Mem: 24GB │  │ Mem: 24GB │  │ Mem: 24GB │                    │    │   │   │
│  │   │  │  └───────────┘  └───────────┘  └───────────┘                    │    │   │   │
│  │   │  │                       ▲                                          │    │   │   │
│  │   │  │                       │ OpenAI-compatible API                    │    │   │   │
│  │   │  │                       │ POST /v1/chat/completions                │    │   │   │
│  │   │  └───────────────────────┼─────────────────────────────────────────┘    │   │   │
│  │   │                          │                                               │   │   │
│  │   │  ┌───────────────────────┴─────────────────────────────────────────┐    │   │   │
│  │   │  │                 vLLM Service (ClusterIP)                         │    │   │   │
│  │   │  │                 Port: 8000                                       │    │   │   │
│  │   │  └─────────────────────────────────────────────────────────────────┘    │   │   │
│  │   └─────────────────────────────────────────────────────────────────────────┘   │   │
│  │                                                                                  │   │
│  │   ┌─────────────────────────────────────────────────────────────────────────┐   │   │
│  │   │                    APPLICATION PODS (CPU nodes)                          │   │   │
│  │   │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐                │   │   │
│  │   │  │ RAG Backend   │  │ Chat API      │  │ Batch Worker  │                │   │   │
│  │   │  │ (FastAPI)     │  │ (FastAPI)     │  │ (Celery)      │                │   │   │
│  │   │  │               │  │               │  │               │                │   │   │
│  │   │  │ - Calls vLLM  │  │ - Calls vLLM  │  │ - Calls vLLM  │                │   │   │
│  │   │  │ - Calls       │  │ - Streaming   │  │ - Bulk        │                │   │   │
│  │   │  │   Bedrock     │  │   responses   │  │   processing  │                │   │   │
│  │   │  │   (fallback)  │  │               │  │               │                │   │   │
│  │   │  └───────────────┘  └───────────────┘  └───────────────┘                │   │   │
│  │   └─────────────────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                         │
│  │ S3              │  │ OpenSearch      │  │ ElastiCache     │                         │
│  │ - Model weights │  │ - Vector store  │  │ - Response cache│                         │
│  │ - Documents     │  │ - RAG retrieval │  │ - Session store │                         │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘                         │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

### Real Corporate: Hybrid Architecture (Most Common)

**Real companies often use BOTH vLLM and Bedrock:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         HYBRID ARCHITECTURE                                  │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      AI GATEWAY (Kong/Istio)                         │   │
│  │                                                                      │   │
│  │   Routing Rules:                                                     │   │
│  │   ├── /v1/chat/internal/* ──────▶ vLLM (private data)               │   │
│  │   ├── /v1/chat/public/*   ──────▶ Bedrock (general queries)         │   │
│  │   ├── /v1/embed/*         ──────▶ vLLM (high volume, cost)          │   │
│  │   └── /v1/chat/complex/*  ──────▶ Bedrock Claude (best quality)     │   │
│  │                                                                      │   │
│  │   Features:                                                          │   │
│  │   ├── Rate limiting per user/team                                    │   │
│  │   ├── API key validation                                             │   │
│  │   ├── Request/response logging                                       │   │
│  │   ├── Retry + circuit breaker                                        │   │
│  │   └── Fallback: vLLM down? → route to Bedrock                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                          │                    │                             │
│                          ▼                    ▼                             │
│  ┌──────────────────────────────┐  ┌──────────────────────────────┐        │
│  │      vLLM on EKS             │  │      AWS Bedrock              │        │
│  │                              │  │                               │        │
│  │  Use for:                    │  │  Use for:                     │        │
│  │  ├── Sensitive data (PII)   │  │  ├── Best quality (Claude)    │        │
│  │  ├── High volume embedding  │  │  ├── Burst traffic            │        │
│  │  ├── Predictable workloads  │  │  ├── New model testing        │        │
│  │  └── Cost optimization      │  │  └── Fallback when vLLM down  │        │
│  │                              │  │                               │        │
│  │  Cost: ~$750/mo per GPU     │  │  Cost: Pay per token          │        │
│  │  (g5.xlarge 24/7)           │  │  (~$3/1M tokens Sonnet)       │        │
│  └──────────────────────────────┘  └──────────────────────────────┘        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Your llm_client.py pattern in this architecture:**

```python
# Your code (simplified)
class LLMClient:
    def generate(self, prompt):
        if self.backend == "ollama":
            return self._generate_ollama(prompt)
        else:
            return self._generate_bedrock(prompt)

# Production code - same pattern, more routing logic
class AIGateway:
    def route(self, request):
        if request.contains_pii:
            return self.vllm_client.generate(request)      # Keep private
        elif request.needs_best_quality:
            return self.bedrock_client.generate(request)   # Use Claude
        elif self.vllm_healthy:
            return self.vllm_client.generate(request)      # Cost savings
        else:
            return self.bedrock_client.generate(request)   # Fallback
```

---

## Part 3: Traditional K8s vs AI/GPU K8s

| Aspect | Traditional K8s | AI/GPU K8s |
|--------|-----------------|------------|
| **Node types** | CPU only (m5, c5) | CPU + GPU (g5, p4d, p5) |
| **Scheduling** | CPU/memory requests | GPU requests (`nvidia.com/gpu: 1`) |
| **Node cost** | ~$0.10/hr (m5.large) | ~$1.00/hr (g5.xlarge) - 10x more |
| **Scaling speed** | Fast (30 sec) | Slow (2-5 min for GPU node) |
| **Pod startup** | Fast (seconds) | Slow (model loading: 30-120 sec) |
| **Replicas** | Many (10-100) | Few (2-5, GPUs are expensive) |
| **Autoscaling metric** | CPU/memory | Queue depth, pending requests |
| **Node utilization** | Target 70% | Target 90%+ (GPUs are expensive) |

### GPU-Specific K8s Components

```yaml
# 1. NVIDIA Device Plugin (DaemonSet) - Makes GPUs visible to K8s
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: nvidia-device-plugin
  namespace: kube-system
spec:
  selector:
    matchLabels:
      name: nvidia-device-plugin
  template:
    spec:
      containers:
      - name: nvidia-device-plugin
        image: nvcr.io/nvidia/k8s-device-plugin:v0.14.0
        volumeMounts:
        - name: device-plugin
          mountPath: /var/lib/kubelet/device-plugins

---
# 2. vLLM Deployment - Request GPU resources
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-llama3
spec:
  replicas: 2
  template:
    spec:
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        args:
        - --model=meta-llama/Meta-Llama-3-8B-Instruct
        - --tensor-parallel-size=1
        - --gpu-memory-utilization=0.9
        resources:
          limits:
            nvidia.com/gpu: 1        # <-- Key difference from traditional K8s
            memory: "24Gi"
          requests:
            nvidia.com/gpu: 1
            memory: "20Gi"
        ports:
        - containerPort: 8000
      nodeSelector:
        node.kubernetes.io/instance-type: g5.2xlarge
      tolerations:
      - key: "nvidia.com/gpu"
        operator: "Exists"
        effect: "NoSchedule"

---
# 3. Karpenter NodePool for GPU nodes
apiVersion: karpenter.sh/v1beta1
kind: NodePool
metadata:
  name: gpu-nodes
spec:
  template:
    spec:
      requirements:
      - key: "node.kubernetes.io/instance-type"
        operator: In
        values: ["g5.xlarge", "g5.2xlarge", "g5.4xlarge"]
      - key: "karpenter.sh/capacity-type"
        operator: In
        values: ["spot", "on-demand"]
      taints:
      - key: "nvidia.com/gpu"
        value: "true"
        effect: "NoSchedule"
  limits:
    cpu: 100
    memory: 400Gi
    nvidia.com/gpu: 10
  disruption:
    consolidationPolicy: WhenEmpty
```

---

## Part 4: Cost Comparison

| Scenario | vLLM Self-Hosted | Bedrock | Winner |
|----------|------------------|---------|--------|
| 100K tokens/day | $750/mo (1 GPU idle) | $0.30/day = $9/mo | **Bedrock** |
| 10M tokens/day | $750/mo (1 GPU busy) | $30/day = $900/mo | **vLLM** |
| 100M tokens/day | $2,250/mo (3 GPUs) | $300/day = $9,000/mo | **vLLM** (4x cheaper) |
| Burst traffic | Over-provision or slow | Auto-scales | **Bedrock** |
| Sensitive data | Only option | N/A | **vLLM** |

**Breakeven point:** ~3-5M tokens/day, vLLM becomes cheaper than Bedrock

---

## Part 5: Summary - What's Valuable from Your Practice

### ✅ High Value (Directly Transferable)

| Your Practice | Why It's Valuable |
|---------------|-------------------|
| Bedrock API patterns | Same boto3 calls in production Lambda/ECS |
| Cost tracking (`Usage` class) | Every enterprise needs this for FinOps |
| Rate limiting concepts | Required for multi-tenant SaaS |
| Retry with backoff | Industry standard, in every production service |
| Backend abstraction (`llm_client.py`) | Exactly what corps build internally |
| Streaming responses | Required for chat UIs |

### ⚠️ Medium Value (Concept Transfers, Implementation Differs)

| Your Practice | Production Difference |
|---------------|----------------------|
| Ollama for local inference | Corps use vLLM/TGI on K8s |
| Env var for backend switching | Corps use feature flags, service mesh |
| Manual model serving | Corps use K8s orchestration |

### ❌ Low Value (Learning Only)

| Your Practice | Why It Doesn't Transfer |
|---------------|------------------------|
| WSL port forwarding | Corps use VPC, private endpoints |
| Single GPU node | Corps use auto-scaling GPU pools |
| No authentication | Corps require IAM, Cognito, API keys |
| No observability | Corps require X-Ray, CloudWatch, dashboards |

---

## Part 6: The Gap Your Existing Skills Fill

Your EKS/Terraform/Karpenter experience already covers:
- Cluster provisioning
- Node pool management
- Auto-scaling configuration
- GitOps deployment (Argo CD)
- Networking (VPC, ALB, Ingress)

**What's NEW for AI workloads:**
1. GPU resource requests (`nvidia.com/gpu: 1`)
2. NVIDIA device plugin installation
3. Model loading time considerations (affects scaling)
4. vLLM/TGI specific configurations
5. Vector database integration
6. LLM-specific metrics (tokens/sec, queue depth)

This is what Month 2 of your learning path addresses.
