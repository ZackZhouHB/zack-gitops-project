# AWS Managed RAG vs Local RAG — What We Gain, What We Lose, and Production Expectations

> **Audience**: Technical decision-makers, solution architects, and engineers evaluating whether to use AWS Bedrock Knowledge Base for production RAG or build a custom local pipeline.

---

## 1. Our Current Solution at a Glance

| Component | What We Use | Role |
|-----------|-------------|------|
| **Vector Store** | OpenSearch Serverless | Stores embeddings, handles similarity search |
| **Embedding Model** | Amazon Titan Embed Text V2 (1024 dimensions) | Converts text chunks into vectors |
| **Knowledge Base** | AWS Bedrock Knowledge Base | Manages chunking, embedding, indexing, and retrieval |
| **Data Sources** | S3 (PDFs/markdown), Web Crawler (blog), Confluence API | Feeds documents into the KB |
| **LLM** | Claude Sonnet 4 via Bedrock | Generates answers from retrieved context |
| **Chunking Strategy** | Bedrock Default (~300 tokens per chunk, sentence-preserving) | No custom configuration set |

### Data Sources We Ingest

| Source | Type | Count | Content Nature |
|--------|------|-------|----------------|
| S3 bucket | PDF, Markdown | 4 docs | Infrastructure docs (Terraform, Azure AD, Lakehouse) |
| Web crawler | HTML pages | 64 pages | Technical blog (EKS, Karpenter, CI/CD, Bedrock) + personal stories |
| Confluence | Wiki pages | 40 pages (8 target) | Solution design docs (Health Analyzer POC, pipeline design) |

---

## 2. Chunking: What AWS Manages vs What You Control Locally

### 2.1 What Bedrock Does Automatically (Default Mode)

When you don't specify a chunking strategy (our current setup), Bedrock:

1. **Parses** the document (extracts text from PDF, HTML, .docx, .md, .csv, .txt)
2. **Splits** into ~300-token chunks, preserving sentence boundaries
3. **Embeds** each chunk using Titan Embed V2 (1024-dimensional vectors)
4. **Indexes** into OpenSearch Serverless with HNSW algorithm
5. **Stores** metadata (source URI, source type, page number)

You write zero chunking code. No LangChain `RecursiveCharacterTextSplitter`. No sentence tokenizers. No overlap tuning.

### 2.2 Bedrock's Available Chunking Options (Configurable)

Bedrock actually offers **5 strategies** — we're using the default, but you can switch:

| Strategy | How It Works | Best For | Our Use? |
|----------|-------------|----------|----------|
| **Default** | ~300 tokens, sentence-preserving | General-purpose, quick start | ✅ Current |
| **Fixed Size** | N tokens with M% overlap | Uniform docs, predictable sizing | Available |
| **Semantic** | NLP-based topic boundary detection | Technical docs with clear sections | Available |
| **Hierarchical** | Parent/child chunks (section → paragraph) | Legal, structured manuals | Available |
| **Custom (Lambda)** | Your Lambda function processes each doc | Images, tables, custom metadata | Available |

> **Key insight**: We're NOT locked into default chunking. Bedrock gives you a spectrum from fully-managed to fully-custom. The Lambda option gives you the same control as a local pipeline — you just deploy it as a Lambda function instead of running it locally.

### 2.3 What You Control in a Local RAG Pipeline

In a local setup (e.g., LangChain + Weaviate + FAISS), you control **everything**:

| Step | Local Control | Tools |
|------|--------------|-------|
| **Document parsing** | Choose parser per file type | PyPDF2, pdfplumber, Unstructured.io, Tika |
| **Image extraction** | Extract images, run OCR, generate captions | Tesseract, GPT-4V, Claude Vision |
| **Table extraction** | Preserve table structure as markdown/JSON | Camelot, Tabula, pdfplumber |
| **Chunking strategy** | Any algorithm, any size, any overlap | LangChain splitters, LlamaIndex nodes |
| **Metadata injection** | Add custom tags (author, date, category) | Manual code |
| **Embedding model** | Any model, local or API | OpenAI, Cohere, local sentence-transformers |
| **Vector store tuning** | Index type, distance metric, sharding | Weaviate, Qdrant, Pinecone, pgvector |
| **Re-ranking** | Second-stage ranking after retrieval | Cohere Rerank, cross-encoders |
| **Hybrid search** | Combine vector + keyword (BM25) search | Weaviate hybrid, Elasticsearch |

---

## 3. What We Gain with AWS Managed RAG

### 3.1 Operational Simplicity

| Benefit | Detail |
|---------|--------|
| **Zero chunking code** | No `text_splitter.split_documents()` to write, test, or maintain |
| **Auto-sync** | S3 upload → Lambda → KB sync. Confluence/Web on schedule. No cron jobs to manage |
| **Managed vector store** | OpenSearch Serverless auto-scales, no cluster management, no shard rebalancing |
| **Embedding at scale** | Titan embeds millions of chunks without you provisioning GPU instances |
| **Built-in metadata** | Source URI, source type, relevance score — automatic provenance tracking |
| **Security** | IAM roles, KMS encryption, VPC endpoints — enterprise-grade out of the box |

### 3.2 Time-to-Production

| Task | Local RAG | AWS Managed |
|------|----------|-------------|
| Set up vector DB | 2-4 hours (install, configure, tune) | 15 minutes (Terraform) |
| Write chunking pipeline | 4-8 hours (per source type) | 0 hours (Bedrock handles it) |
| Build ingestion pipeline | 8-16 hours (S3 watcher, parsers, error handling) | 1 hour (Lambda trigger) |
| Add Confluence source | 16-24 hours (API client, pagination, auth, chunking) | 30 minutes (Terraform data source) |
| Add web crawler | 8-16 hours (Scrapy/Playwright, dedup, scheduling) | 30 minutes (Terraform data source) |
| Monitoring & alerting | 4-8 hours (custom logging, dashboards) | Built-in (CloudWatch) |
| **Total estimate** | **40-80 hours** | **3-5 hours** |

### 3.3 Multi-Source Integration

Bedrock KB natively supports:
- ✅ S3 (PDF, .docx, .md, .txt, .csv, .html)
- ✅ Web crawler (HTTP-only, configurable scope/depth)
- ✅ Confluence (Cloud, via API token)
- ✅ Salesforce
- ✅ SharePoint
- ✅ Custom connectors

With local RAG, each source needs a separate ingestion pipeline you build and maintain.

---

## 4. What We Lose with AWS Managed RAG

### 4.1 Chunking Customization (Default Mode)

| Limitation | Impact on Our Solution | Severity |
|------------|----------------------|----------|
| **No recursive chunking by default** | Bedrock default is simple ~300-token sentence split, not LangChain's `RecursiveCharacterTextSplitter` which respects headers → paragraphs → sentences hierarchy | Medium |
| **No overlap by default** | Default chunks have no overlap — context at chunk boundaries can be lost | Medium |
| **Can't tune per source** | Same chunking strategy applies to ALL data sources in a KB; you can't use semantic chunking for Confluence and fixed-size for PDFs | Medium |
| **No chunk preview** | You can't easily inspect individual chunks before they're indexed (you can query them after, but not preview during ingestion) | Low |

> **Mitigation**: Switch to Fixed Size with overlap, Semantic, or Hierarchical chunking in Terraform. For full control, use the **Custom Lambda** strategy.

### 4.2 Document Parsing Limitations

| Limitation | Detail | Impact |
|------------|--------|--------|
| **Image extraction** | Default parser ignores images in PDFs. Advanced parser (Foundation Model-based) can extract some, but quality varies | **High** if docs have diagrams |
| **Table structure** | Default parser flattens tables to text. Advanced parser attempts structure preservation but struggles with complex/nested tables | **High** for data-heavy PDFs |
| **OCR for scanned PDFs** | Not supported by default. Advanced parser with Data Automation can do limited OCR | **High** for scanned docs |
| **Code blocks** | Extracted as plain text, formatting lost. Code-specific context (language, function boundaries) not preserved | **Medium** for technical docs |
| **PDF max size** | 50 MB per file limit | Low for most docs |

### 4.3 Web Crawler Limitations

| Limitation | Detail | Impact on Our Blog |
|------------|--------|-------------------|
| **No JavaScript rendering** | HTTP-only crawler, cannot execute JS | **High** — blog uses Django infinite scroll, only 64/150+ posts indexed |
| **No authentication** | Can't crawl pages behind login | Medium |
| **Depth/scope limits** | Max 25,000 URLs per crawl | Low |
| **No custom extraction** | Can't target specific CSS selectors or DOM elements | Medium |
| **Rate limiting** | Crawl rate is not configurable | Low |

> **Our experience**: The web crawler indexed 64 of 150+ blog posts because older posts are loaded via JavaScript infinite scroll. Post #112 ("Letter to Matilda") was never crawled. Workaround: upload critical posts as S3 documents or add a `sitemap.xml` to the blog.

### 4.4 Confluence Connector Limitations

| Limitation | Detail | Impact |
|------------|--------|--------|
| **Scans entire space** | Cannot filter by folder/parent page during crawl — filters apply during indexing only | Low (extra pages don't hurt) |
| **Filter is regex on titles** | No page ID-based or label-based filtering | Medium |
| **Image attachments skipped** | Diagrams in Confluence pages are not indexed | **High** if diagrams contain info |
| **Nested page hierarchy lost** | Pages are chunked individually, parent-child structure not preserved | Medium |
| **Auth format strict** | Must be exactly `{"username":"...","password":"..."}` — no extra fields | Low (known gotcha) |

### 4.5 Search & Retrieval Limitations

| Limitation | Local RAG Alternative | Impact |
|------------|----------------------|--------|
| **No hybrid search** | Weaviate/Elasticsearch support vector + BM25 keyword search | **High** for exact term matching |
| **No re-ranking** | Cohere Rerank or cross-encoder can boost precision by 10-20% | **High** for quality |
| **No query expansion** | HyDE (Hypothetical Document Embeddings) or multi-query can improve recall | Medium |
| **No custom relevance tuning** | Can't adjust similarity threshold, distance metric, or boost factors per source | Medium |
| **Fixed embedding model** | Titan V2 only — can't use OpenAI, Cohere, or domain-specific models | Medium |

> **Note**: Bedrock KB does support **query reformulation** (rephrasing queries for better retrieval) as a recent feature, but hybrid search and re-ranking are not available.

---

## 5. Side-by-Side Comparison

| Dimension | AWS Bedrock KB (Our Solution) | Local RAG (LangChain + Weaviate) |
|-----------|-------------------------------|----------------------------------|
| **Setup time** | Hours | Days to weeks |
| **Chunking control** | 5 strategies (default → Lambda custom) | Unlimited (any code you write) |
| **Image handling** | Limited (advanced parser only) | Full (OCR, Vision LLM, captions) |
| **Table extraction** | Basic (advanced parser better) | Full (Camelot, Tabula, pdfplumber) |
| **Web crawling** | HTTP-only, no JS rendering | Playwright/Puppeteer, full JS |
| **Confluence integration** | Native connector, 30 min setup | Custom API client, days of work |
| **Hybrid search (vector + BM25)** | ❌ Not available | ✅ Weaviate, Elasticsearch |
| **Re-ranking** | ❌ Not available | ✅ Cohere, cross-encoders |
| **Query expansion** | ✅ Query reformulation | ✅ HyDE, multi-query |
| **Embedding model choice** | Titan V2 or Cohere (Bedrock models only) | Any model (local or API) |
| **Scaling** | Automatic (serverless) | Manual (cluster management) |
| **Cost model** | Pay per API call + storage | Fixed infra + variable compute |
| **Security** | IAM, KMS, VPC — enterprise-grade | Self-managed |
| **Monitoring** | CloudWatch built-in | Custom (Prometheus, Grafana) |
| **Maintenance** | AWS-managed updates | You patch everything |
| **Vendor lock-in** | High (Bedrock APIs, Titan embeddings) | Low (swap any component) |

---

## 6. Output Quality Assessment — Our Solution

Based on real testing with our 3 data sources:

### 6.1 What Works Well (Relevance 45-65%)

| Query Type | Example | Score | Source |
|------------|---------|-------|--------|
| Technical concept lookup | "How does Karpenter work with EKS?" | 47-62% | Blog (web) |
| Confluence doc retrieval | "How does the 2-staged pipeline work?" | 50-57% | Confluence |
| PDF content search | "What is the Azure AD group approach?" | 54% | S3 |
| Infrastructure architecture | "EventBridge and SNS design" | 57% | Confluence |

### 6.2 What Struggles (Relevance < 40%)

| Query Type | Example | Issue | Root Cause |
|------------|---------|-------|------------|
| Personal blog stories | "Letter to Matilda" | Not found | Post #112 not crawled (JS infinite scroll) |
| Cross-document reasoning | "Compare Karpenter vs Cluster Autoscaler across all blog posts" | Partial | Each chunk is independent, no cross-chunk reasoning |
| Exact term matching | "Find all mentions of IRSA" | Misses some | Vector search is semantic, not keyword-exact |
| Image-described content | Diagrams referenced in Confluence | Missing | Images not indexed |
| Table data | Specific rows/columns from PDF tables | Inaccurate | Tables flattened to text during parsing |

### 6.3 Relevance Score Interpretation

| Score Range | Meaning | Action Needed |
|-------------|---------|---------------|
| **60-100%** | Strong match — answer will be accurate | None |
| **45-60%** | Good match — answer mostly correct, may miss details | Accept for most use cases |
| **30-45%** | Weak match — answer may be tangential | Consider re-ranking, query refinement |
| **< 30%** | Poor match — likely irrelevant results | Source may not be indexed, or query needs rephrasing |

Our solution typically returns results in the **45-62% range** for well-indexed content. This is adequate for an internal assistant but would benefit from hybrid search and re-ranking for production.

---

## 7. Production Readiness — Setting Business Expectations

### 7.1 What This Solution CAN Deliver

✅ **"Ask a question, get a sourced answer"** — for text-based documents that are properly indexed, the system reliably retrieves relevant chunks and generates grounded answers with citations.

✅ **Multi-source knowledge** — engineers can ask about Terraform AND blog tutorials AND Confluence design docs in the same conversation.

✅ **Auto-updating** — new S3 uploads auto-index, web/Confluence sync on schedule. No manual re-indexing.

✅ **Audit trail** — every answer includes source URIs and relevance scores. Stakeholders can verify.

✅ **Cost-effective** — serverless pricing means you pay only for what you use. No idle GPU clusters.

### 7.2 What This Solution CANNOT Deliver (Without Enhancement)

❌ **100% recall** — if a document wasn't crawled (JS-rendered pages), or content is in images/tables, it won't be found.

❌ **Exact keyword search** — "Find all documents mentioning IRSA" may miss some because vector search is semantic, not lexical. Hybrid search would fix this.

❌ **Cross-document synthesis** — "Compare the approach in PDF-A with the approach in Confluence-B" is limited because the LLM sees individual chunks, not full documents.

❌ **Image/diagram understanding** — architecture diagrams, flowcharts, and screenshots in docs are invisible to the system.

❌ **Real-time data** — the KB is as fresh as the last sync. Default is daily for web/Confluence. Not suitable for "what happened in the last 5 minutes."

### 7.3 Quality Improvement Roadmap

If moving to production, here's what would improve output quality, in priority order:

| Priority | Enhancement | Effort | Quality Impact |
|----------|------------|--------|---------------|
| **P1** | Switch to **Semantic Chunking** in Bedrock | 1 hour (Terraform change) | +10-15% relevance for structured docs |
| **P1** | Add **sitemap.xml** to blog | 2 hours | Fixes JS crawling gap, +30-50 more posts indexed |
| **P2** | Enable **query reformulation** in Bedrock | 1 hour | Better retrieval for ambiguous queries |
| **P2** | Use **Advanced Parser** (Foundation Model) for PDFs | 2 hours + cost increase | Better table/image extraction |
| **P3** | Add **Custom Lambda chunking** for PDFs with tables | 8-16 hours | Full table structure preservation |
| **P3** | Implement **re-ranking** via post-retrieval Lambda | 8-16 hours | +10-20% precision improvement |
| **P4** | Switch to **hybrid search** (requires custom OpenSearch config) | 16-24 hours | Exact keyword + semantic search combined |
| **P4** | Add **multi-query retrieval** in agent code | 4-8 hours | Better recall for complex questions |

### 7.4 The Honest Summary for Stakeholders

> **"This AWS managed RAG solution gets you to 80% quality with 20% of the effort of building a custom pipeline. The last 20% of quality (hybrid search, re-ranking, image understanding, perfect table extraction) requires either switching to Bedrock's advanced features (moderate effort) or building custom components (significant effort). For an internal platform assistant answering questions about text-based documentation, 80% quality with full source citations is a strong starting point."**

---

## 8. Decision Framework: When to Use Which

### Use AWS Bedrock KB When:
- ✅ Documents are primarily **text-based** (markdown, HTML, simple PDFs)
- ✅ You need **multi-source integration** (S3 + Confluence + web) quickly
- ✅ Team is **small** (1-3 engineers) and can't afford dedicated ML/infra ops
- ✅ Content volume is **moderate** (< 50,000 documents)
- ✅ **Time-to-market** matters more than perfect retrieval quality
- ✅ Enterprise **security/compliance** is non-negotiable (IAM, KMS, VPC)

### Build Local/Custom RAG When:
- ✅ Documents contain **critical images, diagrams, or complex tables**
- ✅ You need **hybrid search** (vector + keyword) for exact matching
- ✅ **Re-ranking** quality improvement is essential for production SLA
- ✅ You need **custom embedding models** (domain-specific, multilingual)
- ✅ Sources require **JavaScript rendering** or authenticated crawling
- ✅ Team has **dedicated ML engineers** who can maintain the pipeline
- ✅ You want **zero vendor lock-in**

### Hybrid Approach (Best of Both):
- Use Bedrock KB for **ingestion and basic retrieval** (saves 80% of pipeline work)
- Add a **post-retrieval re-ranking Lambda** for quality boost
- Use **Custom Lambda chunking** for complex documents
- Add **sitemap.xml** or pre-render tools for JS-heavy web sources
- Supplement with **S3 manual uploads** for content the crawler can't reach

---

## 9. Appendix: RAG Chunking Strategy Deep Dive

For engineers who want to understand what they're giving up (or could configure) in Bedrock:

### Industry-Standard Chunking Strategies

| Strategy | How It Works | Retrieval Accuracy | Cost | Production Default? |
|----------|-------------|-------------------|------|-------------------|
| **Fixed Size** | N tokens, M% overlap | Low-Medium | Low | No (prototype only) |
| **Sentence-Level** | Split at sentence boundaries | Medium | Medium | Rarely |
| **Recursive** | Headers → paragraphs → sentences hierarchy, 512 tokens + 10-20% overlap | **High** | Low | **Yes (LangChain default)** |
| **Semantic** | NLP-based topic boundary detection | **High** (specialized) | High | Yes (with budget) |
| **Hierarchical** | Parent/child chunks for multi-level context | High | Medium | For structured docs |

### Bedrock Default vs Industry Best Practice

| Aspect | Bedrock Default | Industry Best Practice |
|--------|----------------|----------------------|
| Chunk size | ~300 tokens | 256-512 tokens |
| Overlap | None | 10-25% |
| Strategy | Sentence-preserving fixed | Recursive with hierarchy |
| Embedding | Titan V2 (1024d) | Domain-tuned or OpenAI Ada |
| Search | Pure vector (cosine similarity) | Hybrid (vector + BM25) |
| Re-ranking | None | Cross-encoder or Cohere |

**Gap analysis**: Our default Bedrock config is ~1 tier below industry best practice. Switching to **Semantic chunking** or **Fixed Size with overlap** in Terraform closes most of this gap without any code changes.

### Recommended Terraform Change (When Ready)

```hcl
# In bedrock-kb.tf, add to each data source:
vector_ingestion_configuration {
  chunking_configuration {
    chunking_strategy = "FIXED_SIZE"
    fixed_size_chunking_configuration {
      max_tokens      = 512
      overlap_percentage = 15
    }
  }
}
```

Or for semantic chunking:
```hcl
vector_ingestion_configuration {
  chunking_configuration {
    chunking_strategy = "SEMANTIC"
    semantic_chunking_configuration {
      max_tokens          = 512
      buffer_size         = 0
      breakpoint_percentile_threshold = 95
    }
  }
}
```

After changing, re-sync all data sources to re-chunk and re-index existing documents.

---

*Last updated: 2026-03-26 — Based on real deployment experience with Platform Health Insight Assistant on AWS ECS.*
