# Custom RAG for Cloud Engineering Knowledge Base

> Your personal RAG system for LLD docs, ServiceNow incidents, and Confluence pages

## Quick Start

### 1. Start the database

```bash
cd custom-rag
docker-compose up -d
```

This starts:
- PostgreSQL with pgvector (port 5432)
- Qdrant (port 6333) - optional alternative

### 2. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### 3. Add your data

```
data/
├── lld/              # Drop your LLD PDFs here
├── servicenow/       # Export incidents as CSV
└── confluence/       # Export pages as MD or HTML
```

### 4. Ingest documents

```bash
python -m src.ingest.main --data-dir ./data --clear
```

### 5. Query

```python
from src.retrieve.pipeline import RAGPipeline

pipeline = RAGPipeline()
response = pipeline.query("How do I restart an EKS deployment?")

print(response.answer)
for citation in response.citations:
    print(f"  Source: {citation.source_path}")
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     CUSTOM RAG ARCHITECTURE                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   DATA SOURCES              INGESTION              STORAGE      │
│   ┌─────────┐              ┌─────────┐           ┌──────────┐   │
│   │   LLD   │──────────────│ Loaders │           │          │   │
│   │  PDFs   │              │ (PDF,   │           │ pgvector │   │
│   └─────────┘              │  CSV,   │           │          │   │
│   ┌─────────┐              │  MD,    │──────────▶│ Documents│   │
│   │ServiceNow│─────────────│  HTML)  │           │ + Chunks │   │
│   │  CSV    │              └────┬────┘           │ + Vectors│   │
│   └─────────┘                   │                │          │   │
│   ┌─────────┐              ┌────▼────┐           └──────────┘   │
│   │Confluence│─────────────│ Chunker │                 │        │
│   │  MD/HTML│              │(semantic│                 │        │
│   └─────────┘              │ /fixed) │                 │        │
│                            └────┬────┘                 │        │
│                                 │                      │        │
│                            ┌────▼────┐                 │        │
│                            │Embedder │                 │        │
│                            │(Bedrock │─────────────────┘        │
│                            │ Titan)  │                          │
│                            └─────────┘                          │
│                                                                 │
│   QUERY FLOW                                                    │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                                                         │   │
│   │  Question ──▶ Embed ──▶ Hybrid Search ──▶ Context ──▶   │   │
│   │                         (vector+keyword)                │   │
│   │                                                         │   │
│   │  ──▶ Bedrock Claude ──▶ Answer + Citations              │   │
│   │                                                         │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
custom-rag/
├── docker-compose.yml      # pgvector + qdrant
├── init.sql                # Database schema
├── requirements.txt        # Python dependencies
├── README.md               # This file
│
├── data/                   # Your documents
│   ├── lld/               # PDF files
│   ├── servicenow/        # CSV exports
│   └── confluence/        # MD/HTML exports
│
├── src/
│   ├── ingest/            # Document loading & chunking
│   │   ├── loaders.py     # PDF, CSV, MD, HTML loaders
│   │   ├── chunker.py     # Chunking strategies
│   │   └── main.py        # Ingestion script
│   │
│   ├── embed/             # Embedding generation
│   │   └── embedder.py    # Bedrock Titan + Ollama
│   │
│   ├── store/             # Vector storage
│   │   └── pgvector_store.py  # PostgreSQL + pgvector
│   │
│   ├── retrieve/          # Query pipeline
│   │   └── pipeline.py    # RAG orchestration
│   │
│   └── api/               # API layer (optional)
│       └── main.py        # FastAPI server
│
├── notebooks/             # Jupyter notebooks for exploration
│
└── tests/                 # Test files
    └── test_questions.json
```

---

## Key Features

### 1. Multiple Document Types
- **PDF**: LLD documents from SharePoint
- **CSV**: ServiceNow incident exports
- **Markdown/HTML**: Confluence pages

### 2. Smart Chunking
- **Semantic chunking** for structured docs (by headers/sections)
- **ServiceNow chunking** preserves incident structure
- **Fixed-size fallback** for unstructured content

### 3. Hybrid Search
- **Vector search**: Semantic similarity ("restart deployment" ≈ "rollout restart")
- **Keyword search**: Exact matches (incident IDs, error codes)
- **Combined**: Best of both worlds

### 4. Citations
- Every answer includes source references
- Links back to original document
- Similarity scores for transparency

---

## Configuration

### Database Connection

```python
store = PgVectorStore(
    host="localhost",
    port=5432,
    database="ragdb",
    user="raguser",
    password="ragpass"
)
```

### Embedding Model

```python
# Bedrock (default, costs ~$0.10 per 1M tokens)
embedder = BedrockEmbedder(profile="default", region="ap-southeast-2")

# Ollama (free, local)
embedder = OllamaEmbedder(model="nomic-embed-text")
```

### LLM Model

```python
pipeline = RAGPipeline(
    llm_model="anthropic.claude-3-haiku-20240307-v1:0"  # Fast, cheap
    # llm_model="anthropic.claude-3-5-sonnet-20241022-v2:0"  # Better quality
)
```

---

## Cost Estimate

| Component | Cost |
|-----------|------|
| Embeddings (Titan, 10K chunks) | ~$0.50 one-time |
| LLM (Haiku, 1000 queries/month) | ~$15/month |
| pgvector (local Docker) | $0 |
| **Total** | **~$15/month** |

Compare to Bedrock KB + OpenSearch: ~$700+/month

---

## Next Steps

1. [ ] Add your real data to `data/` directory
2. [ ] Run ingestion: `python -m src.ingest.main --data-dir ./data`
3. [ ] Test queries in Python or notebook
4. [ ] (Optional) Build Slack bot or web UI
5. [ ] (Optional) Add more data sources (Jira, etc.)
