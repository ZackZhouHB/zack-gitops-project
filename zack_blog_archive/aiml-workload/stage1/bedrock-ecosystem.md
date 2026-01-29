# AWS Bedrock: Complete Service Map

> What we've covered, what's left, and what matters for interviews vs production

---

## Bedrock Service Components Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            AWS BEDROCK ECOSYSTEM                                │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                     FOUNDATION MODELS (Core)                            │   │
│  │  • Claude (Anthropic)    • Titan (Amazon)    • Llama (Meta)            │   │
│  │  • Mistral               • Cohere            • AI21 Labs               │   │
│  │  • Stability AI (images) • Amazon Nova                                  │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────────────┐   │
│  │   KNOWLEDGE BASE  │  │     AGENTS        │  │      GUARDRAILS           │   │
│  │   (Managed RAG)   │  │  (Tool Use/Actions)│  │   (Safety/Compliance)     │   │
│  │                   │  │                   │  │                           │   │
│  │  • Auto chunking  │  │  • Multi-step     │  │  • PII filtering          │   │
│  │  • Auto embedding │  │  • Lambda tools   │  │  • Content filtering      │   │
│  │  • Vector search  │  │  • API actions    │  │  • Topic blocking         │   │
│  │  • S3/Web crawl   │  │  • Code interpret │  │  • Custom word filters    │   │
│  └───────────────────┘  └───────────────────┘  └───────────────────────────┘   │
│                                                                                 │
│  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────────────┐   │
│  │   MODEL EVAL      │  │   FINE-TUNING     │  │    PROVISIONED            │   │
│  │                   │  │   & DISTILLATION  │  │    THROUGHPUT             │   │
│  │  • Auto eval      │  │                   │  │                           │   │
│  │  • Human eval     │  │  • Custom models  │  │  • Reserved capacity      │   │
│  │  • Compare models │  │  • Continued pre  │  │  • Predictable latency    │   │
│  │  • Custom metrics │  │  • Model distill  │  │  • Cost commitment        │   │
│  └───────────────────┘  └───────────────────┘  └───────────────────────────┘   │
│                                                                                 │
│  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────────────┐   │
│  │   BATCH           │  │   FLOWS           │  │    MARKETPLACE            │   │
│  │   INFERENCE       │  │   (Preview)       │  │                           │   │
│  │                   │  │                   │  │                           │   │
│  │  • Async jobs     │  │  • Visual builder │  │  • 3rd party models       │   │
│  │  • 50% cheaper    │  │  • Chain prompts  │  │  • Specialized models     │   │
│  │  • Large scale    │  │  • Conditions     │  │  • Subscribe & use        │   │
│  └───────────────────┘  └───────────────────┘  └───────────────────────────┘   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## What We've Covered vs What's Left

| Component | Covered? | How We Used It | Priority |
|-----------|----------|----------------|----------|
| **Foundation Models** | ✅ Yes | `invoke_model()`, streaming | Must know |
| **Guardrails** | ✅ Yes | PII anonymization | Must know |
| **Knowledge Base** | ❌ No | - | High - most common enterprise use |
| **Agents** | ❌ No | - | High - growing adoption |
| **Model Evaluation** | ❌ No | - | Medium |
| **Fine-tuning** | ❌ No | - | Low (expensive, rare) |
| **Batch Inference** | ❌ No | - | Medium |
| **Provisioned Throughput** | ❌ No | - | Low (enterprise only) |
| **Flows** | ❌ No | - | Low (preview) |
| **Marketplace** | ❌ No | - | Low |

---

## Priority Matrix: What to Learn

### 🔴 MUST KNOW (Interview + Production)

| Feature | Why Critical | Learn How |
|---------|--------------|-----------|
| **Foundation Model Invocation** | Core skill, everything builds on this | ✅ Done (bedrock_client.py) |
| **Streaming** | Required for any chat UI | ✅ Done |
| **Guardrails** | Compliance requirement | ✅ Done |
| **Knowledge Base** | 80% of enterprise GenAI is RAG | ⬜ Next |
| **Agents** | Growing fast, complex workflows | ⬜ After KB |

### 🟡 SHOULD KNOW (Production)

| Feature | Why Important | When to Learn |
|---------|---------------|---------------|
| **Batch Inference** | Cost savings for bulk processing | Week 3-4 |
| **Model Evaluation** | Compare models, measure quality | Week 3-4 |
| **Embeddings (Titan)** | Required for RAG | With Knowledge Base |

### 🟢 NICE TO KNOW (Specialized)

| Feature | Why Specialized | When to Learn |
|---------|-----------------|---------------|
| **Fine-tuning** | Expensive, rare use case | If job requires |
| **Provisioned Throughput** | Enterprise scale only | If job requires |
| **Flows** | Still in preview | When GA |
| **Marketplace** | Niche models | As needed |

---

## How Enterprises Actually Use Bedrock

### Pattern 1: Knowledge Base (Most Common - 60% of deployments)

```
┌─────────────────────────────────────────────────────────────────┐
│                    ENTERPRISE KNOWLEDGE BASE                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   Data Sources              Bedrock KB              Application │
│   ┌─────────┐              ┌─────────┐              ┌─────────┐│
│   │   S3    │─────────────▶│ Auto    │              │  Chat   ││
│   │ (PDFs)  │              │ Chunk   │              │   UI    ││
│   └─────────┘              │ Auto    │◀────────────▶│         ││
│   ┌─────────┐              │ Embed   │              │ "What's ││
│   │Confluence│────────────▶│ Auto    │              │  our    ││
│   │  (docs) │              │ Index   │              │ policy?"││
│   └─────────┘              └─────────┘              └─────────┘│
│   ┌─────────┐                  │                               │
│   │ Web     │──────────────────┘                               │
│   │ Crawler │                                                  │
│   └─────────┘                                                  │
│                                                                 │
│   WHY COMPANIES USE THIS:                                       │
│   • No vector DB to manage                                      │
│   • No chunking/embedding code to write                         │
│   • Auto-sync when source docs change                           │
│   • Built-in citation/source tracking                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Real Use Cases:**
- HR policy Q&A bot
- Customer support with product docs
- Legal contract search
- Engineering documentation search

### Pattern 2: Agents (Growing Fast - 25% of deployments)

```
┌─────────────────────────────────────────────────────────────────┐
│                      BEDROCK AGENT                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   User: "Book me a flight to Sydney next Tuesday under $500"    │
│                              │                                  │
│                              ▼                                  │
│                    ┌─────────────────┐                          │
│                    │  Bedrock Agent  │                          │
│                    │  (Orchestrator) │                          │
│                    └────────┬────────┘                          │
│                             │                                   │
│         ┌───────────────────┼───────────────────┐               │
│         │                   │                   │               │
│         ▼                   ▼                   ▼               │
│   ┌───────────┐      ┌───────────┐      ┌───────────┐          │
│   │  Lambda   │      │  Lambda   │      │  Lambda   │          │
│   │ (Search   │      │ (Check    │      │ (Book     │          │
│   │  Flights) │      │  Calendar)│      │  Flight)  │          │
│   └───────────┘      └───────────┘      └───────────┘          │
│                                                                 │
│   Agent thinks:                                                 │
│   1. "I need to search flights" → calls search Lambda           │
│   2. "I need to check user's calendar" → calls calendar Lambda  │
│   3. "Found good option, booking" → calls booking Lambda        │
│   4. Returns: "Booked QF1 for $450, departing 9am Tuesday"      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Real Use Cases:**
- IT helpdesk (reset password, create ticket, check status)
- Order management (track, modify, cancel orders)
- Data analysis (query databases, generate reports)
- DevOps assistant (check logs, restart services)

### Pattern 3: Direct API + Custom RAG (15% of deployments)

```
┌─────────────────────────────────────────────────────────────────┐
│                    CUSTOM RAG PIPELINE                          │
│                    (What we built today)                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   WHY BUILD CUSTOM instead of using Bedrock KB?                 │
│                                                                 │
│   • Need specific chunking strategy                             │
│   • Need hybrid search (keyword + vector)                       │
│   • Need custom re-ranking                                      │
│   • Need multi-tenant with row-level security                   │
│   • Need to use non-AWS vector DB (Pinecone, Weaviate)          │
│   • Need fine-grained control over retrieval                    │
│                                                                 │
│   Your bedrock_client.py is the foundation for this pattern     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## What You Should Practice Next (Today)

### Option A: Bedrock Knowledge Base (Recommended)
Most common enterprise pattern. Learn:
- Create KB via console/CLI
- Connect S3 data source
- Query via API
- Understand chunking strategies
- Compare with custom RAG

### Option B: Bedrock Agents
More complex but powerful. Learn:
- Create agent with action groups
- Connect Lambda functions
- Multi-step reasoning
- Session management

### Option C: Batch Inference
Good for cost optimization. Learn:
- Submit batch jobs
- Process results
- Compare costs (50% cheaper)

---

## Interview Expectations by Role

### AI/ML Engineer (Your Target)

| Topic | Expected Knowledge |
|-------|-------------------|
| Foundation Models | Deep - invoke, streaming, model selection |
| Guardrails | Deep - setup, PII, content filtering |
| Knowledge Base | Medium - when to use, how it works |
| Agents | Medium - concepts, use cases |
| Custom RAG | Deep - chunking, embeddings, retrieval |
| Cost Optimization | Deep - model routing, caching, batch |

### Solutions Architect

| Topic | Expected Knowledge |
|-------|-------------------|
| All Bedrock services | Broad - when to use each |
| Integration patterns | Deep - with other AWS services |
| Security/Compliance | Deep - VPC, IAM, encryption |
| Cost estimation | Deep - pricing models |

### Data Scientist

| Topic | Expected Knowledge |
|-------|-------------------|
| Model Evaluation | Deep - metrics, comparison |
| Fine-tuning | Medium - when/how |
| Prompt Engineering | Deep - techniques |
| RAG Quality | Deep - retrieval metrics |

---

## Recommended Learning Path (Rest of Today)

```
NOW (30 min)
├── Understand Bedrock KB concepts (this doc)
├── Create KB via CLI with S3 source
└── Query KB via API

LATER TODAY (1 hr)
├── Compare: KB query vs custom RAG
├── Understand when to use which
└── Document trade-offs

TOMORROW (Desktop)
├── Bedrock Agents basics
├── Create simple agent with Lambda
└── Multi-step workflow
```

---

## Quick Decision Guide: Which Bedrock Feature?

```
START
  │
  ▼
Do you need to search documents/knowledge?
  │
  ├── YES ──▶ Is your use case standard (no custom chunking/ranking)?
  │              │
  │              ├── YES ──▶ Use BEDROCK KNOWLEDGE BASE
  │              │
  │              └── NO ───▶ Use CUSTOM RAG (your bedrock_client.py + vector DB)
  │
  └── NO ───▶ Do you need multi-step actions (book, update, query systems)?
                 │
                 ├── YES ──▶ Use BEDROCK AGENTS
                 │
                 └── NO ───▶ Do you need to process 1000s of items?
                                │
                                ├── YES ──▶ Use BATCH INFERENCE
                                │
                                └── NO ───▶ Use DIRECT API (bedrock_client.py)
```

---

Ready to try Bedrock Knowledge Base next?

---

## Deep Dive: Managed RAG vs Custom RAG

### The Core Trade-off

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                                                                 │
│   MANAGED RAG (Bedrock KB)              CUSTOM RAG (Your Code)                  │
│   ════════════════════════              ════════════════════════                │
│                                                                                 │
│   ✅ Fast to deploy (days)              ✅ Full control                         │
│   ✅ No infra to manage                 ✅ Custom chunking strategies           │
│   ✅ Auto-sync data sources             ✅ Hybrid search (keyword + vector)     │
│   ✅ Built-in citations                 ✅ Custom re-ranking                    │
│   ✅ AWS handles scaling                ✅ Multi-tenant row-level security      │
│                                         ✅ Any vector DB (Pinecone, etc.)       │
│   ❌ Limited chunking control                                                   │
│   ❌ AWS vector stores only             ❌ Weeks/months to build                │
│   ❌ Basic retrieval strategies         ❌ Ongoing maintenance burden           │
│   ❌ Less flexibility                   ❌ Need ML/NLP expertise                │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Decision Framework

```
START: Do you need RAG?
    │
    ▼
Is time-to-market critical? (need it in weeks, not months)
    │
    ├── YES ──▶ Use MANAGED RAG (Bedrock KB)
    │
    └── NO ───▶ Do you have specific requirements?
                    │
                    ├── Custom chunking (legal contracts, code, etc.)
                    ├── Hybrid search (keyword + semantic)
                    ├── Multi-tenant with row-level security
                    ├── Non-AWS vector DB (Pinecone, Weaviate)
                    ├── Custom re-ranking models
                    │
                    └── ANY of these? ──▶ Use CUSTOM RAG
                        NONE of these? ──▶ Use MANAGED RAG
```

---

## Industry-Specific RAG Requirements

### 🏦 Financial Services

| Requirement | Managed RAG? | Custom RAG? | Why |
|-------------|--------------|-------------|-----|
| Regulatory compliance Q&A | ✅ Good fit | | Standard doc search |
| Fraud detection with real-time data | | ✅ Required | Need live data feeds + custom logic |
| Multi-tenant wealth management | | ✅ Required | Row-level security per client |
| Internal policy search | ✅ Good fit | | Standard use case |
| Trading research with proprietary models | | ✅ Required | Custom ranking, hybrid search |

**Real Example - Ramp (Fintech):**
Used RAG for customer classification with NAICS codes. Needed custom retrieval to match business descriptions to industry codes accurately. Built custom because standard chunking couldn't handle the nuanced matching required.

**Real Example - ClearBank:**
Uses RAG for KYC document review. Managed RAG works because it's standard document Q&A against compliance policies.

---

### ⚖️ Legal Tech

| Requirement | Managed RAG? | Custom RAG? | Why |
|-------------|--------------|-------------|-----|
| Contract clause search | | ✅ Required | Contracts need semantic chunking by clause |
| Case law research | ✅ Maybe | ✅ Better | Depends on citation precision needs |
| Due diligence (millions of docs) | | ✅ Required | Scale + custom ranking |
| Compliance policy Q&A | ✅ Good fit | | Standard doc search |
| Multi-client document isolation | | ✅ Required | Strict data separation |

**Why Legal Often Needs Custom:**
- Legal documents have specific structure (clauses, definitions, cross-references)
- Standard chunking breaks clause boundaries
- Need to retrieve related clauses even when not explicitly mentioned
- Citation precision is legally required (page, paragraph, line)

**Real Example - Harvey (Legal AI):**
Built custom RAG because law firms need:
- Retrieval across decades of internal memos
- Precise citation to specific paragraphs
- Integration with proprietary case databases

---

### 🏥 Healthcare

| Requirement | Managed RAG? | Custom RAG? | Why |
|-------------|--------------|-------------|-----|
| Clinical decision support | | ✅ Required | Need real-time patient data + research |
| Patient re-admission prediction | | ✅ Required | Combines structured + unstructured data |
| Medical training content | ✅ Good fit | | Standard educational content |
| Drug interaction lookup | ✅ Good fit | | Standard reference search |
| HIPAA-compliant multi-tenant | | ✅ Required | Strict data isolation |

**Why Healthcare Often Needs Custom:**
- Must combine structured data (lab results, vitals) with unstructured (notes, research)
- Real-time data integration (not just static documents)
- Strict audit requirements for every retrieval
- Multi-modal (images, scans + text)

**Real Example - MedRAG Framework:**
Custom RAG improved diagnostic accuracy by 23% by:
- Combining patient records with latest research
- Custom retrieval that understands medical terminology
- Integration with imaging data

---

### 🎓 Education

| Requirement | Managed RAG? | Custom RAG? | Why |
|-------------|--------------|-------------|-----|
| Course catalog Q&A | ✅ Good fit | | Standard doc search |
| Admissions chatbot | ✅ Good fit | | FAQ-style retrieval |
| Personalized tutoring | | ✅ Required | Need learning history + adaptive retrieval |
| Academic research assistant | | ✅ Better | Need citation precision + source ranking |
| Multi-institution platform | | ✅ Required | Tenant isolation |

**Real Example - Ho Chi Minh City University:**
Used managed RAG for admissions chatbot - standard Q&A against policy documents. Matched commercial systems in accuracy.

---

## Technical Comparison

### Chunking Strategies

| Strategy | Managed RAG | Custom RAG | Best For |
|----------|-------------|------------|----------|
| Fixed size (500 tokens) | ✅ Default | ✅ | General documents |
| Semantic (by meaning) | ❌ Limited | ✅ | Technical docs |
| Hierarchical (parent-child) | ❌ No | ✅ | Long documents with sections |
| Document-specific (by clause) | ❌ No | ✅ | Contracts, legal |
| Sliding window with overlap | ✅ Configurable | ✅ | Most use cases |

### Retrieval Strategies

| Strategy | Managed RAG | Custom RAG | When Needed |
|----------|-------------|------------|-------------|
| Vector similarity | ✅ Yes | ✅ | Always |
| Keyword (BM25) | ❌ No | ✅ | Exact term matching |
| Hybrid (vector + keyword) | ❌ No | ✅ | Best accuracy |
| Re-ranking (cross-encoder) | ❌ No | ✅ | High precision needs |
| Query expansion | ❌ No | ✅ | Ambiguous queries |
| Multi-query retrieval | ❌ No | ✅ | Complex questions |

### Data Sources

| Source | Managed RAG (Bedrock KB) | Custom RAG |
|--------|--------------------------|------------|
| S3 | ✅ Native | ✅ |
| Web crawler | ✅ Native | ✅ |
| Confluence | ✅ Native | ✅ |
| SharePoint | ✅ Native | ✅ |
| Salesforce | ✅ Native | ✅ |
| Custom databases | ❌ No | ✅ |
| Real-time APIs | ❌ No | ✅ |
| Proprietary formats | ❌ Limited | ✅ |

### Vector Stores

| Store | Managed RAG (Bedrock KB) | Custom RAG |
|-------|--------------------------|------------|
| OpenSearch Serverless | ✅ | ✅ |
| Amazon Aurora (pgvector) | ✅ | ✅ |
| Pinecone | ✅ | ✅ |
| Redis Enterprise | ✅ | ✅ |
| MongoDB Atlas | ✅ | ✅ |
| Weaviate | ❌ | ✅ |
| Qdrant | ❌ | ✅ |
| Milvus | ❌ | ✅ |
| Self-hosted pgvector | ❌ | ✅ |

---

## Cost Comparison

### Managed RAG (Bedrock KB) Costs

```
Monthly cost for 10,000 documents, 1,000 queries/day:

Vector Store (OpenSearch Serverless):
  - Minimum 2 OCUs indexing: ~$350/month
  - Minimum 2 OCUs search: ~$350/month
  - Storage: ~$24/GB/month

Embedding (Titan):
  - Initial indexing: ~$10 (one-time)
  - Re-indexing on updates: varies

LLM (Claude Haiku for generation):
  - 1,000 queries × 30 days × $0.0005/query = ~$15/month

TOTAL: ~$750-1,000/month minimum
```

### Custom RAG Costs

```
Monthly cost for 10,000 documents, 1,000 queries/day:

Vector Store (self-managed pgvector on RDS):
  - db.t3.medium: ~$50/month
  - Storage: ~$10/month

OR Pinecone:
  - Starter: Free (limited)
  - Standard: ~$70/month

Embedding:
  - OpenAI ada-002: ~$10/month
  - OR self-hosted: $0 (but compute cost)

LLM:
  - Same as managed: ~$15/month

Engineering time (ongoing):
  - 10-20% of one engineer: ~$2,000-4,000/month

TOTAL: ~$100/month infra + engineering time
```

### Cost Decision Matrix

| Scenario | Cheaper Option | Why |
|----------|----------------|-----|
| Quick POC, small scale | Managed | No engineering time |
| Production, standard use case | Managed | Maintenance included |
| High volume (100K+ queries/day) | Custom | Avoid per-query costs |
| Need specific features | Custom | Can't do it with managed |
| Small team, no ML expertise | Managed | Can't build custom anyway |

---

## Build vs Buy Decision Matrix

### Choose MANAGED RAG (Bedrock KB) When:

| Situation | Why Managed Works |
|-----------|-------------------|
| Standard document Q&A | Exactly what it's designed for |
| Time-to-market < 4 weeks | Can deploy in days |
| Team lacks ML/NLP expertise | No expertise needed |
| Documents are standard formats | Good parsing built-in |
| Single-tenant or simple multi-tenant | Handles this well |
| Budget for managed services | Predictable costs |

### Choose CUSTOM RAG When:

| Situation | Why Custom Required |
|-----------|---------------------|
| Legal/contract documents | Need clause-aware chunking |
| Multi-tenant SaaS with strict isolation | Row-level security |
| Hybrid search required | Managed doesn't support |
| Real-time data integration | Managed is batch-only |
| Custom ranking/re-ranking | Not available in managed |
| Non-AWS vector store preference | Limited options in managed |
| High volume (cost optimization) | Custom can be cheaper at scale |
| Regulatory audit requirements | Need full control over pipeline |

---

## Learning Path Refinement

Based on this analysis, here's your refined learning path:

### Week 1-2: Foundation (Current)
- ✅ Bedrock API, streaming, guardrails
- ✅ Cost tracking, model routing
- ⬜ **Bedrock Knowledge Base** (managed RAG)
  - Create KB with S3 source
  - Query via API
  - Understand limitations

### Week 3: Custom RAG Fundamentals
- ⬜ Chunking strategies (fixed, semantic, hierarchical)
- ⬜ Embedding models (Titan vs OpenAI vs open-source)
- ⬜ Vector stores (pgvector locally, compare with OpenSearch)
- ⬜ Basic retrieval pipeline

### Week 4: Advanced RAG (Differentiator Skills)
- ⬜ Hybrid search (BM25 + vector)
- ⬜ Re-ranking with cross-encoders
- ⬜ Query expansion and transformation
- ⬜ Evaluation metrics (Ragas)

### Month 2: Production Patterns
- ⬜ Multi-tenant RAG architecture
- ⬜ Caching strategies
- ⬜ Observability and monitoring
- ⬜ Cost optimization at scale

### Interview Preparation Focus

| Topic | Managed RAG | Custom RAG | Priority |
|-------|-------------|------------|----------|
| When to use which | Must know | Must know | 🔴 High |
| Chunking strategies | Basic | Deep | 🔴 High |
| Hybrid search | Conceptual | Implementation | 🔴 High |
| Re-ranking | Conceptual | Implementation | 🟡 Medium |
| Multi-tenant design | Basic | Deep | 🔴 High |
| Cost optimization | Know options | Implementation | 🟡 Medium |

---

## Summary: The Real-World Picture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     ENTERPRISE RAG ADOPTION PATTERN                             │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   PHASE 1: POC                                                                  │
│   └── Most companies start with Managed RAG (Bedrock KB)                        │
│       └── Fast, low risk, proves value                                          │
│                                                                                 │
│   PHASE 2: Production (Simple Use Cases)                                        │
│   └── Stay with Managed RAG if:                                                 │
│       └── Standard doc Q&A, internal knowledge base, FAQ bot                    │
│                                                                                 │
│   PHASE 3: Production (Complex Use Cases)                                       │
│   └── Migrate to Custom RAG when:                                               │
│       └── Hit limitations (chunking, hybrid search, multi-tenant)               │
│       └── Scale requires cost optimization                                      │
│       └── Regulatory requirements demand full control                           │
│                                                                                 │
│   YOUR SKILL TARGET:                                                            │
│   └── Know BOTH approaches                                                      │
│   └── Understand WHEN to use each                                               │
│   └── Can IMPLEMENT custom when needed                                          │
│   └── Can ADVISE on architecture decisions                                      │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Next Steps for Today

1. **Try Bedrock Knowledge Base** (30 min)
   - Create KB with sample docs
   - Query via API
   - Understand what it can/can't do

2. **Document the limitations you observe** (15 min)
   - What chunking options exist?
   - What retrieval strategies available?
   - What's missing vs custom?

3. **Plan custom RAG learning** (Week 3)
   - Based on gaps identified

Ready to create a Bedrock Knowledge Base?
