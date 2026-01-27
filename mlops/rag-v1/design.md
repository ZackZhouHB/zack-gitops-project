# RAG v1 - Enterprise Enhancement Design

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                 │
│                    React (localhost:3000)                        │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│                      BACKEND API                                 │
│                  FastAPI (localhost:8001)                        │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    ENDPOINTS                              │   │
│  │  /upload (sync)  /upload/async  /query  /agent  /jobs    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐   │
│  │    RAG     │ │   Agent    │ │  Security  │ │   Queue    │   │
│  │  Service   │ │  (ReAct)   │ │ JWT+RBAC   │ │  Worker    │   │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘   │
└──────┬──────────────────┬───────────────────────────────────────┘
       │                  │
┌──────▼──────┐    ┌──────▼──────┐
│  Weaviate   │    │   Bedrock   │
│  Vector DB  │    │ Claude+Titan│
│  :8080      │    │  us-east-1  │
└─────────────┘    └─────────────┘
```

---

## Data Pipeline Design

### Synchronous Flow (Simple)
```
POST /upload → Load → Chunk → Embed → Store → Response
```

### Asynchronous Flow (Production)
```
POST /upload/async → Create Job → Queue → Return job_id
                                    ↓
                            Background Worker
                                    ↓
                     Load → Chunk → Embed → Store
                                    ↓
                            Update Job Status
                                    ↓
GET /jobs/{id} → "completed" with chunk count
```

### Production AWS Architecture
```
┌─────────────────────────────────────────────────────────────────┐
│                     INGESTION PIPELINE                           │
│                                                                  │
│  ┌─────────┐      ┌──────────┐      ┌───────────┐    ┌────────┐ │
│  │   S3    │─────▶│   SQS    │─────▶│  Lambda   │───▶│OpenSearch│
│  │ Bucket  │      │  Queue   │      │  Worker   │    │Serverless│
│  └─────────┘      └──────────┘      └───────────┘    └────────┘ │
│       ↑                                                          │
│  ┌─────────┐      ┌──────────┐                                  │
│  │   API   │─────▶│ DynamoDB │  (Job Status)                    │
│  │ Gateway │      │  Table   │                                  │
│  └─────────┘      └──────────┘                                  │
│                                                                  │
│  ┌─────────┐      ┌──────────┐                                  │
│  │EventBridge────▶│  Lambda  │  (Scheduled Sync)                │
│  │ Schedule│      │  Sync    │                                  │
│  └─────────┘      └──────────┘                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Implemented Features

### Phase 1: Core RAG ✅
- Multi-format document loader (PDF, DOCX, TXT, images)
- Smart chunking with metadata preservation
- Bedrock Titan embeddings
- Weaviate vector storage

### Phase 2: Advanced RAG ✅
- Hybrid search (vector + BM25 keyword)
- LLM reranking for precision
- Source citation with relevance scores

### Phase 3: Security ✅
- JWT authentication
- Row-level access control (document permissions)
- Audit logging
- Input validation (prompt injection detection)
- PII filtering

### Phase 4: Agentic ✅
- ReAct agent pattern
- Tool registry
- Multi-step reasoning

### Phase 5: Production Features ✅
- Response caching (4s → 8ms)
- Model routing (cost optimization)
- Conversation memory (follow-up questions)
- Connector framework (Jira, Confluence mock)
- Streaming responses
- RAG evaluation endpoint
- **Rate limiting** (30 req/min per user)
- **Token usage tracking** (cost monitoring)
- **No results handling** (friendly UX)

---

## Production PII/Sensitive Data Protection

### Defense in Depth Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Input Pipeline                        │
│  User → WAF → Rate Limit → PII Detect → Tokenize → LLM │
└─────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────┐
│                   Output Pipeline                        │
│  LLM → PII Scan → Guardrails → De-tokenize → Response  │
└─────────────────────────────────────────────────────────┘
```

### Input Protection (Before LLM)

| Technique | Description | Tools |
|-----------|-------------|-------|
| Regex Detection | Pattern match SSN, credit cards, emails | Custom rules |
| NER Models | ML-based entity recognition | AWS Comprehend, Presidio, spaCy |
| Tokenization | Replace PII with tokens, store mapping | AWS Macie, HashiCorp Vault |
| Redaction | Remove/mask before sending to LLM | Presidio, custom |

### Output Protection (After LLM)

| Technique | Description | Tools |
|-----------|-------------|-------|
| Post-scan | Scan LLM response for leaked PII | NER/regex |
| Guardrails | Block responses with sensitive patterns | AWS Bedrock Guardrails |
| Content filtering | Block harmful/inappropriate content | Bedrock Guardrails |

### AWS Bedrock Guardrails (Production)

Managed service providing:
- **PII detection/redaction** - SSN, credit cards, names, addresses, phone numbers
- **Denied topics** - Block specific subjects (competitors, legal advice)
- **Word filters** - Profanity, custom blocked terms
- **Content filters** - Hate speech, violence, sexual content, insults

### Current Implementation vs Production

| Feature | This Project | Production Recommendation |
|---------|--------------|---------------------------|
| PII regex | ✅ Basic patterns | AWS Comprehend for NER |
| Prompt injection | ✅ Keyword detection | ML-based classifiers |
| Output sanitization | ✅ Basic regex | Bedrock Guardrails |
| Tokenization | ❌ Not implemented | Vault/custom service |
| Audit trail | ✅ File logging | SIEM integration (Splunk, CloudWatch) |

### Key Interview Points

1. **Defense in depth** - Multiple layers, not single check
2. **Tokenization** - LLM never sees real PII, only reversible tokens
3. **Managed services** - AWS Comprehend + Bedrock Guardrails for enterprise
4. **Audit everything** - Log detections/blocks for compliance (SOC2, HIPAA)
5. **Trade-offs** - More protection = more latency + cost

---

## Enterprise Web Connector

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Web Connector                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │  Auth    │→ │ Discover │→ │  Fetch   │→ │  Ingest  │    │
│  │ (Django/ │  │  Pages   │  │ & Parse  │  │  to RAG  │    │
│  │  Basic)  │  │          │  │          │  │          │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### Supported Authentication

| Type | Use Case | Config |
|------|----------|--------|
| None | Public sites | `{}` |
| Django Admin | Internal Django apps | `{"type": "django_admin", "username": "x", "password": "y"}` |
| Basic Auth | Simple protected sites | `{"type": "basic", "username": "x", "password": "y"}` |
| API Key | REST APIs | `{"type": "api_key", "api_key": "xxx"}` |
| Cookie | Session-based | `{"type": "cookie", "cookie_name": "x", "cookie_value": "y"}` |

### API Usage

```bash
# Sync from internal Django blog
POST /connectors/web/sync
{
  "base_url": "http://internal-blog:8000",
  "pattern": "/post/",
  "limit": 50,
  "auth": {"type": "django_admin", "username": "admin", "password": "xxx"}
}
```

### Security Considerations

1. **Credential storage** - Use secrets manager (AWS Secrets Manager, Vault)
2. **Network isolation** - Connector runs in private subnet
3. **Rate limiting** - Respect target site's limits
4. **Content hashing** - Detect changes, avoid re-ingesting
5. **Audit trail** - Log all sync operations

---

## Source-Aware Retrieval

### Problem
When users ask about specific documents by ID (e.g., "What is blog 148 about?"), semantic search fails because:
- "blog 148" is a URL identifier, not in the document content
- Vector similarity finds semantically similar content, not the specific document

### Solution

1. **Explicit source filter** - API parameter to filter by source URL
2. **Auto-detection** - Regex extracts document references from questions

```python
# Auto-detect: "blog 148", "post 148", "document #123"
match = re.search(r'(?:blog|post|document|doc|article)\s*(?:#|id\s*)?(\d+)', question, re.I)
if match:
    source_filter = f"post/{match.group(1)}"
```

### API Usage

```bash
# Explicit filter
POST /query
{"question": "Summarize this", "source_filter": "post/148"}

# Auto-detected (no filter needed)
POST /query
{"question": "What is blog 148 about?"}  # Auto-extracts "post/148"
```

### Why This Matters

| Query Type | Without Fix | With Fix |
|------------|-------------|----------|
| "What is blog 148 about?" | Returns random similar docs | Returns post 148 content |
| "Summarize document 123" | Semantic mismatch | Filters to doc 123 |
| "Tell me about electricity analytics" | Works (semantic) | Works (semantic) |

This is a common RAG pattern for enterprise systems where users reference documents by ID, ticket number, or filename.

---

## Scheduled Data Pipeline

### Real-World Patterns

| Pattern | How It Works | AWS Tools |
|---------|--------------|-----------|
| Event-Driven | S3 upload → Lambda → Ingest | S3 Events, EventBridge, Lambda |
| Scheduled Sync | Cron polls sources periodically | CloudWatch Events, Airflow, Step Functions |
| Change Data Capture | DB triggers on insert/update | DynamoDB Streams, Debezium, Kinesis |
| Webhook | Source pushes on change | API Gateway, SNS |
| Queue-Based | Messages trigger processing | SQS, Kafka, RabbitMQ |

### Enterprise Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Data Sources                                  │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐        │
│  │   S3   │ │ Jira   │ │Confluenc│ │ Slack  │ │  Web   │        │
│  └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘        │
└──────┼──────────┼──────────┼──────────┼──────────┼──────────────┘
       │          │          │          │          │
       ▼          ▼          ▼          ▼          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Event Bus (EventBridge/Kafka)                 │
└─────────────────────────────────┬───────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Processing Pipeline                           │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐        │
│  │ Queue  │→│ Parse  │→│ Chunk  │→│ Embed  │→│ Store  │        │
│  │ (SQS)  │ │        │ │        │ │(Bedrock)│ │(Vector)│        │
│  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

### Local Simulation

Our implementation simulates:
- **Job Registry** - Define sync jobs with source config
- **Change Detection** - Content hashing to skip unchanged docs
- **Manual/Scheduled Triggers** - Run on-demand or via scheduler
- **State Persistence** - Track last run, enable/disable jobs

### API Usage

```bash
# Create a scheduled sync job
POST /pipeline/jobs
{
  "name": "blog-sync",
  "source_type": "web",
  "source_config": {
    "base_url": "http://internal-blog:8000",
    "pattern": "/post/",
    "limit": 50
  },
  "schedule": "*/5"
}

# List all jobs
GET /pipeline/jobs

# Manually trigger a job
POST /pipeline/jobs/blog-sync/run

# Run all enabled jobs
POST /pipeline/run-all
```

### Production vs Local

| Feature | Local Simulation | Production |
|---------|------------------|------------|
| Scheduler | In-memory loop | Airflow/Step Functions |
| Queue | In-memory | SQS/Kafka |
| State | JSON file | DynamoDB/RDS |
| Triggers | Manual/API | EventBridge/S3 Events |
| Scaling | Single worker | Lambda/ECS auto-scale |
| Monitoring | Logs | CloudWatch/Datadog |

### Interview Talking Points

1. **Event-driven vs polling** - Events are real-time but complex; polling is simple but delayed
2. **Idempotency** - Content hashing ensures re-runs don't duplicate data
3. **Backpressure** - Queues decouple ingestion rate from processing capacity
4. **Dead letter queues** - Failed items go to DLQ for retry/investigation
5. **Observability** - Track sync lag, failure rates, processing time

---

## Session Management & Scalability

### Current Implementation (Demo)

```python
class ConversationMemory:
    sessions: Dict[str, dict] = {}  # In-memory
    max_turns = 10                   # Cap history
    timeout = 60 minutes             # Auto-cleanup
```

| Feature | Status | Notes |
|---------|--------|-------|
| Session isolation | ✅ | By `session_id` |
| History limit | ✅ | 10 turns max |
| Prompt limit | ✅ | Only 3 turns to LLM |
| Auto-cleanup | ✅ | 60 min timeout |
| Persistence | ❌ | Lost on restart |
| Horizontal scale | ❌ | Single instance only |

### Production Architecture

```
┌─────────┐  ┌─────────┐  ┌─────────┐
│Backend 1│  │Backend 2│  │Backend 3│
└────┬────┘  └────┬────┘  └────┬────┘
     │            │            │
     └────────────┼────────────┘
                  │
           ┌──────▼──────┐
           │    Redis    │
           │  (Sessions) │
           └─────────────┘
                  │
           ┌──────▼──────┐
           │  DynamoDB   │
           │ (Long-term) │
           └─────────────┘
```

### Production Requirements

| Feature | Solution | AWS Service |
|---------|----------|-------------|
| Session persistence | External store | Redis (ElastiCache) |
| Horizontal scaling | Shared session store | ElastiCache/DynamoDB |
| Session quota | Max sessions per user | Application logic |
| Memory cap | LRU eviction | Redis maxmemory policy |
| Long-term history | Archive old sessions | DynamoDB + S3 |
| Cross-region | Global session store | DynamoDB Global Tables |

### Redis Session Store (Production Code)

```python
import redis
import json

class RedisConversationMemory:
    def __init__(self, redis_url: str, max_turns: int = 10, ttl: int = 3600):
        self.redis = redis.from_url(redis_url)
        self.max_turns = max_turns
        self.ttl = ttl  # 1 hour
    
    def get_history(self, session_id: str) -> List[dict]:
        data = self.redis.get(f"session:{session_id}")
        return json.loads(data) if data else []
    
    def add_turn(self, session_id: str, question: str, answer: str):
        history = self.get_history(session_id)
        history.extend([
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer}
        ])
        # Keep last N turns
        history = history[-(self.max_turns * 2):]
        self.redis.setex(f"session:{session_id}", self.ttl, json.dumps(history))
```

### Interview Talking Points

1. **Why not in-memory?** - Lost on restart, can't scale horizontally
2. **Why Redis over DynamoDB?** - Lower latency for frequent reads, TTL built-in
3. **Session isolation** - Each user gets unique session_id, no cross-contamination
4. **Token control** - Only send last N turns to LLM to manage costs
5. **Memory pressure** - Redis LRU eviction prevents OOM under load

### Frontend Session Persistence ✅

| Feature | Implementation |
|---------|----------------|
| Session ID | Stored in localStorage, persists across refresh |
| Chat history | Stored in localStorage, restored on page load |
| New Chat | Clears localStorage, creates new session_id |
| Logout | Clears all session data (token, session, history) |

```javascript
// Session persistence
const [sessionId] = useState(() => localStorage.getItem('sessionId'))
const [messages] = useState(() => JSON.parse(localStorage.getItem('chatHistory') || '[]'))

// New chat clears everything
const newChat = () => {
  const newSession = user.user_id + '_' + Date.now()
  setSessionId(newSession)
  localStorage.setItem('sessionId', newSession)
  setMessages([])
}
```

### Phase 6: Data Pipeline ✅
- Async upload with job queue
- Background worker processing
- Job status tracking
- Document deletion

### Phase 7: Frontend ✅
- React chat interface
- Login with mock users
- Document upload/delete
- Processing time display
- Relevance scores per source
- Upload timestamps

---

## API Reference

### Document Management
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/upload` | POST | Sync upload (blocking) |
| `/upload/async` | POST | Async upload (returns job_id) |
| `/jobs` | GET | List processing jobs |
| `/jobs/{id}` | GET | Get job status |
| `/documents` | GET | List indexed documents |
| `/documents/{source}` | DELETE | Delete document |

### Query
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/query` | POST | RAG query with memory |
| `/query/stream` | POST | Streaming response |
| `/agent` | POST | Agent with reasoning |

### Admin
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/audit` | GET | View audit log |
| `/cache/stats` | GET | Cache statistics |
| `/connectors/sync` | POST | Sync Jira/Confluence (mock) |
| `/connectors/web/sync` | POST | Sync internal websites |
| `/evaluate` | POST | Evaluate response quality |
| `/usage` | GET | Token usage & cost estimates |

---

## Local vs Production Mapping

| Local Component | Production AWS |
|-----------------|----------------|
| In-memory queue | SQS |
| Background worker | Lambda / ECS |
| File storage | S3 |
| Job status dict | DynamoDB |
| Weaviate | OpenSearch Serverless |
| Mock connectors | Real Jira/Confluence APIs |
| In-memory sessions | Redis (ElastiCache) |
| JSON pipeline state | DynamoDB |
| localStorage (frontend) | Backend session store |

---

## Feature Summary

### ✅ Implemented (Local Demo)

| Category | Feature | Description |
|----------|---------|-------------|
| **Core RAG** | Multi-format ingestion | PDF, DOCX, TXT, images |
| | Hybrid search | Vector + BM25 keyword |
| | LLM reranking | Precision improvement |
| | Source citation | With relevance scores |
| | Source filtering | Auto-detect "blog 148" references |
| **Security** | JWT authentication | Mock users (admin, user1, user2) |
| | Row-level access | Document permissions by group |
| | Audit logging | All queries logged |
| | Input validation | Prompt injection detection |
| | PII filtering | Regex-based patterns |
| | Rate limiting | 30 req/min per user |
| **Production** | Response caching | 4s → 8ms |
| | Model routing | Fast/smart auto-selection |
| | Conversation memory | Session-based with history |
| | Token tracking | Cost monitoring per user |
| | No results handling | Friendly UX message |
| | Streaming responses | SSE for real-time output |
| **Data Pipeline** | Async upload | Job queue + worker |
| | Scheduled sync | Pipeline job management |
| | Web connector | Django/WordPress scraping |
| | Change detection | Content hashing |
| **Agent** | ReAct pattern | Multi-step reasoning |
| | Tool registry | Extensible tools |
| **Frontend** | React chat UI | Login, upload, query |
| | Session persistence | localStorage for history |
| | New Chat button | Clear and start fresh |

### ❌ Not Implemented (Production Recommendations)

| Feature | Why Not Local | Production Solution |
|---------|---------------|---------------------|
| Bedrock Guardrails | Requires AWS setup | Enable in Bedrock console |
| PII tokenization | Complex, needs Vault | HashiCorp Vault / AWS Macie |
| ML prompt injection | Needs training data | Fine-tuned classifier |
| Redis sessions | Extra container | AWS ElastiCache |
| Real Jira/Confluence | Needs API keys | OAuth + REST APIs |
| Kubernetes deploy | Infra complexity | EKS + Helm charts |
| CI/CD pipeline | DevOps scope | CodePipeline / GitHub Actions |
| Observability | Extra setup | CloudWatch + X-Ray |
| Load testing | Time-consuming | Locust / k6 |

---

## Interview Checklist

### Questions You Can Now Answer

1. **"How do you build a RAG system?"**
   - Document ingestion → Chunking → Embedding → Vector store → Retrieval → Generation

2. **"How do you improve retrieval quality?"**
   - Hybrid search (vector + keyword), reranking, source filtering

3. **"How do you handle security?"**
   - JWT auth, RBAC, audit logs, input validation, PII filtering, rate limiting

4. **"How do you handle production scale?"**
   - Caching, async queues, model routing, token tracking

5. **"How do you integrate with enterprise systems?"**
   - Web connector with auth, scheduled pipelines, change detection

6. **"How do you manage conversation context?"**
   - Session-based memory, history limits, token control

7. **"How do you control costs?"**
   - Token tracking, model routing, caching, rate limiting

8. **"How do you handle sensitive data?"**
   - Input validation, PII filtering, Bedrock Guardrails (production)

9. **"How do you design data pipelines?"**
   - Event-driven vs polling, queues, idempotency, dead letter queues

10. **"How do you scale sessions?"**
    - Redis for horizontal scaling, TTL for cleanup, LRU eviction
