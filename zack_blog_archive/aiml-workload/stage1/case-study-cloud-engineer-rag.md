# Case Study: Cloud Engineer Knowledge Base RAG

> Real-world RAG project using actual enterprise data sources

---

## The Problem

As a Cloud Engineer, you're the "human search engine" for:
- Legacy application knowledge (no docs, tribal knowledge)
- LLD documents (PDFs scattered in SharePoint, laptops)
- Incident history (ServiceNow - past fixes and resolutions)
- Design docs (Jira/Confluence - buried in folder hierarchies)

**Current workflow:**
```
Someone asks question
    → You try to remember
    → Ask other engineers (if they have time)
    → Search SharePoint (maybe find it)
    → Search ServiceNow (keyword guessing)
    → Search Confluence (folder diving)
    → 30 min - 2 hours later... maybe have answer
```

**Target workflow:**
```
Someone asks question
    → Query RAG system
    → Get answer with source citations
    → 30 seconds
```

---

## Data Sources Analysis

| Source | Data Type | Access Method | Volume (Est.) | Priority |
|--------|-----------|---------------|---------------|----------|
| **SharePoint** | LLD PDFs, design docs | Graph API or manual export | 100-500 docs | 🔴 High |
| **ServiceNow** | Incidents, resolutions | REST API or CSV export | 1000+ tickets | 🔴 High |
| **Confluence** | Design docs, runbooks | REST API or export | 200-1000 pages | 🔴 High |
| **Jira** | Tickets with context | REST API | 500+ tickets | 🟡 Medium |
| **Local files** | PDFs, docs on laptops | Manual collection | 50-200 docs | 🟡 Medium |
| **Email** | Incident threads | Complex (privacy) | Skip for now | 🟢 Low |

---

## Project Phases

### Phase 1: Local POC (Week 1-2) ← START HERE
**Goal:** Prove the concept works with a subset of your data

```
Your Laptop
├── sample_docs/
│   ├── lld_samples/          # 10-20 LLD PDFs (manually collected)
│   ├── servicenow_exports/   # CSV export of 100 incidents
│   └── confluence_exports/   # HTML/PDF export of key pages
│
├── rag_poc/
│   ├── ingest.py            # Load and chunk documents
│   ├── embed.py             # Generate embeddings
│   ├── search.py            # Query interface
│   └── evaluate.py          # Test with real questions
```

**Tech Stack (Local):**
- Vector DB: pgvector (Docker) or Qdrant (Docker)
- Embeddings: Bedrock Titan or local (nomic-embed-text via Ollama)
- LLM: Bedrock Claude or local (Llama via Ollama)
- Framework: LangChain or raw Python

**Success Criteria:**
- Can answer 5 real questions you've been asked before
- Answers include source citations
- Response time < 10 seconds

---

### Phase 2: Managed RAG Comparison (Week 2-3)
**Goal:** Compare Bedrock Knowledge Base with your custom solution

```
Same data → Bedrock Knowledge Base
         → Your custom RAG

Compare:
- Answer quality
- Citation accuracy  
- Setup effort
- Cost
- Limitations hit
```

**What you'll learn:**
- When managed RAG is "good enough"
- What limitations you hit with your specific data
- Cost comparison with real numbers

---

### Phase 3: Production-Ready Custom RAG (Week 3-4)
**Goal:** Build a solution you could actually deploy

**Add enterprise features:**
- Hybrid search (keyword + vector) - important for incident IDs, error codes
- Incremental updates (new incidents, new docs)
- Source tracking (which doc, which page)
- Basic auth (who can query)

**Tech Stack (Production):**
- Vector DB: OpenSearch or pgvector on RDS
- Embeddings: Bedrock Titan
- LLM: Bedrock Claude
- API: FastAPI
- Frontend: Streamlit (simple) or Slack bot (practical)

---

### Phase 4: Data Pipeline (Month 2)
**Goal:** Automate data ingestion from live sources

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ SharePoint  │────▶│             │     │             │
├─────────────┤     │   Lambda    │────▶│  Vector DB  │
│ ServiceNow  │────▶│  (ingest)   │     │             │
├─────────────┤     │             │     │             │
│ Confluence  │────▶│             │     │             │
└─────────────┘     └─────────────┘     └─────────────┘
        │                                      │
        │         EventBridge (schedule)       │
        └──────────────────────────────────────┘
                   Daily/Weekly sync
```

---

## Phase 1 Detailed Plan (This Week)

### Step 1: Collect Sample Data (Today/Tomorrow)

**From SharePoint (manual for POC):**
```
1. Download 10-20 LLD PDFs you know are useful
2. Save to: ~/rag-project/data/lld/
3. Note: Which systems do these cover?
```

**From ServiceNow (export):**
```
1. Export last 6 months of incidents (CSV)
   - Fields: number, short_description, description, resolution_notes, category
2. Save to: ~/rag-project/data/servicenow/incidents.csv
3. Note: ~100-500 incidents is enough for POC
```

**From Confluence (export):**
```
1. Export key spaces as HTML or PDF
   - Focus on: runbooks, architecture docs, troubleshooting guides
2. Save to: ~/rag-project/data/confluence/
3. Note: 20-50 pages is enough for POC
```

### Step 2: Build Ingestion Pipeline (Day 2-3)

```python
# Pseudocode - we'll build this together

# 1. Load documents
docs = []
docs += load_pdfs("data/lld/")
docs += load_csv_as_docs("data/servicenow/incidents.csv")
docs += load_html("data/confluence/")

# 2. Chunk with source tracking
chunks = []
for doc in docs:
    chunks += chunk_document(doc, 
        chunk_size=500,
        overlap=50,
        metadata={"source": doc.source, "type": doc.type}
    )

# 3. Embed
embeddings = embed_chunks(chunks, model="titan-embed")

# 4. Store
vector_db.upsert(chunks, embeddings)
```

### Step 3: Build Query Interface (Day 3-4)

```python
# Pseudocode

def query(question: str) -> Answer:
    # 1. Embed question
    q_embedding = embed(question)
    
    # 2. Retrieve relevant chunks
    chunks = vector_db.search(q_embedding, top_k=5)
    
    # 3. Generate answer with citations
    context = format_chunks_with_sources(chunks)
    answer = llm.generate(
        prompt=f"Answer based on context:\n{context}\n\nQuestion: {question}"
    )
    
    return Answer(text=answer, sources=chunks)
```

### Step 4: Test with Real Questions (Day 4-5)

**Prepare test questions (things you've been asked):**
```
1. "How do we connect to the XYZ database in prod?"
2. "What was the fix for the ABC service outage last month?"
3. "Where is the network diagram for the DEF application?"
4. "How do we restart the GHI service?"
5. "What's the escalation path for PQR issues?"
```

**Evaluate:**
- Did it find the right source?
- Is the answer accurate?
- Are citations correct?

---

## Folder Structure for Project

```
~/rag-project/
├── data/
│   ├── lld/                    # PDF exports from SharePoint
│   ├── servicenow/             # CSV exports
│   ├── confluence/             # HTML/PDF exports
│   └── README.md               # Data source notes
│
├── src/
│   ├── ingest/
│   │   ├── pdf_loader.py
│   │   ├── csv_loader.py
│   │   ├── html_loader.py
│   │   └── chunker.py
│   │
│   ├── embed/
│   │   ├── bedrock_embedder.py
│   │   └── local_embedder.py   # Ollama fallback
│   │
│   ├── store/
│   │   ├── pgvector_store.py
│   │   └── qdrant_store.py
│   │
│   ├── retrieve/
│   │   ├── vector_search.py
│   │   ├── hybrid_search.py    # Phase 3
│   │   └── reranker.py         # Phase 3
│   │
│   ├── generate/
│   │   ├── bedrock_llm.py
│   │   └── local_llm.py        # Ollama fallback
│   │
│   └── api/
│       ├── main.py             # FastAPI
│       └── slack_bot.py        # Optional
│
├── notebooks/
│   ├── 01_data_exploration.ipynb
│   ├── 02_chunking_experiments.ipynb
│   ├── 03_retrieval_evaluation.ipynb
│   └── 04_bedrock_kb_comparison.ipynb
│
├── tests/
│   ├── test_questions.json     # Your real questions
│   └── evaluate.py
│
├── docker-compose.yml          # pgvector + qdrant
├── requirements.txt
└── README.md
```

---

## What Makes This Different from Tutorials

| Tutorial RAG | Your RAG |
|--------------|----------|
| Clean markdown files | Messy PDFs, CSVs, HTML |
| Single source | Multiple sources (SharePoint, ServiceNow, Confluence) |
| Generic questions | Your actual questions |
| No evaluation | Test against real scenarios |
| No comparison | Managed vs Custom comparison |
| Toy scale | Real document volume |

---

## Skills You'll Gain

| Skill | Where Applied |
|-------|---------------|
| Document parsing (PDF, CSV, HTML) | Phase 1 |
| Chunking strategies | Phase 1 |
| Embedding models | Phase 1 |
| Vector databases | Phase 1 |
| Bedrock Knowledge Base | Phase 2 |
| Hybrid search | Phase 3 |
| Data pipelines | Phase 4 |
| Cost optimization | Throughout |
| Evaluation metrics | Throughout |

---

## Interview Story

> "I built a RAG system to solve a real problem at work - our team was spending hours searching for information across SharePoint, ServiceNow, and Confluence. I compared Bedrock Knowledge Base with a custom solution, found that [specific limitation], and built a hybrid search system that reduced our average query time from 30 minutes to 30 seconds. The system now handles [X] documents and [Y] queries per day."

This is 10x more compelling than "I followed a LangChain tutorial."

---

## Next Steps

1. **Today:** Finish Bedrock fundamentals (done ✅)
2. **Tonight/Tomorrow:** Collect sample data from your sources
3. **This weekend:** Build Phase 1 POC on desktop (GPU for local models)
4. **Next week:** Phase 2 - Bedrock KB comparison

Ready to start collecting your sample data, or want to set up the project structure first?
