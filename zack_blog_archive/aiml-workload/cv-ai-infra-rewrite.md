# CV Section: AI Infrastructure Focus (TO-BE Version)

> **Target Role:** AI Infrastructure Engineer / AI Platform Engineer  
> **Strategy:** Reframe existing experience + add planned project outcomes

---

## Option 1: Combined Section

```
NSW Education Standards Authority (NESA) – Senior Cloud Engineer
Sydney, NSW | 03/2024 – Present

Cloud & AI Infrastructure
• Lead AWS cloud platform governance, security, and cost optimization
• Architected data lakehouse migration (Glue, SageMaker), transitioning 
  EC2-based analytics workloads to serverless architecture

AI Platform Engineering
• Designed and deployed production RAG platform on Amazon EKS
  - Architected K8s infrastructure for AI workloads (FastAPI, vector search, LLM serving)
  - Integrated AWS Bedrock (Claude Sonnet) with Kendra for enterprise semantic search
  - Built automated document ingestion pipeline (S3 → processing → vector embeddings)
  - Implemented token usage tracking and cost optimization strategies

• Built enterprise AI chatbot infrastructure
  - Deployed OpenWebUI + Bedrock on containerized architecture with persistent storage
  - Designed VPC-isolated deployment ensuring corporate data never leaves AWS boundary
  - Created serverless LLM pipeline (Lambda → Bedrock) for automated cloud health reporting
  - Achieved cost reduction through two-stage token optimization

• Migrated ML workloads from self-managed EC2 to SageMaker managed infrastructure
```

---

## Option 2: Separate AI Infra Section (After completing your local project)

```
AI INFRASTRUCTURE EXPERIENCE

NSW Education Standards Authority (NESA) | 03/2024 – Present
AI Platform Engineer (within Senior Cloud Engineer role)

Production AI Deployments:
• RAG Platform on EKS
  - Designed Kubernetes architecture for production RAG workloads
  - Deployed FastAPI backend with AWS Bedrock integration
  - Configured Kendra for vector search, S3 pipelines for document ingestion
  - Implemented observability: token tracking, latency metrics, cost dashboards

• Enterprise LLM Infrastructure
  - Architected secure chatbot deployment (OpenWebUI + Bedrock + EFS)
  - Built serverless LLM pipelines for automated reporting (Lambda + Bedrock)
  - Designed multi-stage processing to optimize token usage and reduce costs

Personal AI Infrastructure Lab | 2024 – Present
Self-Hosted LLM Platform (Portfolio Project)

• Built multi-node Kubernetes cluster with GPU support for LLM inference
  - Configured NVIDIA device plugin and GPU resource scheduling
  - Deployed vLLM serving Llama-3-8B with production-grade configuration
  - Achieved X tokens/sec throughput on RTX 5070 Ti (comparable to AWS g5.xlarge)

• Designed hybrid AI gateway with intelligent routing
  - Built FastAPI service routing between self-hosted vLLM and AWS Bedrock
  - Implemented fallback patterns, circuit breakers, and health checks
  - Created cost optimization logic: route to self-hosted when available, Bedrock as fallback

• Deployed complete AI platform stack on Kubernetes
  - vLLM (GPU node) for LLM inference
  - Qdrant for vector database
  - Prometheus + Grafana for AI-specific observability
  - Traefik for ingress with rate limiting

• Documented cost analysis: self-hosted vs managed LLM breakeven calculations
```

---

## Option 3: Skills-First Format

```
AI INFRASTRUCTURE SKILLS

LLM Serving & Deployment
• vLLM, Ollama | Model serving, GPU optimization, throughput tuning
• AWS Bedrock | Claude, Titan Embeddings, Guardrails, cost management
• Kubernetes GPU | NVIDIA device plugin, resource scheduling, node selectors

AI Platform Architecture
• Hybrid routing | Self-hosted + managed LLM fallback patterns
• Vector databases | Qdrant, Kendra, pgvector deployment and tuning
• Observability | LLM-specific metrics (tokens/sec, latency p99, GPU utilization)

Production Experience
• Deployed RAG platform on EKS serving enterprise document Q&A
• Built serverless LLM pipelines processing cloud health data
• Designed secure AI infrastructure within VPC boundaries

Infrastructure Foundation
• Kubernetes | EKS, kubeadm, Karpenter, Helm, Argo CD
• IaC | Terraform, Ansible, CloudFormation
• AWS | 10+ years, Solutions Architect Professional certified
```

---

## Key Phrases to Use (AI Infra Language)

| Instead of... | Say... |
|---------------|--------|
| "Built RAG application" | "Architected RAG platform infrastructure" |
| "Used LangChain for memory" | "Designed stateful conversation architecture" |
| "Prompt engineering" | "Optimized LLM pipeline for cost efficiency" |
| "Vector embeddings" | "Deployed vector search infrastructure" |
| "Built chatbot" | "Deployed LLM serving infrastructure" |
| "ML model training" | (Remove or minimize) |
| "Feature engineering" | (Remove - data scientist language) |

---

## What to REMOVE from Current CV

| Remove/Minimize | Reason |
|-----------------|--------|
| "prompt engineering to achieve AWS health insight" | Sounds like app developer |
| "LangChain for conversation memory and context" | Implementation detail, app layer |
| "feature engineering, LightGBM, PyTorch" | Data scientist language |
| "Oscar Best Picture Prediction" | ML project, not infra |
| "Image Classification...DVC, MLflow" | Data scientist/MLOps, not infra |
| "React frontend" | Frontend dev, not infra |

---

## What to ADD (After Your Local Project)

```
AI Platform Engineering (Personal Lab)

• Multi-node Kubernetes cluster with GPU passthrough
  - 3-node cluster (control plane + CPU worker + GPU worker)
  - NVIDIA device plugin for GPU scheduling
  - Production-equivalent to EKS with g5 instances

• Self-hosted LLM serving with vLLM
  - Deployed Llama-3-8B on RTX 5070 Ti (16GB VRAM)
  - Configured continuous batching, GPU memory optimization
  - Benchmarked: X tokens/sec, p99 latency Xms

• Hybrid AI gateway architecture
  - Intelligent routing between vLLM (self-hosted) and Bedrock (managed)
  - Fallback patterns, circuit breakers, health checks
  - Cost optimization: calculated breakeven at X tokens/day

• AI observability stack
  - Prometheus metrics: tokens/sec, queue depth, GPU utilization
  - Grafana dashboards for LLM workload monitoring
  - Alerting on latency spikes, error rates

• Vector database deployment
  - Qdrant on Kubernetes with persistent storage
  - HNSW index tuning for search performance
  - Hybrid search (vector + keyword) configuration
```

---

## Interview Talking Points (Prepared Answers)

**Q: "Tell me about your AI infrastructure experience"**
> "At NESA, I architected and deployed a production RAG platform on EKS. This included 
> designing the Kubernetes infrastructure for AI workloads, integrating Bedrock for LLM 
> inference, and building observability for token usage and costs. I also built a personal 
> lab with a multi-node K8s cluster and GPU passthrough to gain hands-on experience with 
> self-hosted LLM serving using vLLM."

**Q: "How would you deploy LLM inference at scale?"**
> "I'd use vLLM on Kubernetes with GPU nodes. Key considerations: NVIDIA device plugin 
> for GPU scheduling, resource limits to prevent overcommit, HPA based on queue depth 
> rather than CPU, and proper node taints to isolate GPU workloads. I've implemented 
> this in my local lab with a 3-node cluster."

**Q: "When would you self-host vs use Bedrock?"**
> "It's a cost and compliance decision. Self-hosted wins above ~3-5M tokens/day, or when 
> data can't leave your VPC. Bedrock wins for variable traffic, quick experimentation, 
> or when you need the best models (Claude). I typically design hybrid architectures 
> with routing logic to use both."

**Q: "What metrics do you track for LLM workloads?"**
> "Tokens per second for throughput, p99 latency for user experience, GPU utilization 
> for capacity planning, queue depth for scaling decisions, and cost per request for 
> business reporting. I built Grafana dashboards for these in my lab project."

---

## Timeline to Complete CV

| Week | Complete | Add to CV |
|------|----------|-----------|
| Now | Reframe NESA experience | Use Option 1 above |
| Week 2 | K8s cluster + GPU | "Multi-node K8s with GPU" |
| Week 4 | vLLM deployed | "Self-hosted LLM serving" |
| Week 6 | AI Gateway | "Hybrid routing architecture" |
| Week 8 | Observability | "AI observability stack" |
| Week 10 | RAG pipeline | "End-to-end RAG platform" |
| Week 12 | Polish | Full Option 2 version |
