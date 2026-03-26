# Implementation Plan — Step-by-Step Build Guide

> **Created:** 2026-03-26  
> **Approach:** Build incrementally, explain every step, verify it works before moving on  

---

## Pre-Build Checklist ✅

| Item | Status |
|---|---|
| Docker (4 services configured) | ✅ Ready |
| .env (17 variables — Bedrock, Confluence, Blog) | ✅ Ready |
| AWS Bedrock Titan Embed V2 | ✅ Verified |
| AWS Bedrock Claude Sonnet 4 | ✅ Verified |
| Blog (zackblog.work) | ✅ HTTP 200 |
| Confluence (8 pages, API token) | ✅ Verified |
| PDFs (documents/ folder) | ✅ Files present |
| Ports 8501, 8080 | ✅ Available |

---

## Build Order (7 Steps)

Each step produces a **working, testable result** before moving to the next.

```
Step 1: Infrastructure     → docker-compose up (Weaviate + Postgres running)
Step 2: Data Ingestion      → Documents loaded into Weaviate (RAG ready)
Step 3: RAG Tool            → Agent can search knowledge base
Step 4: Basic Agent         → LangGraph agent answers questions using RAG
Step 5: Tool Calling        → Agent uses multiple tools (RAG + policy + checklist)
Step 6: Workflow 1          → Full eligibility check with branching
Step 7: Production Patterns → Streaming, circuit breaker, logging
```

---

### Step 1: Infrastructure — Get Docker Services Running

**What:** Start Weaviate (vector DB) and PostgreSQL (state). No code changes needed.

**Why:** We need the databases running before we can load data or run the agent.

**Test:** Weaviate health endpoint responds, PostgreSQL accepts connections.

```bash
docker compose up -d vectordb postgres
curl http://localhost:8080/v1/.well-known/ready  # Weaviate
docker exec -it $(docker ps -qf name=postgres) pg_isready  # PostgreSQL
```

---

### Step 2: Data Ingestion — Populate Knowledge Base

**What:** Build the ingestion pipeline that loads your 3 data sources into Weaviate.

**Why:** The RAG tool needs data to search. Without this, the agent has no knowledge.

**Components to build:**
```
ingestion/ingest.py
├── load_pdfs()         — Read PDFs from ./documents/
├── crawl_blog()        — Fetch pages from zackblog.work
├── crawl_confluence()  — Fetch 8 pages via Atlassian API
├── chunk_documents()   — Split into overlapping chunks
├── embed_chunks()      — Call Bedrock Titan for embeddings
└── store_in_weaviate() — Upsert vectors + metadata
```

**Key concepts explained:**
- **Chunking:** Documents are too long for LLM context. We split into ~500-token chunks with overlap so no information is lost at chunk boundaries.
- **Embedding:** Each chunk is converted to a 1024-dimension vector by Titan. Similar content = similar vectors = found by search.
- **Metadata:** Each chunk stores its source (blog/confluence/pdf), title, and URL so the agent can cite sources.

**Test:** Query Weaviate directly — search "AWS" returns relevant chunks.

---

### Step 3: RAG Tool — Knowledge Base Search

**What:** Implement `tools/rag_tool.py` so the agent can search Weaviate.

**Why:** This is the agent's primary knowledge source. Every workflow needs it.

**How it works:**
```
User question: "What is Bedrock integration?"
  ↓
1. Embed the question using Bedrock Titan → 1024-dim vector
2. Search Weaviate for nearest vectors (cosine similarity)
3. Return top-5 chunks with content, source, and score
  ↓
Agent receives: [{content: "...", source: "confluence/page-03", score: 0.92}, ...]
```

**Test:** Call the tool directly from Python — returns relevant results with sources.

---

### Step 4: Basic Agent — LangGraph + RAG

**What:** Wire LangGraph to use Claude (Bedrock) + RAG tool to answer questions.

**Why:** This is the minimum viable agent — it can think and search. Foundation for everything else.

**How LangGraph works (explained):**

```python
# LangGraph is a state machine. Think of it as a flowchart in code.
# 
# State: A dictionary that flows through the graph. Every node can read and update it.
# Node:  A function that does one thing (call LLM, call tool, make decision).
# Edge:  Connects nodes. Can be conditional (if X → go to A, else → go to B).

# Simple agent graph:
#
#   [start] → [call_llm] → [should_use_tool?]
#                                │
#                          ┌─────┴─────┐
#                         YES          NO
#                          │           │
#                          ▼           ▼
#                     [call_tool]   [respond]
#                          │
#                          ▼
#                     [call_llm]  ← loops back (agent sees tool result, decides next)

graph = StateGraph(AgentState)
graph.add_node("agent", call_llm)          # LLM decides what to do
graph.add_node("tools", execute_tool)      # Run the chosen tool
graph.add_edge("agent", should_continue)   # Conditional: tool or respond?
graph.add_edge("tools", "agent")           # After tool, go back to LLM
```

**What you'll see:**
```
User: "What does the Health Analyzer use Bedrock for?"
Agent thinks: I need to search the knowledge base for this.
Agent calls: rag_search("Bedrock integration Health Analyzer")
Tool returns: [relevant chunks from your Confluence page 03]
Agent responds: "Based on your documentation, the Health Analyzer uses Bedrock for..."
```

**Test:** Chat via FastAPI endpoint — agent searches KB and answers with citations.

---

### Step 5: Tool Calling — Multiple Tools

**What:** Add policy_tool, db_tool, escalation_tool. Agent picks which tool to use.

**Why:** This is the core agent skill — reasoning about WHICH tool to use and WHEN.

**How tool calling works (explained):**

```python
# Tools are just Python functions with descriptions.
# The LLM reads the descriptions and decides which to call.

@tool("rag_search", description="Search knowledge base for information")
async def rag_search(query: str) -> SearchResult: ...

@tool("check_eligibility", description="Check if requirements are met")
async def check_eligibility(qualification: str, level: str) -> PolicyResult: ...

@tool("create_checklist", description="Create a tracked checklist")
async def create_checklist(user_id: str, type: str) -> Checklist: ...

# The LLM sees these descriptions and thinks:
# "User asked about eligibility → I should call check_eligibility"
# "User asked a general question → I should call rag_search"
# This is NOT hardcoded logic. The LLM DECIDES based on the conversation.
```

**What you'll see:**
```
User: "Am I eligible to teach in NSW with a UK teaching degree?"
Agent thinks: This is an eligibility question. I need to check policy.
Agent calls: rag_search("eligibility UK teaching degree NSW")
Agent calls: check_eligibility(qualification="UK teaching degree", jurisdiction="UK")
Agent responds: "Based on NESA guidelines, a UK teaching degree may be recognised..."
```

**Test:** Ask different types of questions — verify agent picks the right tool each time.

---

### Step 6: Workflow 1 — Eligibility Check (Full Agentic Workflow)

**What:** Implement the complete eligibility check workflow with branching and state.

**Why:** This is where it stops being a chatbot and becomes an agent. Multi-turn, stateful, with decisions.

**How the workflow works (explained):**

```python
# This is a LangGraph state machine with multiple nodes and conditional edges.
# The agent maintains STATE across turns — it remembers what happened.

# State tracks:
state = {
    "messages": [...],              # Full conversation
    "qualification": None,          # Gathered from user
    "jurisdiction": None,           # Gathered from user
    "eligibility_result": None,     # From policy_check tool
    "workflow_step": 0,             # Where we are in the process
}

# The graph:
# [gather_info] → Did we get qualification AND jurisdiction?
#      │                    │
#     NO                   YES
#      │                    │
#      ▼                    ▼
# [ask_user]          [check_eligibility]
#      │                    │
#      └──→ loop       ┌────┴────┐
#                       ▼         ▼
#                  [eligible]  [not_eligible]

# KEY INSIGHT: The agent doesn't just answer — it DRIVES the conversation.
# It asks questions, gathers data, makes decisions, and acts.
```

**What you'll see (multi-turn):**
```
User: "Can I teach in NSW?"
Agent: "I'd be happy to help check your eligibility. What teaching 
        qualification do you have?"  ← Agent drives the conversation

User: "Bachelor of Education from University of London"
Agent: [Tool: rag_search("UK Bachelor of Education NSW recognition")]
       [Tool: check_eligibility("Bachelor of Education", "UK")]
       "A UK Bachelor of Education is generally recognised in NSW. 
        You would need to apply for Provisional accreditation. 
        Would you like me to create a checklist of what you need?"  ← Offers next workflow

User: "Yes please"
Agent: [Tool: create_checklist(user, "provisional_application")]
       "Here's your checklist:
        ☐ NESA application form
        ☐ Certified qualification transcripts
        ☐ Working With Children Check
        ..."
```

**Test:** Full multi-turn conversation — agent maintains state, branches correctly, offers next steps.

---

### Step 7: Production Patterns — Streaming, Logging, Resilience

**What:** Add streaming UI, tool call logging, circuit breaker, checkpoint resume.

**Why:** Makes the agent feel responsive and reliable. Teaches production patterns.

**What changes:**
- Frontend shows "🔍 Searching..." as agent works (streaming)
- Every tool call logged to PostgreSQL with latency and result
- Failed tools retry 3 times then circuit-break
- Conversation state saved — can resume after browser refresh

**Test:** Refresh page mid-conversation → agent resumes from checkpoint.

---

## Summary

| Step | What You Get | What You Learn |
|---|---|---|
| 1. Infrastructure | Weaviate + Postgres running | Docker Compose orchestration |
| 2. Ingestion | Knowledge base populated | Chunking, embedding, vector storage |
| 3. RAG Tool | Searchable knowledge | Vector similarity search |
| 4. Basic Agent | LLM + RAG answering questions | LangGraph basics, state machine |
| 5. Multi-Tool | Agent picks which tool to use | Tool calling, LLM reasoning |
| 6. Workflow | Full multi-step eligibility check | Branching, state, multi-turn |
| 7. Production | Streaming, logging, resilience | Real-world agent patterns |

Each step builds on the previous. Each step is testable. Each step is explained.
