# Tutorial Step 1: Infrastructure — Docker Compose, Weaviate & PostgreSQL

> **Goal:** Get the database services running so we have somewhere to store data  
> **Time:** ~10 minutes  
> **Prerequisites:** Docker installed and running  

---

## What We're Building in This Step

Before we can build an AI agent, we need two databases running:

1. **Weaviate** — a vector database that stores our documents as searchable embeddings
2. **PostgreSQL** — a traditional database that stores conversation state, tool logs, and checklists

Think of it like building a house — this step is pouring the foundation.

```
┌────────────────────────────────────────┐
│           What We Build Here           │
│                                        │
│   Weaviate (port 8080)                 │
│   └── Stores document embeddings       │
│   └── Enables semantic search          │
│   └── "Where the knowledge lives"      │
│                                        │
│   PostgreSQL (port 5432)               │
│   └── Stores conversation history      │
│   └── Stores workflow state            │
│   └── Stores tool call logs            │
│   └── "Where the memory lives"         │
└────────────────────────────────────────┘
```

---

## Key Concepts (Explained for Beginners)

### What Is Docker Compose?

Docker Compose is a tool that lets you run multiple applications (called "services") together with one command. Instead of manually starting Weaviate, then PostgreSQL, then checking if they're healthy... you write a `docker-compose.yml` file that describes all services, and Docker does the rest.

```bash
docker compose up -d    # Start everything in background
docker compose down     # Stop everything
docker compose ps       # See what's running
```

### What Is a Vector Database (Weaviate)?

A normal database stores data in rows and columns (like a spreadsheet). A **vector database** stores data as **embeddings** — lists of numbers that represent the *meaning* of text.

**Example:**
```
Text: "Teacher accreditation requirements in NSW"
Embedding: [0.023, -0.041, 0.089, ... 1024 numbers total]

Text: "What do I need to become a teacher in New South Wales?"  
Embedding: [0.025, -0.039, 0.091, ... similar numbers!]
```

Even though these two sentences use different words, their embeddings are **similar** because they mean similar things. This is how the AI finds relevant documents — it searches by meaning, not keywords.

**Why Weaviate specifically?**
- Open source, runs in Docker (free)
- You've used it before in your RAG projects
- Supports hybrid search (vector + keyword combined)
- The original PoC used OpenSearch Serverless ($350/month) — Weaviate does the same thing for free

### What Is PostgreSQL?

PostgreSQL is a traditional relational database — it stores structured data in tables with rows and columns. We use it for things that need exact lookups, not semantic search:

- "Show me conversation #abc123" → exact lookup
- "What tools did the agent call in this session?" → structured query
- "Resume the workflow from step 4" → state retrieval

### Why Two Databases?

| Data Type | Best Database | Why |
|---|---|---|
| Documents, knowledge | Weaviate (vectors) | Need semantic/meaning-based search |
| Conversations, state, logs | PostgreSQL (relational) | Need exact lookups, joins, transactions |

Using one database for everything would be like using a screwdriver for nails — it works badly.

---

## The Docker Compose File (Explained)

Here's our `docker-compose.yml` with every line explained:

```yaml
services:
  # --- Vector Database: stores document embeddings for RAG search ---
  vectordb:
    image: semitechnologies/weaviate:latest    # Official Weaviate Docker image
    ports:
      - "8080:8080"    # HTTP API — we call this to search/insert
      - "50051:50051"  # gRPC — faster protocol, used by Python client
    environment:
      QUERY_DEFAULTS_LIMIT: 25                           # Return max 25 results per query
      AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED: 'true'    # No auth needed (localhost only)
      PERSISTENCE_DATA_PATH: /var/lib/weaviate           # Where data is stored inside container
      DEFAULT_VECTORIZER_MODULE: none                    # We handle embeddings ourselves (via Bedrock)
      CLUSTER_HOSTNAME: node1                            # Required even for single-node
    volumes:
      - ./data/weaviate:/var/lib/weaviate  # Persist data to local disk (survives restart)
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/v1/.well-known/ready"]
      interval: 10s   # Check every 10 seconds
      timeout: 5s     # Fail if no response in 5 seconds
      retries: 5      # Mark unhealthy after 5 failures
    restart: unless-stopped  # Auto-restart if it crashes

  # --- Relational Database: stores conversations, state, logs ---
  postgres:
    image: postgres:16-alpine    # Official PostgreSQL (Alpine = smaller image)
    ports:
      - "5432:5432"    # Standard PostgreSQL port
    environment:
      POSTGRES_USER: agent         # Database username
      POSTGRES_PASSWORD: agent     # Database password (fine for local dev)
      POSTGRES_DB: agent_db        # Database name
    volumes:
      - ./data/postgres:/var/lib/postgresql/data                       # Persist data
      - ./agent-backend/init.sql:/docker-entrypoint-initdb.d/init.sql:ro  # Auto-create tables
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U agent -d agent_db"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
```

**Key things to notice:**
- `volumes` make data persist — if you restart Docker, your data is still there
- `healthcheck` lets Docker know when the service is ready — other services wait for this
- `DEFAULT_VECTORIZER_MODULE: none` — we don't use Weaviate's built-in embeddings because we use AWS Bedrock Titan instead (same model as the original PoC)

---

## PostgreSQL Tables (Explained)

We create 6 tables. Here's what each one does:

### `conversations` — One row per chat session
```sql
CREATE TABLE conversations (
    id UUID PRIMARY KEY,           -- Unique ID for this conversation
    trace_id UUID UNIQUE NOT NULL, -- Used to link all related data together
    started_at TIMESTAMP,          -- When the user started chatting
    ended_at TIMESTAMP,            -- When the conversation ended
    total_tokens INT,              -- How many LLM tokens were used (cost tracking)
    total_tool_calls INT,          -- How many tools the agent called
    workflow_type TEXT,             -- Which workflow was used (eligibility, maintenance, etc.)
    final_status TEXT              -- completed, escalated, timed_out, error
);
```
**Why:** Every conversation gets a trace_id. We use this to find all tool calls, state, and escalations for that conversation.

### `tool_call_log` — Every tool the agent uses
```sql
CREATE TABLE tool_call_log (
    id SERIAL PRIMARY KEY,
    trace_id UUID,              -- Links to the conversation
    step_number INT,            -- 1st tool call, 2nd tool call, etc.
    tool_name TEXT,             -- "rag_search", "check_eligibility", etc.
    input_params JSONB,         -- What was passed to the tool
    output_result JSONB,        -- What the tool returned
    latency_ms INT,             -- How long the tool took (milliseconds)
    tokens_used INT,            -- LLM tokens consumed
    success BOOLEAN,            -- Did it work?
    error_message TEXT,         -- If not, what went wrong?
    created_at TIMESTAMP
);
```
**Why:** This is our **observability** layer. If the agent gives a wrong answer, we can trace exactly what it searched, what it found, and what it decided. Without this, debugging agents is nearly impossible.

### `workflow_state` — Resume multi-step workflows
```sql
CREATE TABLE workflow_state (
    trace_id UUID,
    workflow_type TEXT,       -- "eligibility_check", "application_guidance"
    current_step INT,         -- Which step we're on (e.g., step 3 of 7)
    state_data JSONB,         -- All collected data so far (qualification, jurisdiction, etc.)
    updated_at TIMESTAMP
);
```
**Why:** If the user closes their browser mid-workflow, we can resume from exactly where they left off. The `state_data` JSONB stores everything the agent has gathered so far.

### `escalation_queue` — Human handoff
```sql
CREATE TABLE escalation_queue (
    trace_id UUID,
    reason TEXT,               -- "Low confidence", "User requested human"
    context_summary TEXT,      -- Summary of conversation so far
    priority TEXT,             -- low, medium, high
    status TEXT,               -- pending, acknowledged
    created_at TIMESTAMP
);
```
**Why:** When the agent can't help, it doesn't just say "I don't know." It creates an escalation with full context so a human can pick up where the agent left off.

### `checklists` + `checklist_items` — Track requirements
```sql
CREATE TABLE checklists (
    id UUID PRIMARY KEY,
    title TEXT,                -- "Proficient Teacher Application Checklist"
    checklist_type TEXT        -- "proficient_application", "maintenance"
);

CREATE TABLE checklist_items (
    checklist_id UUID,         -- Links to parent checklist
    description TEXT,           -- "Working With Children Check"
    status TEXT,               -- pending, complete, not_applicable
    notes TEXT                 -- "Submitted 2026-01-15, awaiting confirmation"
);
```
**Why:** The agent creates checklists for users and tracks their progress. This is a real *action* — not just answering a question, but creating something persistent the user can come back to.

---

## How to Run It

### Start the services
```bash
cd ~/zz/Documents/conversation-ai/teacher-accreditation-agent
docker compose up -d vectordb postgres
```

### Verify everything is healthy
```bash
# Check containers are running
docker compose ps

# Test Weaviate
curl http://localhost:8080/v1/meta | python3 -m json.tool

# Test PostgreSQL
docker compose exec -T postgres psql -U agent -d agent_db -c "SELECT tablename FROM pg_tables WHERE schemaname = 'public';"
```

### Expected output
```
Weaviate:   Version 1.35.16, ready on port 8080
PostgreSQL: Version 16.13, 6 tables created, ready on port 5432
```

---

## What We Have Now

```
BEFORE this step:        AFTER this step:
──────────────────       ─────────────────
Empty Docker             Weaviate running (vector search ready)
No databases             PostgreSQL running (6 tables for state/logs)
Nothing to search        Ready to accept documents (Step 2)
No memory                Ready to store conversations
```

---

## Troubleshooting

| Problem | Solution |
|---|---|
| Port 8080 already in use | `lsof -i :8080` to find what's using it, stop it or change port in docker-compose.yml |
| Port 5432 already in use | Same approach — `lsof -i :5432` |
| Weaviate won't start | Check `docker compose logs vectordb` for errors |
| PostgreSQL tables missing | Tables auto-create on first start. If data/ exists from a previous run, delete `./data/postgres/` and restart |
| Containers keep restarting | Check `docker compose logs` — usually a config issue |

---

## Next Step

**Step 2: Data Ingestion** — we'll build a Python script that loads your blog posts, Confluence pages, and PDFs into Weaviate so the agent has knowledge to search.
