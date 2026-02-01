# Stage 4 Progress

> **Last Updated:** 2026-02-01 11:41 AEDT  
> **Current Phase:** Phase 1 - Document Loaders  
> **Next Task:** Build v3, deploy, test with season1.pdf

---

## Quick Status

| Phase | Status | Tasks |
|-------|--------|-------|
| Phase 1: Document Loaders | 🔄 In Progress | 3/4 |
| Phase 2: Evaluation Baseline | ⬜ | 0/4 |
| Phase 3: Confluence Connector | ⬜ | 0/3 |
| Phase 4: Final Eval & Docs | ⬜ | 0/4 |

---

## NEXT SESSION PICKUP

```bash
# 1. Build and push v3
cd /Users/zz/zz/Documents/zack-gitops-project/zack_blog_archive/aiml-workload/stage4/src/rag-enhanced
eval $(minikube docker-env)
docker build -t rag-enhanced:v3 .

# 2. Update deployment to v3
ssh zz@192.168.1.100 "kubectl set image deployment/rag-backend rag-backend=rag-enhanced:v3 -n ai-platform"

# 3. Test with PDF
curl -X POST "http://$(minikube ip):30085/v1/rag/upload" \
  -F "file=@/Users/zz/zz/Documents/zack-gitops-project/mlops/peppapig/season1.pdf"

# 4. Query to verify
curl -X POST "http://$(minikube ip):30085/v1/rag/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "What happens in the first episode of Peppa Pig?"}'
```

---

## This Session Goals

- [x] 1.1 PDF Loader ✅
- [x] 1.2 Word Loader ✅
- [x] 1.3 Excel Loader ✅
- [ ] 1.4 Test with real docs (season1.pdf)
- [ ] 2.1-2.4 Baseline evaluation

---

## Completed ✅

### Phase 1: Document Loaders (Code Complete)
- [x] `loaders/base.py` - LoadedDocument dataclass with checksum
- [x] `loaders/pdf.py` - PDFLoader with pdfplumber, page-aware, table extraction
- [x] `loaders/office.py` - WordLoader (python-docx), ExcelLoader (openpyxl)
- [x] `loaders/__init__.py` - Exports all loaders
- [x] Integrated loaders into `main.py` /upload endpoint
- [x] Updated `requirements.txt` with: pdfplumber, python-docx, openpyxl

### Pre-work (from earlier sessions)
- [x] Smart chunking (LangChain text-splitters)
- [x] Hybrid retrieval (vector + BM25)
- [x] LLM reranking
- [x] Evaluation framework (RAGAS-style)
- [x] Deployed rag-enhanced:v2

### Documentation
- [x] master-plan.md (refined)
- [x] career-strategy.md (ROI assessment)
- [x] new-design.md
- [x] rag-tooling-landscape.md

---

## Key File Locations

```
stage4/
├── progress.md          <- THIS FILE (pickup point)
├── master-plan.md       <- Overall plan & ROI
├── career-strategy.md   <- Job search focus
├── src/rag-enhanced/
│   ├── app/
│   │   ├── main.py      <- FastAPI app (updated with loaders)
│   │   ├── loaders/     <- NEW: PDF, Word, Excel loaders
│   │   ├── chunker/     <- Smart chunking
│   │   ├── retriever/   <- Hybrid search + rerank
│   │   └── evaluation/  <- RAGAS-style metrics
│   ├── requirements.txt <- Updated with loader deps
│   └── Dockerfile
```

---

## Cluster State (as of last session)

```
ai-platform namespace:
├── ai-gateway (Running) - port 30085
├── rag-backend (Running, rag-enhanced:v2) <- needs v3
├── vllm (Running)
└── weaviate (Running)

Mac Mini: 192.168.1.100
```

---

## Session Log

### 2026-02-01 Session 2

**Duration:** ~15 min (context overflow recovery)

**Done:**
- Recovered from context overflow
- Found stage4 at `zack_blog_archive/aiml-workload/stage4/`
- Verified loaders were already created (base.py, pdf.py, office.py)
- Added `__init__.py` exports
- Updated `requirements.txt` with loader dependencies
- Integrated loaders into `main.py` /upload endpoint

**Stopped at:** Ready to build v3 and test with season1.pdf

**Test file:** `mlops/peppapig/season1.pdf` (701KB, multi-page script)
