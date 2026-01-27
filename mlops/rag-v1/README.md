# RAG v1 - Enterprise Knowledge Assistant

Production-ready RAG system demonstrating enterprise patterns for GenAI consulting interviews.

## Quick Start

```bash
# 1. Login to AWS SSO
aws sso login --profile sandboxtest

# 2. Start all services
cd /mnt/f/zack-gitops-project/mlops/rag-v1
docker-compose up -d

# 3. Open browser
http://localhost:3000
```

**Default Users:** `admin`, `user1`, `user2` (no password needed)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React)                          │
│                    localhost:3000                            │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Login │ Chat │ Upload │ Documents │ New Chat       │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                  Backend (FastAPI)                           │
│                  localhost:8001                              │
│                                                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │   RAG    │ │  Agent   │ │ Security │ │ Pipeline │       │
│  │ Service  │ │ (ReAct)  │ │ JWT+RBAC │ │  Queue   │       │
│  │          │ │          │ │          │ │          │       │
│  │• Hybrid  │ │• Tools   │ │• Auth    │ │• Async   │       │
│  │• Rerank  │ │• Reason  │ │• Audit   │ │• Jobs    │       │
│  │• Cache   │ │          │ │• PII     │ │• Sync    │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
└──────┬──────────────────────────────┬───────────────────────┘
       │                              │
┌──────▼──────┐                ┌──────▼──────┐
│  Weaviate   │                │   Bedrock   │
│  Vector DB  │                │ Claude+Titan│
│  :8080      │                │  us-east-1  │
└─────────────┘                └─────────────┘
```

---

## Comparison: Previous RAG vs This Version

| Category | Previous RAG | RAG v1 (This Project) |
|----------|--------------|----------------------|
| **Core RAG** | | |
| Document formats | TXT, PDF | PDF, DOCX, TXT, images |
| Chunking | Fixed size | Semantic with overlap |
| Search | Vector only | Hybrid (vector + BM25) |
| Reranking | ❌ None | ✅ LLM-based |
| Source citation | Basic | With relevance scores |
| Source filtering | ❌ None | ✅ Auto-detect "blog 148" |
| **Security** | | |
| Authentication | ❌ None | ✅ JWT with mock users |
| Authorization | ❌ None | ✅ Row-level access control |
| Audit logging | ❌ None | ✅ Full audit trail |
| Input validation | ❌ None | ✅ Prompt injection detection |
| PII filtering | ❌ None | ✅ Regex-based |
| Rate limiting | ❌ None | ✅ 30 req/min per user |
| **Production** | | |
| Caching | ❌ None | ✅ Response cache (4s→8ms) |
| Conversation memory | ❌ None | ✅ Session-based |
| Streaming | ❌ None | ✅ SSE streaming |
| Async processing | ❌ None | ✅ Job queue + worker |
| Token tracking | ❌ None | ✅ Cost monitoring |
| Model routing | ❌ None | ✅ Fast/smart selection |
| **Advanced** | | |
| Agent/reasoning | ❌ None | ✅ ReAct pattern |
| External connectors | ❌ None | ✅ Web, Jira, Confluence |
| Data pipeline | ❌ None | ✅ Scheduled sync jobs |
| **UI** | | |
| Frontend | CLI only | ✅ React chat UI |
| Doc management | Manual | ✅ Upload/delete in UI |
| Session persistence | ❌ None | ✅ localStorage |

### Verdict

| Aspect | Previous | This Version |
|--------|----------|--------------|
| Interview Ready | 3/10 | **9/10** |
| Production Ready | 2/10 | **7/10** |
| Security | 1/10 | **7/10** |
| Scalability | 2/10 | **6/10** |
| Maintainability | 3/10 | **8/10** |

---

## Features

### Core RAG
- ✅ Multi-format upload (PDF, DOCX, TXT, images)
- ✅ Semantic chunking with overlap
- ✅ Hybrid search (vector + BM25 keyword)
- ✅ LLM reranking for precision
- ✅ Source citation with relevance scores
- ✅ Source filtering (auto-detects "blog 148", "document 123")

### Security
- ✅ JWT authentication with mock users
- ✅ Row-level access control (document permissions)
- ✅ Audit logging (all queries logged)
- ✅ Input validation (prompt injection detection)
- ✅ PII filtering in outputs
- ✅ Rate limiting (30 req/min per user)

### Production Features
- ✅ Response caching (4s → 8ms)
- ✅ Model routing (fast/smart auto-selection)
- ✅ Conversation memory (session-based)
- ✅ Token usage tracking & cost estimates
- ✅ Streaming responses (SSE)
- ✅ No results handling (friendly UX)
- ✅ Async document processing (job queue)

### Data Pipeline
- ✅ Scheduled sync jobs
- ✅ Web connector (Django, WordPress)
- ✅ Change detection (content hashing)
- ✅ Multiple auth types (Django admin, Basic, API key)

### Agent
- ✅ ReAct pattern with multi-step reasoning
- ✅ 5 tools: search_docs, list_sources, calculate, get_date, compare_docs
- ✅ Rule-based tool selection for reliability

### Frontend
- ✅ React chat interface
- ✅ Login with mock users
- ✅ Document upload/delete
- ✅ Processing time & relevance scores
- ✅ Session persistence (survives refresh)
- ✅ New Chat button

---

## API Reference

### Authentication
```bash
# Login (get JWT token)
curl -X POST http://localhost:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin"}'

# Use token in subsequent requests
-H "Authorization: Bearer <token>"
```

### Document Management
```bash
# Upload document (sync)
curl -X POST http://localhost:8001/upload -F "file=@document.pdf"

# Upload document (async)
curl -X POST http://localhost:8001/upload/async -F "file=@document.pdf"
# Returns: {"job_id": "abc123"}

# Check job status
curl http://localhost:8001/jobs/abc123

# List documents
curl http://localhost:8001/documents

# Delete document
curl -X DELETE http://localhost:8001/documents/document.pdf
```

### Query
```bash
# Basic query
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is RAG?"}'

# Query with session (conversation memory)
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Tell me more", "session_id": "my-session"}'

# Query specific document
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Summarize blog 148"}'  # Auto-detects source

# Agent query (multi-step reasoning)
curl -X POST http://localhost:8001/agent \
  -H "Content-Type: application/json" \
  -d '{"query": "Find documents about AWS and summarize them"}'
```

### Data Pipeline
```bash
# Create sync job
curl -X POST http://localhost:8001/pipeline/jobs \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "blog-sync",
    "source_type": "web",
    "source_config": {
      "base_url": "http://host.docker.internal:8000",
      "pattern": "/post/",
      "limit": 20
    }
  }'

# Run job manually
curl -X POST http://localhost:8001/pipeline/jobs/blog-sync/run \
  -H "Authorization: Bearer <token>"

# Sync from internal website
curl -X POST http://localhost:8001/connectors/web/sync \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "base_url": "http://host.docker.internal:8000",
    "pattern": "/post/",
    "limit": 10
  }'
```

### Admin
```bash
# View audit log
curl http://localhost:8001/audit -H "Authorization: Bearer <token>"

# Token usage & costs
curl http://localhost:8001/usage -H "Authorization: Bearer <token>"

# Cache stats
curl http://localhost:8001/cache/stats -H "Authorization: Bearer <token>"
```

---

## Configuration

### Environment Variables (docker-compose.yml)
```yaml
AWS_PROFILE: sandboxtest
AWS_REGION: us-east-1
BEDROCK_MODEL_ID: anthropic.claude-3-haiku-20240307-v1:0
EMBEDDING_MODEL_ID: amazon.titan-embed-text-v1
```

### Services
| Service | Port | Description |
|---------|------|-------------|
| Frontend | 3000 | React chat UI |
| Backend | 8001 | FastAPI server |
| Weaviate | 8080 | Vector database |

---

## Project Structure

```
rag-v1/
├── docker-compose.yml
├── README.md
├── design.md              # Detailed architecture & patterns
├── progress.md            # Development log
├── RAG_FUNDAMENTALS.md    # Interview prep guide
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py        # FastAPI endpoints
│       ├── config.py      # Settings
│       ├── rag/
│       │   ├── service.py     # Core RAG logic
│       │   ├── retriever.py   # Hybrid search + rerank
│       │   └── evaluator.py   # Response evaluation
│       ├── agents/
│       │   └── rag_agent.py   # ReAct agent
│       ├── security/
│       │   ├── auth.py        # JWT authentication
│       │   ├── access_control.py  # RBAC
│       │   ├── audit.py       # Audit logging
│       │   └── validation.py  # Input validation
│       ├── connectors/
│       │   ├── base.py        # Jira/Confluence mock
│       │   └── web_connector.py  # Web scraper
│       └── utils/
│           ├── cache.py       # Response caching
│           ├── memory.py      # Conversation memory
│           ├── queue.py       # Async job queue
│           ├── router.py      # Model routing
│           ├── limits.py      # Rate limiting
│           └── pipeline.py    # Scheduled sync
│
└── frontend/
    ├── Dockerfile
    ├── package.json
    ├── nginx.conf
    └── src/
        ├── App.jsx        # Main chat component
        ├── main.jsx       # Entry point
        └── index.css      # Styles
```

---

## Local vs Production

| Local Component | Production AWS |
|-----------------|----------------|
| In-memory queue | SQS |
| Background worker | Lambda / ECS |
| File storage | S3 |
| Job status dict | DynamoDB |
| Weaviate | OpenSearch Serverless |
| Mock connectors | Real Jira/Confluence APIs |
| In-memory sessions | Redis (ElastiCache) |
| localStorage | Backend session store |
| JSON pipeline state | DynamoDB |

---

## Interview Topics Covered

1. **RAG Architecture** - Ingestion, chunking, embedding, retrieval, generation
2. **Hybrid Search** - Vector + keyword (BM25), alpha parameter tuning
3. **Reranking** - LLM-based precision improvement
4. **Security** - JWT, RBAC, audit, input validation, PII filtering
5. **Production Patterns** - Caching, async queues, rate limiting, cost tracking
6. **Data Pipelines** - Event-driven vs polling, change detection, idempotency
7. **Session Management** - Memory limits, token control, horizontal scaling
8. **Agent Patterns** - ReAct, tool registry, multi-step reasoning
9. **Enterprise Integration** - Web connectors, authentication, scheduled sync
10. **Cost Optimization** - Model routing, caching, token tracking

---

## Documentation

- **[GUIDE.md](GUIDE.md)** - Local setup and testing guide
- **[design.md](design.md)** - Detailed architecture, patterns, and production recommendations
- **[AGENT.md](AGENT.md)** - Agent patterns and tools documentation
- **[RAG_FUNDAMENTALS.md](RAG_FUNDAMENTALS.md)** - Interview preparation guide
- **progress.md** - Development timeline and feature checklist

---

## Troubleshooting

### AWS SSO Token Expired
```bash
aws sso login --profile sandboxtest
docker-compose restart backend
```

### Weaviate Connection Error
```bash
docker-compose restart weaviate
sleep 5
docker-compose restart backend
```

### Check Logs
```bash
docker logs rag-v1-backend-1 --tail 50
docker logs rag-v1-frontend-1 --tail 50
```

---

## License

MIT - Built for GenAI consulting interview preparation (NCS Australia)
