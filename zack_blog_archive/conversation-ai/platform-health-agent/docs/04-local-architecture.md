# Local-First Architecture — Teacher Accreditation Agentic Workflow

> **Created:** 2026-03-26  
> **Goal:** Practice agentic workflows locally, cloud-shiftable when ready  
> **Cost:** ~$5-15/month (Bedrock API usage only)  

---

## 1. Design Principle

**Keep all infrastructure local. Only call AWS for what you can't run locally — LLM and embeddings.**

```
┌──────────────────────────────────────────────────────────┐
│                LOCAL (Docker Compose)                     │
│                                                          │
│  ┌───────────┐  ┌────────────────┐  ┌───────────────┐   │
│  │ Streamlit │  │  LangGraph     │  │  Weaviate     │   │
│  │ Frontend  │→ │  Agent Backend │→ │  (Vectors)    │   │
│  │ :8501     │  │  :8000         │  │  :8080        │   │
│  └───────────┘  └───────┬────────┘  └───────────────┘   │
│                         │                                │
│                   ┌─────┴──────┐    ┌───────────────┐   │
│                   │   Tools    │    │  PostgreSQL   │   │
│                   │            │    │  (State)      │   │
│                   │ • RAG      │    │  :5432        │   │
│                   │ • DB Query │    └───────────────┘   │
│                   │ • Policy   │                         │
│                   │ • Email    │                         │
│                   │ • Escalate │                         │
│                   └─────┬──────┘                         │
│                         │                                │
└─────────────────────────┼────────────────────────────────┘
                          │ API calls only
                ┌─────────▼─────────┐
                │   AWS Bedrock     │
                │   (ap-southeast-2)│
                │                   │
                │ • Claude Sonnet   │
                │   (LLM reasoning) │
                │ • Titan Embed V2  │
                │   (embeddings)    │
                └───────────────────┘
```

---

## 2. Component Specification

### 2.1 Frontend — Streamlit

```yaml
Service: frontend
Image: python:3.12-slim + streamlit
Port: 8501
Purpose: Chat UI for interacting with the agent
Features:
  - Chat interface (message input/output)
  - Conversation history display
  - Workflow status panel (show agent's steps)
  - No auth needed (localhost only)
```

**Why Streamlit:**
- Same as the original PoC (port 8501 confirms Streamlit)
- Simple Python — no frontend framework to learn
- Easy to add workflow visualisation later

### 2.2 Agent Backend — LangGraph + FastAPI

```yaml
Service: agent-backend
Image: python:3.12-slim + langchain + langgraph + fastapi
Port: 8000
Purpose: The agentic brain — reasoning, planning, tool calling

Key Dependencies:
  - langgraph          # Agent orchestration, state machine, checkpointing
  - langchain-aws      # Bedrock LLM + embeddings integration
  - langchain-community # Weaviate vector store integration
  - fastapi + uvicorn  # API server for frontend to call
  - boto3              # AWS Bedrock API calls
  - psycopg2           # PostgreSQL for state persistence
  - pydantic           # Type-safe tool definitions

Environment Variables:
  - AWS_PROFILE=sandboxtest     # Or AWS_ACCESS_KEY_ID + SECRET
  - AWS_DEFAULT_REGION=ap-southeast-2
  - BEDROCK_MODEL_ID=anthropic.claude-sonnet-4-20250514-v1:0
  - BEDROCK_EMBED_MODEL_ID=amazon.titan-embed-text-v2:0
  - WEAVIATE_URL=http://vectordb:8080
  - POSTGRES_URL=postgresql://agent:agent@postgres:5432/agent_db
```

### 2.3 Vector Database — Weaviate

```yaml
Service: vectordb
Image: semitechnologies/weaviate:latest
Port: 8080 (HTTP), 50051 (gRPC)
Purpose: Store and retrieve document embeddings (RAG)
Persistence: ./data/weaviate:/var/lib/weaviate

Configuration:
  QUERY_DEFAULTS_LIMIT: 25
  AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED: true
  PERSISTENCE_DATA_PATH: /var/lib/weaviate
  DEFAULT_VECTORIZER_MODULE: none  # We use Bedrock Titan for embeddings
  CLUSTER_HOSTNAME: node1
```

**Why Weaviate:**
- You already know it from your RAG projects
- Runs in Docker, zero cost
- Supports hybrid search (vector + keyword) — matches original PoC's OpenSearch capability
- Easy to migrate to managed Weaviate Cloud or swap to OpenSearch later

**Cloud equivalent:** OpenSearch Serverless ($350/month) or Weaviate Cloud

### 2.4 PostgreSQL — State & History

```yaml
Service: postgres
Image: postgres:16-alpine
Port: 5432
Purpose: Conversation state, workflow checkpoints, history
Persistence: ./data/postgres:/var/lib/postgresql/data

Environment:
  POSTGRES_USER: agent
  POSTGRES_PASSWORD: agent
  POSTGRES_DB: agent_db

Tables (created by agent backend):
  - conversations:     Session tracking, user info
  - checkpoints:       LangGraph state checkpoints (workflow resume)
  - workflow_state:    Current step in multi-step workflows
  - tool_calls:        Log of every tool invocation + result
  - feedback:          User ratings / corrections
```

**Why PostgreSQL:**
- LangGraph has native PostgreSQL checkpointing support
- Structured data for workflow state (not a vector/document use case)
- Industry standard — same patterns work on RDS

**Cloud equivalent:** RDS PostgreSQL or DynamoDB

### 2.5 AWS Bedrock (Remote API Only)

```yaml
# Not a Docker service — remote API calls via boto3

LLM:
  Provider: AWS Bedrock
  Model: anthropic.claude-sonnet-4-20250514-v1:0
  # Or: anthropic.claude-3-5-sonnet-20241022-v2:0 (same as original PoC)
  Usage: Agent reasoning, planning, tool selection, response generation
  Auth: Local AWS credentials (~/.aws/credentials, profile: sandboxtest)

Embeddings:
  Provider: AWS Bedrock
  Model: amazon.titan-embed-text-v2:0
  Dimensions: 1024
  Usage: Document embedding for RAG ingestion and query
  Auth: Same credentials
```

**Cost estimate:**
| Model | Price | Typical Usage | Monthly Cost |
|---|---|---|---|
| Claude Sonnet (input) | ~$3/1M tokens | ~500K tokens/month (dev) | ~$1.50 |
| Claude Sonnet (output) | ~$15/1M tokens | ~200K tokens/month (dev) | ~$3.00 |
| Titan Embed V2 | ~$0.02/1M tokens | ~100K tokens/month | < $0.01 |
| **Total** | | | **~$5-15/month** |

---

## 3. Docker Compose

```yaml
# docker-compose.yml

version: '3.8'

services:
  frontend:
    build: ./frontend
    ports:
      - "8501:8501"
    environment:
      - AGENT_BACKEND_URL=http://agent-backend:8000
    depends_on:
      - agent-backend

  agent-backend:
    build: ./agent-backend
    ports:
      - "8000:8000"
    environment:
      - AWS_PROFILE=sandboxtest
      - AWS_DEFAULT_REGION=ap-southeast-2
      - BEDROCK_MODEL_ID=anthropic.claude-sonnet-4-20250514-v1:0
      - BEDROCK_EMBED_MODEL_ID=amazon.titan-embed-text-v2:0
      - WEAVIATE_URL=http://vectordb:8080
      - POSTGRES_URL=postgresql://agent:agent@postgres:5432/agent_db
    volumes:
      - ~/.aws:/root/.aws:ro    # Mount AWS credentials (read-only)
      - ./documents:/app/documents  # Mount docs for ingestion
    depends_on:
      - vectordb
      - postgres

  vectordb:
    image: semitechnologies/weaviate:latest
    ports:
      - "8080:8080"
      - "50051:50051"
    environment:
      QUERY_DEFAULTS_LIMIT: 25
      AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED: 'true'
      PERSISTENCE_DATA_PATH: /var/lib/weaviate
      DEFAULT_VECTORIZER_MODULE: none
      CLUSTER_HOSTNAME: node1
    volumes:
      - ./data/weaviate:/var/lib/weaviate

  postgres:
    image: postgres:16-alpine
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: agent
      POSTGRES_PASSWORD: agent
      POSTGRES_DB: agent_db
    volumes:
      - ./data/postgres:/var/lib/postgresql/data
```

---

## 4. Project Folder Structure

```
teacher-accreditation-agent/
├── docs/                          # Documentation (our md files)
│   ├── 01-context-and-direction.md
│   ├── 02-existing-poc-architecture.md
│   ├── 03-replication-blueprint.md
│   └── 04-local-architecture.md   (this file)
│
├── frontend/                      # Streamlit chat UI
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app.py
│
├── agent-backend/                 # LangGraph agent + tools
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                    # FastAPI entry point
│   ├── agent/
│   │   ├── graph.py               # LangGraph state machine
│   │   ├── state.py               # Agent state definition
│   │   └── prompts.py             # System prompts
│   ├── tools/
│   │   ├── rag_tool.py            # Knowledge base search
│   │   ├── db_tool.py             # Database queries
│   │   ├── policy_tool.py         # Accreditation policy checks
│   │   ├── email_tool.py          # Send notifications
│   │   └── escalation_tool.py     # Human handoff
│   └── ingestion/
│       └── ingest.py              # Document loader → Weaviate
│
├── documents/                     # Your PDFs, docs to ingest
│   └── (your files here)
│
├── data/                          # Docker volume mounts (gitignored)
│   ├── weaviate/
│   └── postgres/
│
├── docker-compose.yml
└── .env                           # Environment variables
```

---

## 5. Local ↔ Cloud Mapping

When ready to move to AWS, here's the swap:

| Local Component | Cloud Equivalent | Change Required |
|---|---|---|
| Docker Compose | ECS Fargate + CDK | Containerise same images |
| Streamlit (localhost) | ECS + ALB + Cognito | Add auth layer |
| Weaviate (Docker) | OpenSearch Serverless or Weaviate Cloud | Change vector store URL |
| PostgreSQL (Docker) | RDS PostgreSQL or DynamoDB | Change connection string |
| `~/.aws` credentials | IAM Task Roles | Remove volume mount, add role |
| `localhost:8501` | `https://chatbot.nesa.nsw.edu.au` | DNS + SSL |
| LangGraph agent code | **Unchanged** ✅ | Zero changes |
| Tool definitions | **Unchanged** ✅ | Zero changes |
| Prompts | **Unchanged** ✅ | Zero changes |

**The agent logic is 100% portable.** Only infrastructure wiring changes.

---

## 6. Development Workflow

```
Step 1:  docker-compose up -d                    # Start all services
Step 2:  python ingestion/ingest.py              # Load your documents
Step 3:  Open http://localhost:8501               # Chat with agent
Step 4:  Iterate on agent-backend/agent/graph.py  # Build workflows
Step 5:  docker-compose restart agent-backend     # Hot reload
```

---

## 7. Agentic Workflows

### 7.1 Overview

The PoC chatbot has **zero workflow** — it's a single-turn RAG pipeline (ask → answer → forget). We are adding 6 multi-step workflows that demonstrate real agent capabilities.

```
PoC:    Question → Answer → End (pipeline)
Agent:  Goal → Plan → Act → Observe → Decide → Act → ... → Complete (loop)
```

### 7.2 Workflow Definitions

#### Workflow 1: Accreditation Eligibility Check

**Teaches:** Branching logic — different paths based on user answers.

```
User: "I want to become a teacher in NSW. Am I eligible?"

Agent:
  1. Ask: What qualification do you have?
  2. Tool: rag_search(qualification + accreditation requirements)
  3. Ask: Which state/country was it from?
  4. Tool: policy_check(qualification, jurisdiction) → eligible?
  5. Branch:
     → Eligible: "You qualify. Here's what to do next..." → Route to Workflow 2
     → Not eligible: "Your qualification isn't recognised. Options..."
     → Unclear: Tool: escalate(case_summary) → flag for human review
```

```
LangGraph State Machine:

  [gather_info] → [search_requirements] → [check_eligibility]
                                               │
                          ┌────────────────────┼────────────────┐
                          ▼                    ▼                ▼
                    [eligible]          [not_eligible]     [unclear]
                       │                     │                │
                       ▼                     ▼                ▼
                 [route_to_wf2]      [show_options]     [escalate]
```

---

#### Workflow 2: Accreditation Application Guidance

**Teaches:** Stateful loop — iterate through checklist, track and save progress.

```
User: "Guide me through applying for Proficient Teacher accreditation"

Agent:
  1. Tool: rag_search(proficient teacher requirements)
  2. Tool: create_checklist(user, "proficient_application")
  3. Loop for each requirement:
     a. Explain what's needed
     b. Ask: "Do you have this?"
     c. Tool: update_checklist(item, status)
  4. Tool: generate_summary(checklist) → "You have 5/7 items ready"
  5. Branch:
     → All complete: "You're ready to submit. Here's how..."
     → Gaps remain: "Focus on items 3 and 6. Here's guidance..."
  6. Tool: save_progress(user, checklist) → can resume later
```

```
LangGraph State Machine:

  [get_requirements] → [create_checklist] → [check_next_item] ←──┐
                                                │                  │
                                          ┌─────┴─────┐           │
                                          ▼           ▼           │
                                     [item_done] [item_missing]   │
                                          │           │           │
                                          └─────┬─────┘           │
                                                ▼                 │
                                          [more_items?] ──YES────┘
                                                │
                                               NO
                                                ▼
                                         [generate_summary]
                                                │
                                          ┌─────┴─────┐
                                          ▼           ▼
                                    [all_done]   [gaps_remain]
                                         │           │
                                         ▼           ▼
                                    [submit]   [save_progress]
```

---

#### Workflow 3: Accreditation Maintenance / Renewal

**Teaches:** Calculation + planning — tools that compute, not just search.

```
User: "My accreditation expires in 3 months. What do I need to do?"

Agent:
  1. Ask: What's your current accreditation level?
  2. Ask: When does it expire?
  3. Tool: rag_search(maintenance requirements for level)
  4. Tool: policy_check(level, expiry_date) → calculate PD hours needed
  5. Tool: create_action_plan(user, requirements, deadline)
     → "You need 100 hours of PD, including 50 NESA-registered"
  6. Ask: "How many PD hours have you completed so far?"
  7. Tool: calculate_gap(required, completed)
     → "You need 30 more hours in 3 months. Here's a plan..."
  8. Tool: save_progress(user, plan)
```

```
LangGraph State Machine:

  [gather_level] → [gather_expiry] → [search_requirements]
                                            │
                                            ▼
                                     [calculate_needed]
                                            │
                                            ▼
                                     [ask_completed]
                                            │
                                            ▼
                                     [calculate_gap]
                                            │
                                      ┌─────┴─────┐
                                      ▼           ▼
                                 [on_track]  [behind]
                                      │           │
                                      ▼           ▼
                                 [confirm]   [create_plan]
                                                  │
                                                  ▼
                                           [save_progress]
```

---

#### Workflow 4: Document / Evidence Review Assistant

**Teaches:** LLM-as-judge — agent evaluates, not just retrieves.

```
User: "I have evidence for Standard 3. Can you help me check if it's suitable?"

Agent:
  1. Tool: rag_search(Standard 3 Proficient level descriptors)
  2. Present: "Standard 3 requires evidence of X, Y, Z"
  3. Ask: "Describe your evidence briefly"
  4. Tool: evaluate_evidence(user_description, standard_requirements)
     → LLM assesses alignment between evidence and standard
  5. Branch:
     → Strong: "This looks suitable. It addresses..."
     → Partial: "Covers X but need more evidence for Y"
     → Weak: "Doesn't clearly demonstrate the standard. Consider..."
  6. Tool: update_checklist(standard_3, status, notes)
```

```
LangGraph State Machine:

  [get_standard] → [search_descriptors] → [present_requirements]
                                                  │
                                                  ▼
                                           [ask_evidence]
                                                  │
                                                  ▼
                                         [evaluate_evidence]
                                                  │
                                     ┌────────────┼────────────┐
                                     ▼            ▼            ▼
                               [strong]      [partial]      [weak]
                                  │              │            │
                                  ▼              ▼            ▼
                              [approve]    [suggest_more] [guide_redo]
                                  │              │            │
                                  └──────────────┴────────────┘
                                                 │
                                                 ▼
                                        [update_checklist]
```

---

#### Workflow 5: Policy Q&A with Follow-Up Actions

**Teaches:** RAG → Action chain — answer leads to generated outputs (templates, plans).

```
User: "A teacher at my school hasn't maintained their accreditation. What happens?"

Agent:
  1. Tool: rag_search(lapsed accreditation consequences)
  2. Provide policy answer
  3. Ask: "Would you like me to outline the steps you need to take as principal?"
  4. Tool: rag_search(principal responsibilities lapsed accreditation)
  5. Tool: create_action_plan(role=principal, scenario=lapsed)
     → Step 1: Notify the teacher in writing
     → Step 2: Report to NESA within X days
     → Step 3: ...
  6. Ask: "Should I draft a notification template?"
  7. Tool: generate_template(notification_type=lapsed_accreditation)
```

```
LangGraph State Machine:

  [search_policy] → [provide_answer] → [offer_action_plan]
                                              │
                                        ┌─────┴─────┐
                                       YES          NO → [end]
                                        │
                                        ▼
                                 [search_role_steps]
                                        │
                                        ▼
                                 [create_action_plan]
                                        │
                                        ▼
                                 [offer_template]
                                        │
                                  ┌─────┴─────┐
                                 YES          NO → [end]
                                  │
                                  ▼
                           [generate_template] → [end]
```

---

#### Workflow 6: Multi-Role Routing (Orchestrator)

**Teaches:** Sub-graph routing — agent orchestrates different workflow paths based on user role.

```
User: "I need help with accreditation"

Agent:
  1. Ask: "What's your role?"
     → Teacher / Principal / HR / TAA
  2. Branch by role:
     → Teacher: "What stage are you at?" → Route to WF 1, 2, 3, or 4
     → Principal: "What help do you need?" → Supervision, reporting, lapsed
     → HR: "New hire or existing staff?" → Verification workflow
     → TAA: "Processing an application?" → Assessment workflow
  3. Each branch has its own sub-workflow with role-specific tools
```

```
LangGraph State Machine:

                         [identify_role]
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
         [teacher]       [principal]       [hr / taa]
              │                │                │
         [ask_stage]     [ask_need]        [ask_scenario]
              │                │                │
        ┌─────┼─────┐   ┌─────┼─────┐          ▼
        ▼     ▼     ▼   ▼     ▼     ▼    [role_specific_wf]
      [WF1] [WF2] [WF3] [WF5] [WF5] [WF5]
```

---

### 7.3 Tools Required Across All Workflows

| Tool | Function | Used In | Complexity |
|---|---|---|---|
| `rag_search` | Search Weaviate knowledge base | WF 1-6 | Simple |
| `policy_check` | Evaluate business rules (eligibility, deadlines) | WF 1, 3 | Medium |
| `create_checklist` | Create a tracked checklist for a user | WF 2, 4 | Medium |
| `update_checklist` | Mark items complete/incomplete with notes | WF 2, 4 | Simple |
| `calculate_gap` | Compute what's missing (hours, evidence, docs) | WF 3 | Medium |
| `create_action_plan` | Generate step-by-step plan with deadlines | WF 3, 5 | Medium |
| `generate_template` | Draft letters/notifications from templates | WF 5 | Medium |
| `evaluate_evidence` | LLM assesses evidence against standards | WF 4 | Medium |
| `generate_summary` | Summarise progress/status for user | WF 2, 3 | Simple |
| `save_progress` | Persist workflow state to PostgreSQL | WF 2, 3, 4 | Medium |
| `escalate` | Flag for human review with context summary | WF 1, 6 | Simple |

### 7.4 What Each Workflow Teaches

| Workflow | Primary Agent Skill |
|---|---|
| 1. Eligibility Check | **Branching logic** — different paths from decisions |
| 2. Application Guidance | **Stateful loop** — iterate, track, resume |
| 3. Maintenance/Renewal | **Calculation + planning** — tools that compute |
| 4. Evidence Review | **LLM-as-judge** — agent evaluates, not just retrieves |
| 5. Policy + Actions | **RAG → Action chain** — answer leads to outputs |
| 6. Multi-Role Routing | **Sub-graph orchestration** — route to sub-workflows |

### 7.5 Suggested Build Order

```
Phase 1 (Foundation):   WF1 (Eligibility)  — learn branching + basic tools
Phase 2 (State):        WF2 (Application)  — learn loops + state + checkpointing
Phase 3 (Compute):      WF3 (Maintenance)  — learn calculation tools
Phase 4 (Evaluation):   WF4 (Evidence)     — learn LLM-as-judge pattern
Phase 5 (Generation):   WF5 (Policy+Action)— learn template generation
Phase 6 (Orchestration): WF6 (Router)      — wire all workflows together
```

---

## 8. Production Patterns (Built Into Local Design)

### 8.1 What's Included

We bake production-grade patterns into the local design from day one. These are **Python code patterns**, not extra infrastructure.

### 8.2 Protection Layer (Must Have — Simple)

Built into LangGraph and tool layer with minimal code:

```python
# LangGraph config — prevents infinite loops
app = graph.compile(checkpointer=postgres_saver)
config = {"recursion_limit": 25}  # Max 25 steps per workflow

# Per-tool retry with backoff
@retry(max_attempts=3, backoff=exponential(base=2))
async def rag_search(query: str) -> SearchResult: ...

# Per-tool timeout
result = await asyncio.wait_for(tool.execute(params), timeout=10)

# Loop detection — break if same tool+input called twice
seen = set()
key = hash(f"{tool_name}:{tool_input}")
if key in seen: break  # Detected loop
seen.add(key)

# Token budget — stop if conversation exceeds limit
if state.total_tokens > 50_000: return "Budget exceeded. Escalating."
```

| Pattern | Implementation | Effort |
|---|---|---|
| Max iterations | `recursion_limit=25` in LangGraph config | 1 line |
| Max retries per tool | Retry decorator with counter | 10 lines |
| Tool timeout | `asyncio.wait_for(tool(), timeout=10)` | 5 lines |
| Global workflow timeout | LangGraph `recursion_limit` | 1 line |
| Loop detection | Hash tool+input, check seen set | 20 lines |
| Token budget | Count from Bedrock response, accumulate | 20 lines |
| Read/write tool tags | Metadata on tool definition | 5 lines |

### 8.3 Resilience Layer (Should Have — Medium)

```python
# Circuit breaker per tool (using pybreaker or custom)
class ToolCircuitBreaker:
    def __init__(self, failure_threshold=3, recovery_timeout=60):
        self.failures = 0
        self.state = "closed"  # closed → open → half-open
    
    async def call(self, tool, params):
        if self.state == "open":
            return fallback_response(tool)
        try:
            result = await tool(params)
            self.failures = 0
            return result
        except Exception:
            self.failures += 1
            if self.failures >= self.failure_threshold:
                self.state = "open"
            raise

# Graceful degradation
async def rag_search_with_fallback(query):
    try:
        return await rag_search(query)
    except Exception:
        return ToolResult(
            success=False,
            message="Knowledge base unavailable. Please try again or escalate."
        )

# Confirmation gate on write operations
async def create_case(params):
    if tool_metadata.is_write:
        return PendingApproval(
            action="Create accreditation case",
            details=params,
            message="I'm about to create a case. Shall I proceed?"
        )
```

| Pattern | Implementation | Effort |
|---|---|---|
| Circuit breaker | State machine per tool or `pybreaker` lib | 50 lines or library |
| Graceful degradation | Try/except → fallback message | 30 min |
| Confirmation gates | Tool returns `PendingApproval` → LangGraph waits for user | 1-2 hours |
| Checkpointing | `PostgresSaver` — built into LangGraph | 1-2 hours |
| Confidence threshold | LLM self-rates → branch if low | 1 hour |

### 8.4 Observability Layer (Should Have — Medium)

```python
# Every tool call is logged to PostgreSQL
@log_tool_call  # Decorator logs to tool_calls table
async def rag_search(query: str) -> SearchResult:
    ...

# tool_calls table captures:
# - trace_id (conversation UUID)
# - timestamp
# - tool_name
# - input_params
# - output_result
# - latency_ms
# - tokens_used
# - success/failure
```

```sql
-- PostgreSQL tables for observability
CREATE TABLE conversations (
    id UUID PRIMARY KEY,
    trace_id UUID UNIQUE,
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    total_tokens INT,
    total_tool_calls INT,
    workflow_type TEXT,
    final_status TEXT  -- completed, escalated, timed_out, error
);

CREATE TABLE tool_call_log (
    id SERIAL PRIMARY KEY,
    trace_id UUID REFERENCES conversations(trace_id),
    step_number INT,
    tool_name TEXT,
    input_params JSONB,
    output_result JSONB,
    latency_ms INT,
    tokens_used INT,
    success BOOLEAN,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

| Pattern | Implementation | Effort |
|---|---|---|
| Trace ID per conversation | `uuid4()` in state | 5 lines |
| Full tool call logging | Decorator → PostgreSQL insert | 2 hours |
| Source attribution | Weaviate returns doc metadata with results | Built-in |
| Structured tool outputs | Pydantic models for all tool returns | Part of design |
| Cost tracking | Sum tokens per conversation | 20 lines |
| Latency tracking | `time.time()` around tool calls | 10 lines |

### 8.5 UX Layer (Should Have — Medium)

```python
# Streaming responses via FastAPI
@app.post("/chat")
async def chat(request: ChatRequest):
    async def stream():
        async for event in agent.astream_events(input, config):
            if event["event"] == "on_tool_start":
                yield f"🔍 Searching knowledge base...\n"
            elif event["event"] == "on_tool_end":
                yield f"✅ Found relevant information\n"
            elif event["event"] == "on_chat_model_stream":
                yield event["data"]["chunk"].content
    return StreamingResponse(stream(), media_type="text/event-stream")
```

| Pattern | Implementation | Effort |
|---|---|---|
| Streaming responses | FastAPI `StreamingResponse` + LangGraph `astream_events` | 2-3 hours |
| Step-by-step progress | Streamlit `st.status()` showing agent steps | 1-2 hours |
| Confirmation dialogs | Streamlit button for write-tool approval | 1 hour |

### 8.6 What We Skip (Not Needed Locally)

| Pattern | Why Skip | Add When |
|---|---|---|
| Rate limiting per user | Single user locally | Multi-user deployment |
| Async approval notifications | No team to approve | Real team usage |
| Regression CI pipeline | Manual testing ok for learning | Team development |
| A/B testing | Need real traffic | Production optimisation |
| Bedrock Guardrails service | Prompt-level guardrails sufficient | Public-facing |
| Cost alert notifications | Check AWS bill manually | Production budget |

### 8.7 Architecture with Production Patterns

```
┌─────────────────────────────────────────────────┐
│              Streamlit Frontend                   │
│  • Streaming responses (real-time progress)      │
│  • Step-by-step status UI                        │
│  • Confirmation dialogs for write actions        │
└────────────────────┬────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────┐
│              FastAPI Backend                      │
│  • Trace ID per conversation                     │
│  • Token budget enforcement                      │
│  • StreamingResponse for real-time output         │
└────────────────────┬────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────┐
│              LangGraph Agent                     │
│  • recursion_limit=25 (loop protection)          │
│  • PostgresSaver (checkpointing)                 │
│  • Loop detection (hash tool+input)              │
│  • Confidence-based branching                    │
│  • Read/Write tool classification                │
└────────────────────┬────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────┐
│              Tool Layer                          │
│  • Max 3 retries + exponential backoff           │
│  • 10-second timeout per tool call               │
│  • Circuit breaker (3 failures → open)           │
│  • Structured Pydantic outputs                   │
│  • Source attribution on RAG results             │
│  • Confirmation gate on write tools              │
│  • @log_tool_call decorator (trace logging)      │
└────────────────────┬────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────┐
│              PostgreSQL                          │
│  • conversations table (session tracking)        │
│  • checkpoints table (LangGraph state)           │
│  • tool_call_log table (full trace)              │
│  • workflow_state table (resume capability)       │
│  • escalation_queue table (human handoff)        │
└─────────────────────────────────────────────────┘
```

---

## 9. What This Enables (Agentic Learning Goals)

| Skill | How You'll Practice It |
|---|---|
| **LangGraph** | `agent/graph.py` — state machine with loops, branches, checkpoints |
| **Tool Calling** | `tools/*.py` — agent decides which tool, when, with what params |
| **State Management** | PostgreSQL checkpoints — resume workflows after failures |
| **RAG as a Tool** | `tools/rag_tool.py` — your Weaviate KB is just one tool among many |
| **Multi-Step Workflows** | Agent handles accreditation processes step-by-step |
| **Human-in-the-Loop** | `tools/escalation_tool.py` — pause workflow, ask human, resume |
| **Error Recovery** | Agent retries, compensates, or escalates on tool failures |
| **MCP (later)** | Expose tools via MCP protocol — standard tool discovery |
| **Evaluation (later)** | Log tool calls to PostgreSQL → measure accuracy, completion |
