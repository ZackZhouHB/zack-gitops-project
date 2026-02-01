# Stage 4: Production RAG System - New Design

> **Objective:** Enhance rag-v1 to production-grade with complex source support  
> **Base:** Existing rag-v1 backend + local AI infrastructure  
> **Created:** 2026-02-01

---

## Infrastructure (What We Have)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         EXISTING INFRASTRUCTURE                              │
│                                                                              │
│  Minikube Cluster (ai-platform namespace)                                   │
│  ├── vLLM (GPU) ────────── Qwen2.5-3B, generation + reranking              │
│  ├── Weaviate ──────────── Vector DB, hybrid search ready                   │
│  ├── AI Gateway ────────── Routing, /v1/rag/* endpoints                     │
│  └── rag-backend ───────── Stage 3 simplified (TO BE ENHANCED)              │
│                                                                              │
│  Minikube Cluster (monitoring namespace)                                    │
│  ├── Prometheus ────────── Metrics collection                               │
│  └── Grafana ───────────── Dashboards                                       │
│                                                                              │
│  External                                                                    │
│  ├── Ollama (WSL) ──────── nomic-embed-text (768 dim)                       │
│  └── Bedrock (AWS) ─────── Claude (fallback), Titan (embeddings fallback)   │
│                                                                              │
│  Code Base                                                                   │
│  └── mlops/rag-v1 ──────── Production features to integrate                 │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Complex Input Sources

### Source Types & Challenges

| Source | Challenges | Chunking Strategy |
|--------|------------|-------------------|
| **PDF (long)** | Page breaks, headers/footers, multi-column | Page-aware, remove noise |
| **PDF (images/diagrams)** | Text extraction misses visual info | OCR + image captioning |
| **Markdown** | Code blocks, headers, lists | Structure-aware, preserve code |
| **Word (.docx)** | Styles, tables, embedded images | Paragraph-based, table handling |
| **PowerPoint (.pptx)** | Slides, speaker notes, images | Slide-as-chunk, notes extraction |
| **Excel (.xlsx)** | Tables, sheets, formulas | Row/column context, sheet metadata |
| **Jira** | Issues, comments, attachments | Issue-as-document, link context |
| **Confluence** | Pages, hierarchy, macros | Page-aware, preserve structure |
| **ServiceNow** | Tickets, KB articles, workflows | Article extraction, metadata |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PRODUCTION RAG ARCHITECTURE                               │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                         INGESTION PIPELINE                             │  │
│  │                                                                        │  │
│  │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌───────────┐ │  │
│  │  │   Source    │   │   Loader    │   │  Chunker    │   │  Embedder │ │  │
│  │  │  Connector  │──▶│  (per type) │──▶│ (strategy)  │──▶│  (Ollama) │ │  │
│  │  └─────────────┘   └─────────────┘   └─────────────┘   └─────┬─────┘ │  │
│  │        │                                                      │       │  │
│  │        │ Sources:                                             ▼       │  │
│  │        │ • File Upload (PDF, MD, Office)              ┌───────────┐  │  │
│  │        │ • Jira API                                   │ Weaviate  │  │  │
│  │        │ • Confluence API                             │ (store)   │  │  │
│  │        │ • ServiceNow API                             └───────────┘  │  │
│  │                                                                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                         RETRIEVAL PIPELINE                             │  │
│  │                                                                        │  │
│  │  ┌─────────┐   ┌──────────────┐   ┌──────────┐   ┌─────────────────┐ │  │
│  │  │  Query  │──▶│   Hybrid     │──▶│ Reranker │──▶│    Generator    │ │  │
│  │  │         │   │   Search     │   │  (vLLM)  │   │ (vLLM/Bedrock)  │ │  │
│  │  └─────────┘   │              │   └──────────┘   └────────┬────────┘ │  │
│  │                │ • Vector     │                           │          │  │
│  │                │ • BM25       │                           ▼          │  │
│  │                │ • Hybrid α   │                    ┌─────────────┐   │  │
│  │                └──────────────┘                    │  Evaluator  │   │  │
│  │                                                    │  (RAGAS)    │   │  │
│  │                                                    └─────────────┘   │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                         OBSERVABILITY                                  │  │
│  │                                                                        │  │
│  │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐                  │  │
│  │  │   Tracing   │   │   Metrics   │   │   Logging   │                  │  │
│  │  │ (spans per  │   │ (Prometheus)│   │ (structured)│                  │  │
│  │  │  pipeline)  │   │             │   │             │                  │  │
│  │  └──────┬──────┘   └──────┬──────┘   └──────┬──────┘                  │  │
│  │         └─────────────────┴─────────────────┘                         │  │
│  │                           │                                            │  │
│  │                           ▼                                            │  │
│  │                    ┌─────────────┐                                     │  │
│  │                    │   Grafana   │                                     │  │
│  │                    │  Dashboard  │                                     │  │
│  │                    └─────────────┘                                     │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Design

### 1. Source Connectors

```python
# connectors/base.py
class BaseConnector:
    """Abstract base for all source connectors"""
    async def fetch(self) -> List[RawDocument]
    async def sync(self, since: datetime) -> List[RawDocument]  # Incremental
    
# connectors/file.py
class FileConnector(BaseConnector):
    """Handles: PDF, Markdown, Word, PowerPoint, Excel"""
    
# connectors/jira.py
class JiraConnector(BaseConnector):
    """Fetches issues, comments, attachments from Jira API"""
    
# connectors/confluence.py
class ConfluenceConnector(BaseConnector):
    """Fetches pages, spaces from Confluence API"""
    
# connectors/servicenow.py
class ServiceNowConnector(BaseConnector):
    """Fetches KB articles, incidents from ServiceNow API"""
```

### 2. Document Loaders (Per Type)

```python
# loaders/pdf.py
class PDFLoader:
    """
    Handles:
    - Text extraction (pdfplumber/PyMuPDF)
    - Image extraction
    - Table detection
    - OCR for scanned pages (optional)
    """
    def load(self, file) -> Document:
        # Extract text with page numbers
        # Extract images, generate captions (optional)
        # Detect and extract tables
        
# loaders/markdown.py
class MarkdownLoader:
    """
    Handles:
    - Preserve code blocks with language
    - Extract headers for hierarchy
    - Handle embedded images
    """
    
# loaders/office.py
class WordLoader:
    """Extract paragraphs, tables, images from .docx"""
    
class PowerPointLoader:
    """Extract slides, speaker notes, images from .pptx"""
    
class ExcelLoader:
    """Extract sheets, tables with context from .xlsx"""
```

### 3. Chunking Strategies

```python
# chunker/strategies.py

class ChunkStrategy(Enum):
    FIXED = "fixed"              # Simple fixed size
    RECURSIVE = "recursive"      # LangChain recursive
    MARKDOWN = "markdown"        # Header-aware for MD
    SEMANTIC = "semantic"        # Sentence-based boundaries
    PAGE = "page"                # PDF page-based
    SLIDE = "slide"              # PPT slide-based
    ROW = "row"                  # Excel row-based

# chunker/chunker.py
class SmartChunker:
    """Selects strategy based on document type"""
    
    STRATEGY_MAP = {
        "pdf": ChunkStrategy.PAGE,
        "md": ChunkStrategy.MARKDOWN,
        "docx": ChunkStrategy.RECURSIVE,
        "pptx": ChunkStrategy.SLIDE,
        "xlsx": ChunkStrategy.ROW,
        "jira": ChunkStrategy.FIXED,      # Issues are already bounded
        "confluence": ChunkStrategy.MARKDOWN,
    }
    
    def chunk(self, doc: Document) -> List[Chunk]:
        strategy = self.STRATEGY_MAP.get(doc.format, ChunkStrategy.RECURSIVE)
        return self._apply_strategy(doc, strategy)
```

### 4. Chunk Metadata (Critical for Retrieval)

```python
@dataclass
class Chunk:
    content: str
    
    # Source tracking
    source_id: str           # Unique doc identifier
    source_type: str         # pdf, md, jira, etc.
    source_url: Optional[str]  # Link back to original
    
    # Position
    chunk_id: int
    total_chunks: int
    page_number: Optional[int]   # For PDF
    slide_number: Optional[int]  # For PPT
    section_header: Optional[str]  # For MD/Confluence
    
    # Content type
    content_type: str        # text, code, table, image_caption
    language: Optional[str]  # For code blocks
    
    # Access control
    allowed_groups: List[str]
    
    # Timestamps
    created_at: datetime
    source_updated_at: datetime
```

### 5. Hybrid Retrieval

```python
# retriever/hybrid.py
class HybridRetriever:
    """
    Combines:
    - Vector search (semantic similarity)
    - BM25 search (keyword matching)
    - Configurable alpha blending
    """
    
    def search(
        self,
        query: str,
        top_k: int = 10,
        alpha: float = 0.5,      # 0=keyword, 1=vector, 0.5=balanced
        source_filter: Optional[str] = None,
        content_type_filter: Optional[str] = None,
    ) -> List[Chunk]:
        pass

# retriever/reranker.py
class LLMReranker:
    """
    Uses vLLM to score relevance of retrieved chunks.
    Two-stage: retrieve top-20, rerank to top-5.
    """
    
    def rerank(
        self,
        query: str,
        chunks: List[Chunk],
        top_k: int = 5,
        backend: str = "vllm"  # or "bedrock"
    ) -> List[Chunk]:
        pass
```

### 6. Tracing

```python
# tracing/tracer.py
class RAGTracer:
    """
    Traces each pipeline stage with timing and metadata.
    Exports to Prometheus metrics + structured logs.
    """
    
    @dataclass
    class Span:
        name: str
        start_time: float
        end_time: float
        metadata: Dict
        
    def trace_ingestion(self, doc_id: str) -> ContextManager:
        """Trace: load → chunk → embed → store"""
        
    def trace_retrieval(self, query_id: str) -> ContextManager:
        """Trace: embed_query → search → rerank → generate"""
        
    def get_metrics(self) -> Dict:
        """
        Returns:
        - ingestion_latency_seconds (by source_type)
        - chunks_per_document (by source_type)
        - retrieval_latency_seconds (by stage)
        - rerank_latency_seconds
        - generation_latency_seconds
        """
```

### 7. Evaluation Framework

```python
# evaluation/metrics.py
class RAGEvaluator:
    """
    RAGAS-style metrics for RAG quality.
    Can use vLLM or Bedrock for LLM-as-judge.
    """
    
    def evaluate_single(
        self,
        question: str,
        answer: str,
        contexts: List[str],
        ground_truth: Optional[str] = None
    ) -> EvaluationResult:
        """
        Returns:
        - faithfulness: Is answer grounded in context? (0-1)
        - relevance: Does answer address question? (0-1)
        - context_precision: Are retrieved docs relevant? (0-1)
        - context_recall: Did we get all relevant docs? (0-1, needs ground_truth)
        """
        
    def evaluate_batch(
        self,
        test_suite: List[TestCase]
    ) -> BatchEvaluationResult:
        """Run evaluation on test suite, return aggregates"""
        
    def compare_strategies(
        self,
        test_suite: List[TestCase],
        strategies: List[str]  # e.g., ["vector", "hybrid", "hybrid+rerank"]
    ) -> ComparisonResult:
        """A/B test different retrieval strategies"""

# evaluation/test_suite.py
@dataclass
class TestCase:
    question: str
    expected_answer: Optional[str]       # For recall
    expected_sources: Optional[List[str]]  # Which docs should be retrieved
    expected_keywords: Optional[List[str]]  # Keywords that should appear
    
class TestSuiteBuilder:
    """Generate test cases from documents"""
    
    def from_documents(self, docs: List[Document], num_questions: int = 20) -> List[TestCase]:
        """Use LLM to generate Q&A pairs from documents"""
```

---

## Weaviate Schema (Enhanced)

```python
SCHEMA = {
    "class": "Document",
    "vectorizer": "none",
    "properties": [
        # Content
        {"name": "content", "dataType": ["text"]},
        {"name": "content_type", "dataType": ["string"]},  # text, code, table, image_caption
        {"name": "language", "dataType": ["string"]},      # For code blocks
        
        # Source tracking
        {"name": "source_id", "dataType": ["string"]},
        {"name": "source_type", "dataType": ["string"]},   # pdf, md, jira, confluence, etc.
        {"name": "source_url", "dataType": ["string"]},
        
        # Position
        {"name": "chunk_id", "dataType": ["int"]},
        {"name": "total_chunks", "dataType": ["int"]},
        {"name": "page_number", "dataType": ["int"]},
        {"name": "slide_number", "dataType": ["int"]},
        {"name": "section_header", "dataType": ["string"]},
        
        # Access control
        {"name": "allowed_groups", "dataType": ["text[]"]},
        
        # Timestamps
        {"name": "created_at", "dataType": ["date"]},
        {"name": "source_updated_at", "dataType": ["date"]},
    ],
    # Enable BM25 for hybrid search
    "invertedIndexConfig": {
        "bm25": {"b": 0.75, "k1": 1.2}
    }
}
```

---

## API Endpoints

```yaml
# Ingestion
POST /v1/rag/upload              # File upload (PDF, MD, Office)
POST /v1/rag/sync/jira           # Sync from Jira
POST /v1/rag/sync/confluence     # Sync from Confluence
POST /v1/rag/sync/servicenow     # Sync from ServiceNow

# Query
POST /v1/rag/query               # Standard query
  - search_type: vector | keyword | hybrid
  - alpha: 0.0-1.0 (for hybrid)
  - use_rerank: bool
  - source_filter: string
  - content_type_filter: string

# Management
GET  /v1/rag/documents           # List all documents
GET  /v1/rag/documents/{id}      # Get document details
DELETE /v1/rag/documents/{id}    # Delete document

# Evaluation
POST /v1/rag/evaluate            # Run evaluation on test cases
GET  /v1/rag/evaluate/results    # Get evaluation history
POST /v1/rag/evaluate/compare    # Compare strategies

# Observability
GET  /metrics                    # Prometheus metrics
GET  /v1/rag/traces/{query_id}   # Get trace for a query
```

---

## Metrics (Prometheus)

```python
# Ingestion metrics
rag_ingestion_total              # Counter: docs ingested by source_type
rag_ingestion_latency_seconds    # Histogram: ingestion time by source_type
rag_chunks_per_document          # Histogram: chunks created per doc

# Retrieval metrics
rag_query_total                  # Counter: queries by search_type
rag_query_latency_seconds        # Histogram: total query time
rag_search_latency_seconds       # Histogram: search stage only
rag_rerank_latency_seconds       # Histogram: rerank stage only
rag_generation_latency_seconds   # Histogram: LLM generation only

# Quality metrics (from evaluation)
rag_faithfulness_score           # Gauge: latest faithfulness
rag_relevance_score              # Gauge: latest relevance
rag_context_precision_score      # Gauge: latest context precision

# Resource metrics
rag_embedding_tokens_total       # Counter: tokens sent to embedder
rag_generation_tokens_total      # Counter: tokens sent to LLM
```

---

## Implementation Phases

### Phase 1: Enhanced Chunking (2-3 hours)
- [ ] Integrate LangChain splitters (Recursive, Markdown)
- [ ] Add PDF loader with page awareness
- [ ] Add Office loaders (Word, PPT, Excel)
- [ ] Smart chunker with strategy selection
- [ ] Enhanced metadata in Weaviate schema

### Phase 2: Hybrid Retrieval (2 hours)
- [ ] BM25 search implementation
- [ ] Hybrid search with alpha tuning
- [ ] LLM reranker (vLLM-based)
- [ ] Source/content type filtering

### Phase 3: Evaluation Framework (2-3 hours)
- [ ] RAGAS-style metrics implementation
- [ ] Test suite builder (LLM-generated Q&A)
- [ ] Batch evaluation endpoint
- [ ] Strategy comparison tool

### Phase 4: Enterprise Connectors (3-4 hours)
- [ ] Jira connector (REST API)
- [ ] Confluence connector (REST API)
- [ ] ServiceNow connector (REST API)
- [ ] Incremental sync support

### Phase 5: Observability (1-2 hours)
- [ ] Tracing implementation
- [ ] Enhanced Prometheus metrics
- [ ] Grafana dashboard updates
- [ ] Structured logging

---

## File Structure

```
stage4/
├── README.md
├── progress.md
├── commands-log.md
├── rag-tooling-landscape.md
├── new-design.md                    # This file
├── evaluation-results.md            # Before/after comparison
│
├── src/rag-enhanced/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py                  # FastAPI app
│       ├── config.py                # Settings
│       │
│       ├── connectors/              # Source connectors
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── file.py
│       │   ├── jira.py
│       │   ├── confluence.py
│       │   └── servicenow.py
│       │
│       ├── loaders/                 # Document loaders
│       │   ├── __init__.py
│       │   ├── pdf.py
│       │   ├── markdown.py
│       │   └── office.py
│       │
│       ├── chunker/                 # Chunking strategies
│       │   ├── __init__.py
│       │   ├── strategies.py
│       │   └── chunker.py
│       │
│       ├── retriever/               # Retrieval components
│       │   ├── __init__.py
│       │   ├── hybrid.py
│       │   └── reranker.py
│       │
│       ├── evaluation/              # Evaluation framework
│       │   ├── __init__.py
│       │   ├── metrics.py
│       │   └── test_suite.py
│       │
│       └── tracing/                 # Observability
│           ├── __init__.py
│           └── tracer.py
│
└── k8s-manifests/
    └── rag-enhanced.yaml
```

---

## Dependencies

```txt
# requirements.txt

# Core
fastapi==0.109.0
uvicorn==0.27.0
pydantic==2.5.0
pydantic-settings==2.1.0

# Vector DB
weaviate-client==4.4.0

# LLM clients
httpx==0.26.0
boto3==1.34.0

# Document processing
langchain==0.1.0
langchain-text-splitters==0.0.1
pdfplumber==0.10.0
python-docx==1.1.0
python-pptx==0.6.23
openpyxl==3.1.2
markdown==3.5.0

# Enterprise connectors
atlassian-python-api==3.41.0    # Jira + Confluence
pysnow==0.7.17                  # ServiceNow

# Observability
prometheus-client==0.19.0

# Evaluation
# (custom implementation, no external RAGAS dependency)
```

---

## Success Criteria

| Metric | Target |
|--------|--------|
| Faithfulness | > 0.85 |
| Answer Relevance | > 0.80 |
| Context Precision | > 0.75 |
| PDF ingestion | Works with 100+ page docs |
| Office support | Word, PPT, Excel all working |
| Enterprise connectors | At least Jira + Confluence |
| Hybrid search | Measurable improvement over vector-only |
| Reranking | Measurable improvement in precision |
| Tracing | Full pipeline visibility in Grafana |
