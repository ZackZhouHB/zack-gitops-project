# RAG v1 Enhancement Project - Progress Tracker

## Project Goal

Build production-ready RAG system for GenAI consulting role (NCS Australia) interview preparation.

---

## Implementation Summary

| Phase | Feature | Status |
|-------|---------|--------|
| 0 | Docker infrastructure | ✅ |
| 1 | Core RAG (multi-format, chunking, embedding) | ✅ |
| 2 | Advanced RAG (hybrid search, reranking) | ✅ |
| 3 | Security (JWT, RBAC, audit, validation) | ✅ |
| 4 | Agent (ReAct pattern, tools) | ✅ |
| 5 | Production (caching, routing, memory, connectors) | ✅ |
| 6 | Data Pipeline (async upload, job queue, worker) | ✅ |
| 7 | Frontend (React chat UI) | ✅ |

---

## Session Log

| Date | Time | Task | Status |
|------|------|------|--------|
| 2026-01-27 | 19:17 | Created rag-v1, progress.md, design.md | ✅ |
| 2026-01-27 | 19:24 | Created RAG_FUNDAMENTALS.md | ✅ |
| 2026-01-27 | 19:29 | Cleaned folder, created new structure | ✅ |
| 2026-01-27 | 20:10 | Created docker-compose, config, main.py, service.py | ✅ |
| 2026-01-27 | 20:12 | Added multi-format loader (PDF, DOCX, images) | ✅ |
| 2026-01-27 | 20:13 | Added hybrid search + reranking | ✅ |
| 2026-01-27 | 20:16 | Added JWT auth, access control, audit logging | ✅ |
| 2026-01-27 | 20:17 | Added RAG agent with ReAct pattern | ✅ |
| 2026-01-27 | 20:20 | Docker build & test - API working | ✅ |
| 2026-01-27 | 20:27 | Fixed AWS SSO + Bedrock integration | ✅ |
| 2026-01-27 | 20:30 | Tested all features: auth, upload, query, agent, audit | ✅ |
| 2026-01-27 | 20:35 | Added validation, caching, routing, eval, connectors | ✅ |
| 2026-01-27 | 20:42 | Created React frontend | ✅ |
| 2026-01-27 | 20:48 | Added conversation memory | ✅ |
| 2026-01-27 | 20:52 | Added processing time, relevance scores, upload time | ✅ |
| 2026-01-27 | 20:55 | Added document deletion | ✅ |
| 2026-01-27 | 21:00 | Added async upload with job queue and worker | ✅ |
| 2026-01-27 | 21:05 | Added rate limiting, token tracking, no-results handling | ✅ |
| 2026-01-27 | 21:10 | Added web connector for Django blog sync | ✅ |
| 2026-01-27 | 21:15 | Added source-aware retrieval (auto-detect doc references) | ✅ |
| 2026-01-27 | 21:20 | Added scheduled data pipeline with job management | ✅ |
| 2026-01-27 | 21:28 | Fixed frontend session persistence (localStorage) | ✅ |

---

## Issues & Resolutions

| Issue | Cause | Resolution |
|-------|-------|------------|
| `BedrockEmbeddings` import error | langchain_aws API changed | Use direct boto3 invoke_model |
| Model ID invalid | Titan v1 not in ap-southeast-2 | Switch to us-east-1 region |
| Claude 3.5 Haiku error | Needs inference profile | Use claude-3-haiku-20240307-v1:0 |
| AWS_REGION not updating | .env overriding compose | Hardcode in docker-compose.yml |
| SSO creds not in container | No AWS config access | Mount ~/.aws:/root/.aws:ro |
| Agent KeyError | Sources missing content | Return RAG answer as context |
| Port 8000 conflict | Other container | Changed to port 8001 |

---

## All Features

### Backend API
| Feature | Endpoint | Status |
|---------|----------|--------|
| Health check | GET /health | ✅ |
| JWT Auth | POST /auth/login | ✅ |
| Sync upload | POST /upload | ✅ |
| **Async upload** | POST /upload/async | ✅ |
| **Job status** | GET /jobs/{id} | ✅ |
| **List jobs** | GET /jobs | ✅ |
| List documents | GET /documents | ✅ |
| Delete document | DELETE /documents/{source} | ✅ |
| RAG query | POST /query | ✅ |
| Streaming query | POST /query/stream | ✅ |
| Agent query | POST /agent | ✅ |
| Conversation memory | session_id in query | ✅ |
| Audit log | GET /audit | ✅ |
| Cache stats | GET /cache/stats | ✅ |
| Connector sync | POST /connectors/sync | ✅ |
| Evaluation | POST /evaluate | ✅ |
| **Rate limiting** | 30 req/min per user | ✅ |
| **Token tracking** | GET /usage | ✅ |
| **No results handling** | Friendly message | ✅ |
| **Web connector** | POST /connectors/web/sync | ✅ |
| **Source filtering** | Auto-detect "blog 148" | ✅ |
| **Data pipeline** | POST /pipeline/jobs | ✅ |
| **Session persistence** | localStorage + New Chat | ✅ |

### Frontend
| Feature | Status |
|---------|--------|
| Login with mock users | ✅ |
| Chat interface | ✅ |
| Document upload | ✅ |
| Document delete | ✅ |
| Processing time display | ✅ |
| Relevance scores | ✅ |
| Upload timestamps | ✅ |
| Cache indicator | ✅ |

---

## Running Services

```bash
docker-compose up -d
```

| Service | Port | URL |
|---------|------|-----|
| Frontend | 3000 | http://localhost:3000 |
| Backend | 8001 | http://localhost:8001 |
| Weaviate | 8080 | http://localhost:8080 |

---

## Test Commands

```bash
# Sync upload
curl -X POST http://localhost:8001/upload -F "file=@test.txt"

# Async upload (production pattern)
curl -X POST http://localhost:8001/upload/async -F "file=@test.txt"
# Returns: {"job_id": "abc123", "status": "queued"}

# Check job status
curl http://localhost:8001/jobs/abc123
# Returns: {"status": "completed", "chunks": 5}

# Query with memory
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is RAG?", "session_id": "user123"}'

# Follow-up question (uses memory)
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Tell me more about it", "session_id": "user123"}'

# Delete document
curl -X DELETE http://localhost:8001/documents/test.txt
```

---

## Configuration

```yaml
AWS_PROFILE: sandboxtest
AWS_REGION: us-east-1
EMBEDDING_MODEL: amazon.titan-embed-text-v1
LLM_MODEL: anthropic.claude-3-haiku-20240307-v1:0
```
