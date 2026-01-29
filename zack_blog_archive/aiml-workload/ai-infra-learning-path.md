# AI Infrastructure Engineer - 3 Month Learning Path

> **Goal:** Transition from Senior Cloud Engineer to AI Platform/Infra Engineer  
> **Strategy:** Leverage existing AWS/EKS expertise + local hardware for cost-effective learning

---

## Your Environment

| Resource | Specs | Role |
|----------|-------|------|
| **MacBook Pro M4** | 16GB RAM, Docker ready | Control plane, coding, light inference (Ollama) |
| **Desktop PC** | RTX 5070 Ti, Minikube ready | Heavy inference, GPU workloads, K8s simulation |
| **AWS Account** | Personal, full access | Production deployment, portfolio projects |

---

## Month 1: Application Layer (Weeks 1-4)

**Theme:** Understand how GenAI apps work before building infra for them

### Week 1: Bedrock & SDK Basics

**On MacBook:**
- [ ] Configure AWS CLI with your account
- [ ] Request Bedrock model access (Claude 3.5 Sonnet, Titan Embeddings)
- [ ] Write Python script calling Bedrock via `boto3`
- [ ] Install Ollama, pull `llama3:8b` for local testing

**Deliverable:** Python script that can switch between Bedrock and local Ollama with one config change

### Week 2: LangChain Core Concepts

**On MacBook:**
- [ ] Learn `Chain`, `PromptTemplate`, `Memory` concepts
- [ ] Build CLI chatbot with conversation history
- [ ] Test against local Ollama (free) before Bedrock (paid)

**Deliverable:** Working chatbot that remembers context

### Week 3: RAG Fundamentals (Chunking & Embedding)

**On MacBook:**
- [ ] Learn text splitting strategies (by paragraph, by tokens, semantic)
- [ ] Process a PDF: chunk → embed → inspect vectors
- [ ] Use Titan Embeddings (Bedrock) or local `nomic-embed-text` (Ollama)

**Deliverable:** Python notebook showing chunking + embedding pipeline

### Week 4: Serverless RAG (Month 1 Capstone)

**On MacBook + AWS:**
- [ ] Deploy: S3 → Lambda → Bedrock → pgvector (RDS) or OpenSearch
- [ ] Build Streamlit frontend
- [ ] Use Terraform/CDK for all infrastructure

**Deliverable:** Working doc Q&A app - upload PDF, ask questions, get answers

---

## Month 2: Infrastructure Layer (Weeks 5-8)

**Theme:** Your differentiator - deploy AI at scale, not just call APIs

### Week 5: Vector Database Engineering

**On MacBook (Docker):**
- [ ] Run pgvector locally: `docker run -e POSTGRES_PASSWORD=pass -p 5432:5432 pgvector/pgvector`
- [ ] Run Qdrant locally: `docker run -p 6333:6333 qdrant/qdrant`
- [ ] Learn indexing: HNSW parameters, distance metrics (cosine vs L2)
- [ ] Implement hybrid search (keyword + vector)

**On AWS (brief):**
- [ ] Deploy OpenSearch Serverless with Terraform
- [ ] Configure IAM, test from Lambda
- [ ] **Delete after testing** (expensive idle cost)

**Deliverable:** IaC code for vector DB + comparison notes (pgvector vs Qdrant vs OpenSearch)

### Week 6: Local Model Serving

**On Desktop PC:**
- [ ] Verify GPU access: `nvidia-smi` in Minikube node or Docker
- [ ] Run Ollama with GPU: serve Llama 3 8B, measure tokens/sec
- [ ] Run vLLM container: `docker run --gpus all vllm/vllm-openai --model meta-llama/Llama-3-8B`
- [ ] Compare: Ollama (easy) vs vLLM (production-grade, faster)

**On MacBook:**
- [ ] Run same models on M4 (CPU/Metal), compare performance
- [ ] Understand when local Mac is "good enough" vs need GPU

**Deliverable:** Benchmark doc comparing inference options

### Week 7: AI on Kubernetes

**On Desktop PC (Minikube):**
- [ ] Enable GPU addon: `minikube start --driver=docker --gpus=all`
- [ ] Install NVIDIA device plugin
- [ ] Deploy vLLM as K8s Deployment + Service
- [ ] Configure resource limits (GPU, memory)
- [ ] Set up HPA based on custom metrics (optional)

**Deliverable:** K8s manifests for GPU inference workload

### Week 8: Private AI Platform (Month 2 Capstone)

**On Desktop PC + MacBook:**
- [ ] Full stack on Minikube:
  - vLLM serving Llama 3
  - Qdrant for vectors
  - FastAPI backend
  - Simple frontend
- [ ] All traffic stays local (simulate "air-gapped" enterprise)

**On AWS (validation only):**
- [ ] Port the same setup to EKS with GPU nodes (g5.xlarge)
- [ ] Run for 1-2 days max, then tear down

**Deliverable:** Complete private RAG platform running on local K8s

---

## Month 3: Operations & Career Prep (Weeks 9-12)

**Theme:** Production readiness + interview preparation

### Week 9: LLMOps - Tracing & Evaluation

**On MacBook:**
- [ ] Integrate LangSmith for tracing (free tier)
- [ ] See full chain: prompt → LLM → tool calls → response
- [ ] Learn Ragas for automated RAG evaluation
- [ ] Build eval dataset, measure retrieval accuracy

**Deliverable:** Dashboard showing RAG pipeline performance metrics

### Week 10: Cost & Security

**On MacBook + AWS:**
- [ ] Calculate token costs: Bedrock vs self-hosted breakeven
- [ ] Implement caching layer (Redis) for repeated queries
- [ ] Configure Bedrock Guardrails (PII filtering, topic blocking)
- [ ] Design VPC architecture: no public endpoints for AI services

**Deliverable:** Cost analysis spreadsheet + secure architecture diagram

### Week 11: Portfolio Project Polish

**On AWS:**
- [ ] Deploy final "Enterprise Knowledge Base" project
- [ ] Components: EKS + OpenSearch + Bedrock + Guardrails
- [ ] Document everything in GitHub README
- [ ] Record demo video (2-3 min)

**Deliverable:** Production-grade project ready for resume

### Week 12: Resume & Interview Prep

- [ ] Rewrite resume with AI Infra focus
- [ ] Prepare system design answers:
  - "Design a RAG system for 10K concurrent users"
  - "How would you reduce LLM inference costs by 50%?"
- [ ] Practice explaining your capstone project architecture

**Deliverable:** Updated resume + interview talking points

---

## Quick Reference: When to Use What

| Task | Use This | Why |
|------|----------|-----|
| Prompt iteration | MacBook + Ollama | Fast, free, no network |
| Heavy inference testing | Desktop + vLLM | GPU power, realistic perf |
| K8s manifest testing | Desktop + Minikube | Full K8s with GPU |
| Vector DB learning | MacBook + Docker (pgvector) | Simple, portable |
| Production validation | AWS | Real cloud, portfolio proof |
| Cost-sensitive dev | Local first, AWS last | Save money |

---

## Cost Control Tips

1. **Bedrock:** Cheap, use freely for API calls
2. **OpenSearch Serverless:** Has minimum OCU cost (~$700/mo if left running). Use local Qdrant/pgvector for learning, only spin up for final project
3. **EKS GPU nodes:** ~$1/hr for g5.xlarge. Test locally first, use AWS only for validation
4. **SageMaker:** Skip for learning, Bedrock is simpler

---

## Next Steps

Ready to start? Let's dive into **Week 1** with specific commands and code.
