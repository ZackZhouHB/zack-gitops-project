# AWS OpenSearch + Bedrock Knowledge Base: Deep Dive

> Architecture, costs, best practices, and when to use vs custom RAG

---

## Why OpenSearch for Bedrock KB?

### The Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     BEDROCK KNOWLEDGE BASE ARCHITECTURE                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   DATA SOURCES                    BEDROCK KB                    VECTOR STORE    │
│   ┌─────────┐                    ┌──────────┐                  ┌─────────────┐  │
│   │   S3    │───────────────────▶│          │                  │ OpenSearch  │  │
│   │ (docs)  │                    │  Ingest  │                  │ Serverless  │  │
│   └─────────┘                    │  Pipeline│                  │             │  │
│   ┌─────────┐                    │          │    Embeddings    │  ┌───────┐  │  │
│   │ Web     │───────────────────▶│ ┌──────┐ │───────────────▶  │  │Vectors│  │  │
│   │ Crawler │                    │ │Chunk │ │                  │  │ Index │  │  │
│   └─────────┘                    │ └──────┘ │                  │  └───────┘  │  │
│   ┌─────────┐                    │ ┌──────┐ │                  │             │  │
│   │Confluence│──────────────────▶│ │Embed │ │                  │  Managed by │  │
│   └─────────┘                    │ │(Titan)│ │                  │  AWS        │  │
│   ┌─────────┐                    │ └──────┘ │                  │             │  │
│   │SharePoint│─────────────────▶│          │                  │  Auto-scale │  │
│   └─────────┘                    └──────────┘                  └─────────────┘  │
│                                                                                 │
│   QUERY FLOW                                                                    │
│   ┌──────────────────────────────────────────────────────────────────────────┐  │
│   │                                                                          │  │
│   │  User Query ──▶ Embed Query ──▶ Vector Search ──▶ Retrieve ──▶ Generate  │  │
│   │                   (Titan)       (OpenSearch)      Chunks       (Claude)  │  │
│   │                                                                          │  │
│   └──────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Why AWS Chose OpenSearch Serverless

| Reason | Explanation |
|--------|-------------|
| **Native k-NN support** | OpenSearch has built-in vector search (k-nearest neighbors) |
| **Serverless = managed** | No cluster management, auto-scaling |
| **AWS integration** | IAM, VPC, CloudWatch, encryption - all native |
| **Enterprise features** | Fine-grained access control, audit logs |
| **Hybrid search ready** | Can combine vector + keyword (BM25) in same index |

---

## OpenSearch Serverless Architecture

### How It Works

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      OPENSEARCH SERVERLESS INTERNALS                            │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │                         COLLECTION                                      │   │
│   │   (logical grouping - like a "database")                                │   │
│   │                                                                         │   │
│   │   Type: VECTORSEARCH (optimized for k-NN)                               │   │
│   │                                                                         │   │
│   │   ┌─────────────────────────────────────────────────────────────────┐   │   │
│   │   │                        INDEX                                    │   │   │
│   │   │   (like a "table" - holds your vectors)                         │   │   │
│   │   │                                                                 │   │   │
│   │   │   Fields:                                                       │   │   │
│   │   │   - id: keyword                                                 │   │   │
│   │   │   - embedding: knn_vector (1024 dimensions)                     │   │   │
│   │   │   - text: text (original chunk content)                         │   │   │
│   │   │   - metadata: object (source, page, etc.)                       │   │   │
│   │   │                                                                 │   │   │
│   │   └─────────────────────────────────────────────────────────────────┘   │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│   COMPUTE UNITS (OCUs)                                                          │
│   ┌─────────────────────┐    ┌─────────────────────┐                            │
│   │   INDEXING OCUs     │    │    SEARCH OCUs      │                            │
│   │                     │    │                     │                            │
│   │   - Write operations│    │   - Query operations│                            │
│   │   - Min: 2 OCUs     │    │   - Min: 2 OCUs     │                            │
│   │   - Auto-scales up  │    │   - Auto-scales up  │                            │
│   │                     │    │                     │                            │
│   └─────────────────────┘    └─────────────────────┘                            │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### The OCU (OpenSearch Compute Unit) Model

```
1 OCU = 6 GB memory + corresponding compute

MINIMUM CONFIGURATION:
├── 2 Indexing OCUs (always running)
├── 2 Search OCUs (always running)
└── TOTAL: 4 OCUs minimum

COST CALCULATION:
├── $0.24 per OCU-hour
├── 4 OCUs × 24 hours × 30 days = 2,880 OCU-hours
└── 2,880 × $0.24 = $691.20/month MINIMUM
```

**This is why it's expensive for small workloads** - you pay for minimum capacity even when idle.

---

## Cost Deep Dive

### OpenSearch Serverless Pricing

| Component | Price | Minimum | Monthly Minimum |
|-----------|-------|---------|-----------------|
| Indexing OCU | $0.24/hour | 2 OCUs | $345.60 |
| Search OCU | $0.24/hour | 2 OCUs | $345.60 |
| Storage | $0.024/GB/month | - | Varies |
| **TOTAL** | | | **~$700+/month** |

### Comparison with Alternatives

| Vector Store | Monthly Cost (Small) | Monthly Cost (Large) | Best For |
|--------------|---------------------|---------------------|----------|
| OpenSearch Serverless | $700+ | $2,000+ | Enterprise, compliance |
| Aurora pgvector | $30-100 | $200-500 | Cost-conscious, AWS-native |
| Pinecone | Free-$70 | $200+ | Quick start, external OK |
| Self-hosted pgvector | $0 (local) | $50-200 (EC2) | Full control, learning |
| Qdrant Cloud | Free-$25 | $100+ | Performance-focused |

### When OpenSearch Serverless Cost Makes Sense

```
BREAK-EVEN ANALYSIS:

OpenSearch Serverless: $700/month fixed + usage

Custom RAG (Aurora pgvector):
├── Aurora db.t3.medium: $50/month
├── Engineering time: 40 hours × $100/hour = $4,000 (one-time)
├── Ongoing maintenance: 5 hours/month × $100 = $500/month
└── Total Year 1: $4,000 + ($550 × 12) = $10,600

OpenSearch Serverless Year 1: $700 × 12 = $8,400

CONCLUSION:
├── < 1 year, small team: OpenSearch might be cheaper (no build time)
├── > 1 year, have engineers: Custom is cheaper
├── Enterprise compliance needs: OpenSearch (audit, encryption, IAM)
└── Startup/learning: Custom (can't justify $700/month)
```

---

## What OpenSearch + Bedrock KB Does Best

### ✅ Strengths

| Capability | Why It's Good |
|------------|---------------|
| **Zero infrastructure** | No clusters to manage, patches, scaling |
| **Native AWS security** | IAM, VPC, encryption at rest/transit, audit logs |
| **Auto-sync data sources** | S3, Confluence, SharePoint, Web - automatic updates |
| **Built-in chunking** | Default strategies work for most docs |
| **Citation tracking** | Returns source document + location |
| **Hybrid search ready** | Can enable keyword + vector (though limited in KB) |
| **Enterprise compliance** | SOC2, HIPAA eligible, FedRAMP |

### Best Use Cases for Managed KB + OpenSearch

| Use Case | Why Managed Works |
|----------|-------------------|
| **Internal knowledge base** | Standard docs, no custom logic needed |
| **Customer support bot** | FAQ, product docs, policies |
| **Compliance Q&A** | Audit trail important, standard retrieval |
| **Quick POC** | Prove value before building custom |
| **Small team, no ML expertise** | Can't build custom anyway |

---

## What OpenSearch + Bedrock KB Cannot Do Well

### ❌ Limitations

| Limitation | Impact | Custom RAG Solution |
|------------|--------|---------------------|
| **Limited chunking control** | Can't do semantic or clause-based chunking | Custom chunker |
| **No hybrid search in KB API** | Vector only through RetrieveAndGenerate | Implement BM25 + vector |
| **No custom re-ranking** | Can't add cross-encoder | Add reranker step |
| **Basic metadata filtering** | Limited filter expressions | Full query flexibility |
| **No real-time data** | Batch sync only (scheduled) | Stream updates |
| **Single retrieval strategy** | Can't do multi-query or HyDE | Custom retrieval |
| **Fixed embedding model** | Titan only (in KB) | Any embedding model |
| **Cost at small scale** | $700/month minimum | $0-50/month |

### ❌ Data Source Limitations

| Source | Bedrock KB Support | Notes |
|--------|-------------------|-------|
| **ServiceNow** | ❌ NO CONNECTOR | Must manually export to CSV → S3 |
| **Jira** | ❌ NO CONNECTOR | Must manually export |
| **Miro** | ❌ NO CONNECTOR | Visual only - not extractable |
| **Custom databases** | ❌ NO | No direct DB connectors |
| **Real-time APIs** | ❌ NO | Batch sync only |

### ❌ File Format Limitations

| Format | Support | Content Captured |
|--------|---------|------------------|
| **PDF (text)** | ✅ Good | ~80% |
| **PDF (with diagrams)** | ⚠️ Partial | ~30-50% (diagrams LOST) |
| **PDF (scanned)** | ❌ Poor | No OCR |
| **PowerPoint** | ⚠️ Partial | ~40-60% (visuals LOST) |
| **Word** | ✅ Good | ~60-80% |
| **Images** | ❌ None | Not processed |
| **Miro exports** | ❌ None | Visual only |

**See:** `your-data-vs-bedrock-kb-analysis.md` for detailed analysis of YOUR specific data sources.

### Use Cases That Need Custom RAG

| Use Case | Why Custom Required |
|----------|---------------------|
| **Legal/contract search** | Need clause-aware chunking |
| **Code search** | Need syntax-aware chunking |
| **Multi-tenant SaaS** | Row-level security per customer |
| **Real-time data** | Live feeds, not batch |
| **Hybrid search critical** | Error codes, IDs need exact match |
| **Cost-sensitive** | Can't justify $700/month |
| **Custom ranking** | Domain-specific relevance |

---

## Enterprise Architecture Patterns

### Pattern 1: Simple Internal KB (Managed)

```
┌─────────────────────────────────────────────────────────────────┐
│                    SIMPLE INTERNAL KB                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   Confluence ──┐                                                │
│                │     ┌──────────────┐     ┌──────────────────┐  │
│   SharePoint ──┼────▶│  Bedrock KB  │────▶│ OpenSearch       │  │
│                │     │  (managed)   │     │ Serverless       │  │
│   S3 docs ─────┘     └──────┬───────┘     └──────────────────┘  │
│                             │                                   │
│                             ▼                                   │
│                      ┌──────────────┐                           │
│                      │   Slack Bot  │                           │
│                      │   or Web UI  │                           │
│                      └──────────────┘                           │
│                                                                 │
│   COST: ~$800-1000/month                                        │
│   EFFORT: Days to set up                                        │
│   MAINTENANCE: Near zero                                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Pattern 2: Hybrid (Managed + Custom Components)

```
┌─────────────────────────────────────────────────────────────────┐
│                    HYBRID ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                    CUSTOM LAYER                         │   │
│   │                                                         │   │
│   │   Query ──▶ Query Expansion ──▶ Hybrid Search ──────┐   │   │
│   │                                  (BM25 + Vector)    │   │   │
│   │                                                     │   │   │
│   │              ┌──────────────────────────────────────┘   │   │
│   │              │                                          │   │
│   │              ▼                                          │   │
│   │         Re-ranker ──▶ Top K ──▶ Generate (Bedrock)      │   │
│   │                                                         │   │
│   └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                  MANAGED LAYER                          │   │
│   │                                                         │   │
│   │   Bedrock KB ──▶ OpenSearch Serverless                  │   │
│   │   (ingestion)    (vector storage)                       │   │
│   │                                                         │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│   COST: ~$900-1200/month                                        │
│   EFFORT: Weeks                                                 │
│   BENEFIT: Best of both - managed storage, custom retrieval     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Pattern 3: Full Custom (Your Case Study)

```
┌─────────────────────────────────────────────────────────────────┐
│                    FULL CUSTOM RAG                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   Data Sources          Custom Pipeline           Vector Store  │
│   ┌─────────┐           ┌─────────────┐          ┌───────────┐  │
│   │SharePoint│──────────▶│             │          │           │  │
│   └─────────┘           │  Lambda/    │          │  Aurora   │  │
│   ┌─────────┐           │  ECS        │          │  pgvector │  │
│   │ServiceNow│─────────▶│             │─────────▶│           │  │
│   └─────────┘           │  - Custom   │          │  ~$50/mo  │  │
│   ┌─────────┐           │    chunking │          │           │  │
│   │Confluence│─────────▶│  - Hybrid   │          └───────────┘  │
│   └─────────┘           │    embed    │                │        │
│                         └─────────────┘                │        │
│                                                        │        │
│   Query Flow                                           │        │
│   ┌────────────────────────────────────────────────────┘        │
│   │                                                             │
│   │  Query ──▶ Expand ──▶ Hybrid Search ──▶ Rerank ──▶ Generate │
│   │            (LLM)      (BM25+Vector)    (cross-   (Bedrock)  │
│   │                                         encoder)            │
│   │                                                             │
│   └─────────────────────────────────────────────────────────────┘
│                                                                 │
│   COST: ~$100-200/month (infra) + engineering time              │
│   EFFORT: Weeks to months                                       │
│   BENEFIT: Full control, best quality, lowest infra cost        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Best Practices for OpenSearch + Bedrock KB

### If You Choose Managed KB

| Practice | Why |
|----------|-----|
| **Start with default chunking** | Test before customizing |
| **Use metadata filters** | Narrow search by source, date, category |
| **Set up CloudWatch alarms** | Monitor latency, errors |
| **Use VPC endpoints** | Keep traffic private |
| **Enable audit logging** | Compliance requirement |
| **Schedule sync wisely** | Balance freshness vs cost |

### Index Design for OpenSearch

```json
{
  "settings": {
    "index": {
      "knn": true,
      "knn.algo_param.ef_search": 512
    }
  },
  "mappings": {
    "properties": {
      "embedding": {
        "type": "knn_vector",
        "dimension": 1024,
        "method": {
          "name": "hnsw",
          "space_type": "cosinesimil",
          "engine": "nmslib",
          "parameters": {
            "ef_construction": 512,
            "m": 16
          }
        }
      },
      "text": { "type": "text" },
      "source": { "type": "keyword" },
      "metadata": { "type": "object" }
    }
  }
}
```

### HNSW Parameters Explained

| Parameter | What It Does | Trade-off |
|-----------|--------------|-----------|
| **ef_construction** | Build-time accuracy | Higher = better index, slower build |
| **m** | Connections per node | Higher = better recall, more memory |
| **ef_search** | Query-time accuracy | Higher = better results, slower query |

---

## Decision Matrix: Your Situation

### Your Requirements

| Requirement | Managed KB | Custom RAG |
|-------------|------------|------------|
| SharePoint PDFs | ✅ Native connector | ✅ Need to build |
| ServiceNow incidents | ❌ No connector | ✅ API integration |
| Confluence | ✅ Native connector | ✅ API integration |
| Hybrid search (error codes) | ❌ Limited | ✅ Full control |
| Cost < $100/month | ❌ $700+ minimum | ✅ Achievable |
| Quick setup | ✅ Days | ❌ Weeks |
| Learning value | 🟡 Medium | ✅ High |

### Recommendation for You

```
YOUR SITUATION:
├── Budget: Personal/learning (cost-sensitive)
├── Data: ServiceNow (no managed connector)
├── Need: Hybrid search (incident IDs, error codes)
├── Goal: Learn + solve real problem
│
└── RECOMMENDATION: Custom RAG
    ├── Use local pgvector (Docker) for learning
    ├── Use Aurora pgvector for "production" (~$50/month)
    ├── Use Bedrock for embeddings + LLM only
    └── Build hybrid search (critical for your use case)
```

---

## Summary: When to Use What

```
┌─────────────────────────────────────────────────────────────────┐
│                    DECISION FLOWCHART                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   START                                                         │
│     │                                                           │
│     ▼                                                           │
│   Budget > $700/month for vector store?                         │
│     │                                                           │
│     ├── NO ───▶ CUSTOM RAG (pgvector, Pinecone free, etc.)      │
│     │                                                           │
│     └── YES ──▶ Need custom chunking/retrieval?                 │
│                   │                                             │
│                   ├── YES ──▶ CUSTOM RAG or HYBRID              │
│                   │                                             │
│                   └── NO ───▶ Have ML/engineering team?         │
│                                 │                               │
│                                 ├── NO ──▶ MANAGED KB           │
│                                 │                               │
│                                 └── YES ─▶ Time-to-market       │
│                                             critical?           │
│                                               │                 │
│                                               ├── YES ─▶ MANAGED│
│                                               │                 │
│                                               └── NO ──▶ CUSTOM │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Interview Talking Points

**Q: "When would you use Bedrock KB with OpenSearch vs custom RAG?"**

> "Bedrock KB with OpenSearch Serverless is ideal when you need quick deployment, have standard document types, and can justify the ~$700/month minimum cost. It's great for enterprise compliance needs with built-in audit logging and IAM integration.
>
> I'd choose custom RAG when: cost is a concern, I need hybrid search for exact matching (like error codes or IDs), I need custom chunking for specialized documents like legal contracts, or I need to integrate data sources without native connectors like ServiceNow.
>
> In my case study, I built custom RAG because I needed ServiceNow integration, hybrid search for incident IDs, and couldn't justify $700/month for a learning project. The trade-off was more development time but full control over the retrieval pipeline."

---

## Files in This Section

```
stage1/bedrock-kb-demo/
├── sample-docs/           # Sample docs (kept for reference)
│   ├── eks-runbook.md
│   ├── servicenow-incidents.csv
│   └── vpc-troubleshooting.md
└── (AWS resources cleaned up)
```

Ready to move on to building your custom RAG with local pgvector?
