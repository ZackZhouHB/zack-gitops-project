# Stage 1 / Month 1: Application Layer (Senior AI Engineer Track)

> **Region:** ap-southeast-2 (Sydney)  
> **AWS Profile:** default (personal account)  
> **Focus:** Enterprise patterns, not entry-level tutorials

---

## Week 1: Bedrock Deep Dive (Enterprise Context)

### Fundamentals (Quick)
- [x] AWS CLI + SSO configured
- [x] Bedrock model access confirmed (Claude 3.5 Sonnet v2, Haiku)
- [x] Ollama setup - remote access from MacBook to Desktop PC (WSL2)
- [x] Unified LLM client (`llm_client.py`) - switch Bedrock/Ollama with one config

### Enterprise Bedrock Patterns

#### 1. Understanding Bedrock's Role in Enterprise AI Stack
- [ ] **What Bedrock solves:** Managed LLM inference without GPU infra management
- [ ] **When NOT to use Bedrock:** High-volume (cost), fine-tuning needs, latency-critical (<100ms)
- [ ] **Bedrock vs SageMaker endpoints:** When to choose which

#### 2. Real Enterprise Architecture Patterns

**Pattern A: Knowledge Base + RAG (Most Common)**
```
User Query → API Gateway → Lambda → Bedrock Knowledge Base → S3/OpenSearch → Bedrock LLM → Response
```
- Use case: Internal doc search, customer support, compliance Q&A
- AWS Services: Bedrock KB, OpenSearch Serverless, S3, Lambda, API Gateway

**Pattern B: Agentic Workflows**
```
User Request → Bedrock Agents → [Tool Calls: Lambda, API, DB] → Multi-step reasoning → Response
```
- Use case: Order processing, IT helpdesk automation, data analysis
- AWS Services: Bedrock Agents, Lambda, Step Functions, DynamoDB

**Pattern C: Batch Processing Pipeline**
```
S3 (docs) → Step Functions → Bedrock (summarize/extract) → S3/RDS (results)
```
- Use case: Contract analysis, report generation, data enrichment
- AWS Services: Step Functions, Bedrock batch inference, S3, EventBridge

**Pattern D: Real-time Streaming with Guardrails**
```
User → AppSync/WebSocket → Lambda → Bedrock (streaming) + Guardrails → Response chunks
```
- Use case: Chat applications with PII filtering, content moderation
- AWS Services: Bedrock Guardrails, AppSync, Lambda, CloudWatch

### Hands-On Tasks (Today)

- [ ] **Task 1:** Basic Bedrock invoke (5 min) - just verify it works
- [ ] **Task 2:** Streaming response implementation - real apps need this
- [ ] **Task 3:** Bedrock Guardrails setup - enterprise requirement (PII, toxicity)
- [ ] **Task 4:** Cost calculation script - estimate token costs for a workload
- [ ] **Task 5:** Multi-model routing - choose model based on task complexity

### Deliverable (Week 1)
Python module with:
- Bedrock client wrapper (sync + streaming)
- Guardrails integration
- Model routing logic (Haiku for simple, Sonnet for complex)
- Cost tracking decorator
- Config-based backend switching (ready for Ollama later)

---

## Week 2: LangChain + Enterprise Patterns

### Beyond Basic Chains
- [ ] LangChain Expression Language (LCEL) - modern approach
- [ ] Structured output with Pydantic models
- [ ] Retry/fallback strategies for production
- [ ] Token counting and context window management

### Enterprise Patterns
- [ ] **Conversation memory:** DynamoDB-backed (not in-memory)
- [ ] **Prompt versioning:** S3 or Parameter Store for prompt templates
- [ ] **A/B testing prompts:** Feature flags for prompt variants

### Deliverable (Week 2)
CLI chatbot with:
- Persistent memory (DynamoDB)
- Structured responses
- Fallback to cheaper model on rate limits

---

## Week 3: RAG - Production Grade (Case Study)

### 🎯 Case Study: Cloud Engineer Knowledge Base
**Your real problem:** People constantly ask you questions, answers buried in:
- LLD PDFs (SharePoint, laptops)
- ServiceNow incidents (past fixes)
- Confluence/Jira (design docs)

**See:** `case-study-cloud-engineer-rag.md` for full details

### Phase 1: Local POC (Custom RAG)
- [ ] Collect sample data:
  - [ ] 10-20 LLD PDFs from SharePoint
  - [ ] Export 100+ ServiceNow incidents (CSV)
  - [ ] Export 20-50 Confluence pages
- [ ] Build ingestion pipeline (PDF, CSV, HTML loaders)
- [ ] Chunking experiments (fixed vs semantic)
- [ ] Embed with Bedrock Titan
- [ ] Store in pgvector (Docker)
- [ ] Test with 5 real questions you've been asked

### Phase 2: Managed RAG Comparison
- [ ] Load same data into Bedrock Knowledge Base
- [ ] Compare: answer quality, citations, setup effort
- [ ] Document limitations hit with your specific data

### Advanced Topics (as needed)
- [ ] Hybrid search (keyword + vector) - important for incident IDs, error codes
- [ ] Re-ranking for better precision
- [ ] Metadata filtering (by system, by date)

### Deliverable (Week 3)
Working POC that answers your real questions with citations
- Custom RAG vs Bedrock KB comparison document
- Decision: which approach for your use case

---

## Week 4: Serverless RAG Platform (Capstone)

### Architecture
```
┌─────────────┐     ┌─────────────┐     ┌──────────────────┐
│  Streamlit  │────▶│ API Gateway │────▶│     Lambda       │
│  Frontend   │     │             │     │  (orchestrator)  │
└─────────────┘     └─────────────┘     └────────┬─────────┘
                                                 │
                    ┌────────────────────────────┼────────────────────────────┐
                    │                            │                            │
                    ▼                            ▼                            ▼
           ┌───────────────┐           ┌─────────────────┐          ┌─────────────┐
           │ Bedrock KB or │           │    Bedrock      │          │  Bedrock    │
           │ OpenSearch    │           │   Guardrails    │          │    LLM      │
           └───────────────┘           └─────────────────┘          └─────────────┘
```

### IaC Requirements
- [ ] Terraform modules for each component
- [ ] Environment separation (dev/prod)
- [ ] CI/CD pipeline (GitHub Actions)

### Deliverable (Week 4)
Complete platform:
- Upload PDF → Process → Query
- Guardrails enabled
- IaC in Terraform
- Cost monitoring dashboard

---

## Enterprise Service Combinations (Reference)

| Business Problem | AWS Services | Pattern |
|-----------------|--------------|---------|
| Internal knowledge search | Bedrock KB + Kendra + OpenSearch | RAG |
| Customer support automation | Bedrock Agents + Connect + Lex | Agentic |
| Document processing at scale | Textract + Bedrock + Step Functions | Batch |
| Code assistant | Bedrock + CodeWhisperer + Cloud9 | Dev tools |
| Content moderation | Bedrock Guardrails + Rekognition | Safety |
| Personalization | Bedrock + Personalize + DynamoDB | Recommendation |
| Data analysis chat | Bedrock Agents + Athena + QuickSight | Analytics |

---

## Today's Focus

1. **Understand** the 4 enterprise patterns above
2. **Build** Task 1-5 (Bedrock fundamentals with enterprise mindset)
3. **Document** learnings in notes

Ready to start with Task 1?
