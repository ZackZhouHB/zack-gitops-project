# Stage 4: Production RAG System - Master Plan (Refined)

> **Objective:** Build demonstrable RAG skills with measurable outcomes  
> **Focus:** High-ROI tasks that tell a compelling interview story  
> **Duration:** 2-3 sessions (~6-8 hours total)  
> **Last Updated:** 2026-02-01

---

## The Goal

Build the story:
> "I built a RAG system that ingests PDFs, Word docs, and Confluence pages. I used RAGAS to measure quality - started at 0.65 faithfulness, improved to 0.85 with hybrid search and better chunking."

---

## Refined Task List (High ROI Only)

### Phase 1: Document Loaders (This Session)
**Goal:** Handle real enterprise documents

| Task | Status | Time | Priority |
|------|--------|------|----------|
| 1.1 PDF Loader (pdfplumber) | ⬜ | 45 min | **MUST** |
| 1.2 Word Loader (python-docx) | ⬜ | 30 min | **MUST** |
| 1.3 Excel Loader (openpyxl) | ⬜ | 30 min | HIGH |
| 1.4 Test with real documents | ⬜ | 30 min | **MUST** |

### Phase 2: Evaluation Baseline (This Session)
**Goal:** Measure current quality with numbers

| Task | Status | Time | Priority |
|------|--------|------|----------|
| 2.1 Create test document set | ⬜ | 20 min | **MUST** |
| 2.2 Generate Q&A test cases | ⬜ | 20 min | **MUST** |
| 2.3 Run baseline evaluation | ⬜ | 20 min | **MUST** |
| 2.4 Document baseline scores | ⬜ | 10 min | **MUST** |

### Phase 3: Confluence Connector (Next Session)
**Goal:** Show enterprise integration capability

| Task | Status | Time | Priority |
|------|--------|------|----------|
| 3.1 Confluence API connector | ⬜ | 1.5 hr | HIGH |
| 3.2 Page extraction + chunking | ⬜ | 30 min | HIGH |
| 3.3 Test with sample space | ⬜ | 30 min | HIGH |

### Phase 4: Final Evaluation & Documentation (Next Session)
**Goal:** Prove improvement with numbers

| Task | Status | Time | Priority |
|------|--------|------|----------|
| 4.1 Run final evaluation | ⬜ | 20 min | **MUST** |
| 4.2 Compare baseline vs final | ⬜ | 15 min | **MUST** |
| 4.3 Write project summary | ⬜ | 1 hr | **MUST** |
| 4.4 Update GitHub README | ⬜ | 30 min | **MUST** |

---

## What We're NOT Doing (Low ROI)

| Skipped | Reason |
|---------|--------|
| Frontend port | Use OpenWebUI/Chainlit instead |
| Auth/sessions | Clients have their own |
| Complex incremental | Most do full re-index |
| PowerPoint loader | Rare use case |
| Jira connector | Confluence is enough to show |
| Production hardening | Over-engineering for demo |

---

## Success Metrics

| Metric | Baseline | Target | Status |
|--------|----------|--------|--------|
| Faithfulness | TBD | > 0.85 | ⬜ |
| Relevance | TBD | > 0.80 | ⬜ |
| Context Precision | TBD | > 0.75 | ⬜ |
| File Types | 1 (txt) | 4 (PDF, Word, Excel, MD) | ⬜ |
| Enterprise Source | 0 | 1 (Confluence) | ⬜ |

---

## The Deliverable

A GitHub project that shows:
1. **Document ingestion** - PDF, Word, Excel, Confluence
2. **Smart chunking** - LangChain with strategy per doc type
3. **Quality retrieval** - Hybrid search + reranking
4. **Measured improvement** - Baseline 0.65 → Final 0.85 (example)
5. **Clear documentation** - README tells the story

---

## Current Progress

### Completed ✅
- [x] Smart chunking (LangChain)
- [x] Hybrid retrieval (vector + BM25)
- [x] LLM reranking
- [x] Evaluation framework
- [x] Deployed to Minikube

### This Session 🔄
- [ ] 1.1 PDF Loader
- [ ] 1.2 Word Loader
- [ ] 1.3 Excel Loader
- [ ] 2.1-2.4 Baseline evaluation

### Next Session ⬜
- [ ] Confluence connector
- [ ] Final evaluation
- [ ] Documentation

---

## How to Resume

1. Check `progress.md` for last completed task
2. Continue from next task in list above
3. Update progress as you complete
4. Focus on **measurable outcomes**

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      PRODUCTION RAG SYSTEM                                   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                         FRONTEND (React)                             │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │    │
│  │  │  Auth    │ │  Chat    │ │  File    │ │  History │ │  Admin   │  │    │
│  │  │  Login   │ │  Interface│ │  Upload  │ │  View    │ │  Panel   │  │    │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                         BACKEND (FastAPI)                            │    │
│  │                                                                      │    │
│  │  ┌─────────────────────────────────────────────────────────────┐   │    │
│  │  │                    INGESTION PIPELINE                        │   │    │
│  │  │                                                              │   │    │
│  │  │  Source → Loader → Chunker → Embedder → Indexer → Weaviate  │   │    │
│  │  │                                                              │   │    │
│  │  │  Loaders:        Chunkers:         Tracking:                │   │    │
│  │  │  • PDF           • Recursive       • doc_id                 │   │    │
│  │  │  • Markdown      • Markdown        • checksum               │   │    │
│  │  │  • Word          • Code            • last_modified          │   │    │
│  │  │  • PowerPoint    • Semantic        • chunk_count            │   │    │
│  │  │  • Excel                                                     │   │    │
│  │  │  • Jira API                                                  │   │    │
│  │  │  • Confluence                                                │   │    │
│  │  └─────────────────────────────────────────────────────────────┘   │    │
│  │                                                                      │    │
│  │  ┌─────────────────────────────────────────────────────────────┐   │    │
│  │  │                    RETRIEVAL PIPELINE                        │   │    │
│  │  │                                                              │   │    │
│  │  │  Query → Embed → Hybrid Search → Rerank → Generate → Eval   │   │    │
│  │  │                                                              │   │    │
│  │  │  Search Types:    Reranking:       Evaluation:              │   │    │
│  │  │  • Vector         • LLM scoring    • Faithfulness           │   │    │
│  │  │  • BM25           • Cross-encoder  • Relevance              │   │    │
│  │  │  • Hybrid (α)                      • Context Precision      │   │    │
│  │  └─────────────────────────────────────────────────────────────┘   │    │
│  │                                                                      │    │
│  │  ┌─────────────────────────────────────────────────────────────┐   │    │
│  │  │                    INCREMENTAL PIPELINE                      │   │    │
│  │  │                                                              │   │    │
│  │  │  Change Detection → Delta Processing → Index Update         │   │    │
│  │  │                                                              │   │    │
│  │  │  • Checksum comparison    • Add new chunks                  │   │    │
│  │  │  • Timestamp tracking     • Remove deleted chunks           │   │    │
│  │  │  • Source sync status     • Update modified chunks          │   │    │
│  │  └─────────────────────────────────────────────────────────────┘   │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                         INFRASTRUCTURE                               │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │    │
│  │  │ Weaviate │ │  vLLM    │ │  Ollama  │ │Prometheus│ │ Grafana  │  │    │
│  │  │ Vector DB│ │  (GPU)   │ │ Embeddings│ │ Metrics  │ │Dashboard │  │    │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Task Breakdown

### Phase 1: Document Loaders (Session 1)
**Goal:** Support all major file types

| Task ID | Task | Status | Est. Time |
|---------|------|--------|-----------|
| 1.1 | PDF Loader (pdfplumber, page-aware) | ⬜ | 1 hr |
| 1.2 | Markdown Loader (preserve code blocks) | ⬜ | 30 min |
| 1.3 | Word Loader (python-docx) | ⬜ | 45 min |
| 1.4 | PowerPoint Loader (python-pptx) | ⬜ | 45 min |
| 1.5 | Excel Loader (openpyxl) | ⬜ | 30 min |
| 1.6 | Test all loaders with sample files | ⬜ | 30 min |

**Deliverable:** All file types can be uploaded and chunked correctly

---

### Phase 2: Initial Indexing Pipeline (Session 2)
**Goal:** Robust first-time document processing

| Task ID | Task | Status | Est. Time |
|---------|------|--------|-----------|
| 2.1 | Document registry (track all docs) | ⬜ | 45 min |
| 2.2 | Checksum calculation (detect changes) | ⬜ | 30 min |
| 2.3 | Batch embedding (efficient processing) | ⬜ | 45 min |
| 2.4 | Progress tracking (for large uploads) | ⬜ | 30 min |
| 2.5 | Error handling (partial failures) | ⬜ | 30 min |
| 2.6 | Test with 50+ documents | ⬜ | 30 min |

**Deliverable:** Can reliably index large document sets

---

### Phase 3: Evaluation Framework (Session 3)
**Goal:** Measure RAG quality before/after changes

| Task ID | Task | Status | Est. Time |
|---------|------|--------|-----------|
| 3.1 | Create test document set | ⬜ | 30 min |
| 3.2 | Generate Q&A test cases (LLM) | ⬜ | 30 min |
| 3.3 | Baseline evaluation (current system) | ⬜ | 30 min |
| 3.4 | Evaluation API endpoint | ✅ Done | - |
| 3.5 | Grafana dashboard for eval metrics | ⬜ | 30 min |
| 3.6 | Document baseline scores | ⬜ | 15 min |

**Deliverable:** Baseline metrics documented, can measure improvements

---

### Phase 4: Frontend Port (Session 4-5)
**Goal:** Full UI from rag-v1

| Task ID | Task | Status | Est. Time |
|---------|------|--------|-----------|
| 4.1 | Analyze rag-v1 frontend structure | ⬜ | 30 min |
| 4.2 | Port auth components | ⬜ | 1 hr |
| 4.3 | Port file upload UI | ⬜ | 45 min |
| 4.4 | Port chat interface | ⬜ | 1 hr |
| 4.5 | Port chat history view | ⬜ | 45 min |
| 4.6 | Adapt API calls to new backend | ⬜ | 1 hr |
| 4.7 | Build and deploy frontend | ⬜ | 30 min |
| 4.8 | End-to-end testing | ⬜ | 30 min |

**Deliverable:** Working UI with auth, upload, chat, history

---

### Phase 5: Incremental Pipeline (Session 6)
**Goal:** Efficient updates without full re-index

| Task ID | Task | Status | Est. Time |
|---------|------|--------|-----------|
| 5.1 | Design change detection strategy | ⬜ | 30 min |
| 5.2 | Implement doc-level change detection | ⬜ | 45 min |
| 5.3 | Add new documents (append) | ⬜ | 30 min |
| 5.4 | Update modified documents | ⬜ | 45 min |
| 5.5 | Delete documents (cascade chunks) | ⬜ | 30 min |
| 5.6 | Sync status tracking | ⬜ | 30 min |
| 5.7 | Test incremental scenarios | ⬜ | 30 min |

**Deliverable:** Can add/update/delete docs without full re-index

---

### Phase 6: Enterprise Connectors (Session 7)
**Goal:** Pull from external systems

| Task ID | Task | Status | Est. Time |
|---------|------|--------|-----------|
| 6.1 | Jira connector (issues, comments) | ⬜ | 1.5 hr |
| 6.2 | Confluence connector (pages) | ⬜ | 1.5 hr |
| 6.3 | Scheduled sync (cron-style) | ⬜ | 45 min |
| 6.4 | Incremental sync (since last) | ⬜ | 45 min |

**Deliverable:** Can sync from Jira/Confluence automatically

---

### Phase 7: Production Hardening (Session 8)
**Goal:** Production-ready system

| Task ID | Task | Status | Est. Time |
|---------|------|--------|-----------|
| 7.1 | Rate limiting | ⬜ | 30 min |
| 7.2 | Request tracing (full pipeline) | ⬜ | 45 min |
| 7.3 | Error recovery | ⬜ | 30 min |
| 7.4 | Performance optimization | ⬜ | 1 hr |
| 7.5 | Final evaluation (compare to baseline) | ⬜ | 30 min |
| 7.6 | Documentation | ⬜ | 1 hr |

**Deliverable:** Production-ready RAG with documented improvements

---

## Session Checkpoints

Each session should end with:
1. **Progress update** in `progress.md`
2. **Working code** committed
3. **Test results** documented
4. **Next session tasks** identified

---

## File Structure (Target)

```
stage4/
├── README.md
├── progress.md                    # Updated each session
├── master-plan.md                 # This file
├── new-design.md                  # Architecture details
├── rag-tooling-landscape.md       # Framework decisions
├── evaluation-results.md          # Before/after metrics
│
├── src/
│   ├── rag-enhanced/              # Backend
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── config.py
│   │   │   ├── loaders/           # Phase 1
│   │   │   │   ├── pdf.py
│   │   │   │   ├── markdown.py
│   │   │   │   ├── office.py
│   │   │   │   └── base.py
│   │   │   ├── chunker/           # ✅ Done
│   │   │   ├── retriever/         # ✅ Done
│   │   │   ├── evaluation/        # ✅ Done
│   │   │   ├── indexing/          # Phase 2
│   │   │   │   ├── registry.py
│   │   │   │   ├── pipeline.py
│   │   │   │   └── incremental.py # Phase 5
│   │   │   ├── connectors/        # Phase 6
│   │   │   │   ├── jira.py
│   │   │   │   └── confluence.py
│   │   │   └── auth/              # Phase 4
│   │   │       └── security.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   │
│   └── frontend/                  # Phase 4 (port from rag-v1)
│       ├── src/
│       ├── package.json
│       └── Dockerfile
│
├── k8s-manifests/
│   ├── rag-enhanced.yaml
│   └── frontend.yaml
│
└── test-data/                     # Phase 3
    ├── sample-docs/
    └── test-cases.json
```

---

## Success Metrics

| Metric | Baseline | Target |
|--------|----------|--------|
| Faithfulness | TBD | > 0.85 |
| Relevance | TBD | > 0.80 |
| Context Precision | TBD | > 0.75 |
| File Types Supported | 1 (txt) | 6+ |
| Incremental Update Time | N/A | < 10s per doc |
| Full Re-index Required | Always | Only on schema change |

---

## Current Progress

### Completed ✅
- [x] Smart chunking (LangChain splitters)
- [x] Hybrid retrieval (vector + BM25)
- [x] LLM reranking
- [x] Evaluation framework (RAGAS-style)
- [x] Basic API endpoints
- [x] Deployed to Minikube

### In Progress 🔄
- [ ] Phase 1: Document Loaders

### Not Started ⬜
- [ ] Phase 2: Initial Indexing Pipeline
- [ ] Phase 3: Evaluation Testing
- [ ] Phase 4: Frontend Port
- [ ] Phase 5: Incremental Pipeline
- [ ] Phase 6: Enterprise Connectors
- [ ] Phase 7: Production Hardening

---

## How to Resume

When starting a new session:

1. **Read this file** (`master-plan.md`) for context
2. **Check `progress.md`** for last completed task
3. **Find next task** in the phase list above
4. **Update progress** as you complete tasks

---

## Key Decisions Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Chunking library | LangChain text-splitters | Best-in-class, minimal deps |
| Vector DB | Weaviate | Already deployed, hybrid search native |
| Embedding | Ollama nomic-embed-text | Free, local, 768 dims |
| LLM | vLLM (local) + Bedrock (fallback) | Cost optimization |
| Frontend | Port rag-v1 React | Already built, proven |
| Incremental strategy | Doc-level checksum | Simple, reliable |

---

## Next Session: Phase 1 - Document Loaders

Start with Task 1.1: PDF Loader
