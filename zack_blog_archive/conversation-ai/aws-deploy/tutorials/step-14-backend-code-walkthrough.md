# Step 14: Backend Code Walkthrough — FastAPI + LangGraph Agent

> **Target audience:** Newcomers to Python, FastAPI, and LangGraph.
> **Time to read:** ~25 minutes
>
> This tutorial walks through every backend source file so you understand *what each piece does* and *how they connect*. By the end you'll be able to trace a user message from the HTTP request all the way to the AI response.

---

## Table of Contents

| Section | File(s) | What You'll Learn |
|---------|---------|-------------------|
| [14.1 Configuration](#141-configuration-configpy) | `config.py` | Environment-driven settings |
| [14.2 The Agent Brain](#142-the-agent-brain--langgraph-graphpy) | `agent/graph.py` | Nodes, edges, routing, tool binding |
| [14.3 Agent State](#143-agent-state-statepy) | `agent/state.py` | Shared state dictionary |
| [14.4 System Prompts](#144-system-prompts-promptspy) | `agent/prompts.py` | How prompt engineering shapes behavior |
| [14.5 Tools](#145-tools--the-agents-hands) | `tools/*.py` | KB search, DynamoDB, escalation, history, incidents |
| [14.6 Incident Triage Workflow](#146-incident-triage-workflow-incident_triagepy) | `agent/workflows/incident_triage.py` | Structured sub-graph |
| [14.7 API Server](#147-api-server-mainpy) | `main.py` | FastAPI endpoints, SSE streaming, sessions |
| [14.8 Docker](#148-docker-dockerfile--requirementstxt) | `Dockerfile`, `requirements.txt` | Packaging for deployment |
| [14.9 Local vs AWS Differences](#149-local-vs-aws-differences) | — | Side-by-side comparison table |

---

## 14.1 Configuration (`config.py`)

Think of `config.py` as the **settings panel** for the entire backend. Instead of hard-coding values like database names or AI model IDs, we read them from *environment variables*. This means the same code runs locally (with a `.env` file) and on AWS (where ECS injects the values automatically).

```python
"""AWS deployment configuration.

All values are injected via ECS task environment variables.
Locally, use a .env file for testing.
"""
import os

# AWS Region
AWS_REGION = os.getenv("AWS_REGION", "ap-southeast-2")

# Bedrock LLM
BEDROCK_MODEL_ID = os.getenv(
    "BEDROCK_MODEL_ID",
    "apac.anthropic.claude-sonnet-4-20250514-v1:0"
)

# Bedrock Knowledge Base
KNOWLEDGE_BASE_ID = os.getenv("KNOWLEDGE_BASE_ID", "")

# DynamoDB tables
DYNAMODB_CHECKLISTS_TABLE = os.getenv("DYNAMODB_CHECKLISTS_TABLE", "platform-health-checklists")
DYNAMODB_ESCALATIONS_TABLE = os.getenv("DYNAMODB_ESCALATIONS_TABLE", "platform-health-escalations")

# EFS mount path for chat history
EFS_MOUNT_PATH = os.getenv("EFS_MOUNT_PATH", "/mnt/efs")
SESSIONS_DIR = os.path.join(EFS_MOUNT_PATH, "sessions")

# Agent settings
RECURSION_LIMIT = int(os.getenv("RECURSION_LIMIT", "25"))
```

### What each variable controls

| Variable | Default | Purpose |
|----------|---------|---------|
| `AWS_REGION` | `ap-southeast-2` | Which AWS region to call for Bedrock, DynamoDB, etc. |
| `BEDROCK_MODEL_ID` | `apac.anthropic.claude-sonnet-4-20250514-v1:0` | The Claude model the agent talks to. The `apac.` prefix routes to the Asia-Pacific inference profile. |
| `KNOWLEDGE_BASE_ID` | `""` (empty) | The Bedrock Knowledge Base to search. Must be set in AWS for RAG to work. |
| `DYNAMODB_CHECKLISTS_TABLE` | `platform-health-checklists` | DynamoDB table that stores action checklists. |
| `DYNAMODB_ESCALATIONS_TABLE` | `platform-health-escalations` | DynamoDB table that stores human escalation requests. |
| `EFS_MOUNT_PATH` | `/mnt/efs` | Where the EFS (Elastic File System) is mounted inside the container — used for persistent chat history. |
| `SESSIONS_DIR` | `{EFS_MOUNT_PATH}/sessions` | Folder under EFS where each chat session's JSON files live. |
| `RECURSION_LIMIT` | `25` | Maximum number of LLM ↔ tool loops before the agent forcibly stops. Think of it like a safety valve — it prevents runaway loops. |

**Key pattern:** `os.getenv("NAME", "default")` reads the environment variable `NAME`; if it's not set, it falls back to the second argument. This is a very common Python pattern for 12-factor app configuration.

---

## 14.2 The Agent Brain — LangGraph (`graph.py`)

This is the most important file. Think of it like a **flowchart for a phone-tree**: when a user's message arrives, the graph decides which "department" handles it and what steps to follow.

### The big picture (ASCII diagram)

```
                           ┌──────────┐
                    START ─▶  router  │
                           └────┬─────┘
                                │
                 ┌──────────────┴──────────────┐
                 │ general_qa                   │ incident_triage
                 ▼                              ▼
            ┌─────────┐                ┌─────────────────┐
            │   llm   │◀─────┐        │ gather_symptoms  │
            └────┬────┘      │        └────────┬─────────┘
                 │           │                 │
          ┌──────┴──────┐    │                 ▼
          │should_continue│   │        ┌─────────────────┐
          └──┬────────┬──┘   │        │   search_docs    │
             │        │      │        └────────┬─────────┘
        "tools"    "end"     │                 │
             │        │      │      ┌──────────┼──────────┐
             ▼        ▼      │      ▼          ▼          ▼
         ┌───────┐   END     │  known_fix  investigate  escalate
         │ tools │───────────┘      │          │          │
         └───────┘                  ▼          ▼          ▼
                                   END        END        END
```

### Path 1 — General Q&A (ReAct loop)

The left side is a classic **ReAct (Reason + Act) loop**. Think of it like a student doing homework:

1. **llm** — The student reads the question and thinks about it.
2. **should_continue** — Did the student decide they need to look something up?
   - *Yes* → go to **tools** (look it up), then back to **llm** (think again).
   - *No* → they have their answer → **END**.

### Path 2 — Incident Triage (structured workflow)

The right side is a **fixed pipeline** for incident reports — like a hospital triage process:

1. **gather_symptoms** — Extract *what*, *where*, *how bad* from the user's message.
2. **search_docs** — Look up the knowledge base and match patterns.
3. **Branch** — Based on confidence:
   - **known_fix** (confidence ≥ 0.6) — "We know this one, here's the fix."
   - **investigate** (0.3–0.6) — "We're not sure yet, try these diagnostic steps."
   - **escalate** (< 0.3 or critical severity) — "Handing this to a human."

### Key code: how the graph is built

```python
def create_agent_graph():
    graph = StateGraph(AgentState)

    # --- Nodes (the boxes in the flowchart) ---
    graph.add_node("router", router_node)
    graph.add_node("llm", llm_node)
    graph.add_node("tools", tool_node)
    graph.add_node("gather_symptoms", gather_symptoms_node)
    graph.add_node("search_docs", search_docs_node)
    graph.add_node("known_fix", known_fix_node)
    graph.add_node("investigate", investigate_node)
    graph.add_node("escalate_incident", escalate_node)

    # --- Edges (the arrows) ---
    graph.set_entry_point("router")

    # Router dispatches to the right workflow
    graph.add_conditional_edges(
        "router",
        lambda s: s.get("current_workflow", "general_qa"),
        {
            "general_qa": "llm",
            "incident_triage": "gather_symptoms",
        },
    )

    # General QA: ReAct loop
    graph.add_conditional_edges(
        "llm",
        should_continue,
        {"tools": "tools", "end": END},
    )
    graph.add_edge("tools", "llm")  # after tools, always go back to LLM

    # Incident triage: linear → branch
    graph.add_edge("gather_symptoms", "search_docs")
    graph.add_conditional_edges(
        "search_docs",
        route_after_search,
        {
            "known_fix": "known_fix",
            "investigate": "investigate",
            "escalate": "escalate_incident",
        },
    )
    graph.add_edge("known_fix", END)
    graph.add_edge("investigate", END)
    graph.add_edge("escalate_incident", END)

    return graph.compile()
```

**Analogy:** `add_node` is like placing a worker at a desk. `add_edge` is like drawing an arrow between desks. `add_conditional_edges` is like drawing *multiple* arrows with labels — "go here *if* this condition is true."

### The Router Node

The router makes a quick LLM call to classify the user's intent:

```python
async def router_node(state: AgentState) -> dict:
    llm = _get_llm()
    response = await llm.ainvoke([
        SystemMessage(content=ROUTER_PROMPT),
        HumanMessage(content=user_msg),
    ])
    workflow = raw.strip().lower().replace(" ", "_")

    if workflow in ("incident_triage", "incident"):
        return {"current_workflow": "incident_triage"}
    else:
        return {"current_workflow": "general_qa"}
```

It sends the user's message to Claude with a special `ROUTER_PROMPT` that says "respond with ONLY the workflow name." Based on the answer, it sets `current_workflow` in the state — and the conditional edges take it from there.

### Tool binding

The LLM doesn't call Python functions directly — it outputs a *structured request* saying "I want to call `rag_search` with these arguments." The `TOOLS` list defines what tools the LLM is allowed to request:

```python
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "rag_search",
            "description": "Search the platform knowledge base for architecture docs...",
            "parameters": { ... }
        }
    },
    # ... assess_incident, create_checklist, escalate_to_human
]
```

Then `llm.bind_tools(TOOLS)` tells the LLM "here are the tools you can use." When the LLM responds with tool calls, the `tool_node` catches them and runs the actual Python code.

### Loop protection

```python
def should_continue(state: AgentState) -> str:
    iteration = state.get("iteration_count", 0)
    if iteration >= RECURSION_LIMIT:
        return "end"
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"
    return "end"
```

If the agent has looped more than `RECURSION_LIMIT` (25) times, it stops. This prevents infinite loops where the LLM keeps calling tools without ever producing a final answer.

---

## 14.3 Agent State (`state.py`)

Think of state as a **clipboard** that gets passed from desk to desk. Every node can read from it and write to it.

```python
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    # Conversation — add_messages appends new messages (never overwrites)
    messages: Annotated[list, add_messages]

    # Workflow tracking
    current_workflow: str      # "general_qa" or "incident_triage"
    workflow_step: int         # 0, 1, 2, 3...
    workflow_status: str       # "in_progress", "completed", "escalated"

    # Workflow-specific data
    workflow_data: dict        # e.g., {"component": "Lambda", "symptoms": "timeout"}
    incident_result: dict      # Result from assess_incident tool

    # Observability
    tool_calls_log: list[dict] # [{name, input, output_length, latency_ms}]
    iteration_count: int       # Loop protection counter
```

### The magic of `add_messages`

The line `messages: Annotated[list, add_messages]` is the most important detail. The `add_messages` annotation tells LangGraph: *"when a node returns new messages, **append** them to the list — don't replace it."*

Without this, every node would overwrite the conversation history. With it, messages accumulate naturally — just like a real chat log.

### Why `TypedDict`?

`TypedDict` is Python's way of saying "this dictionary should have these specific keys with these types." It gives you autocomplete in your editor and catches typos early. Think of it like a form template — you define the fields once, and every node fills in the ones it cares about.

---

## 14.4 System Prompts (`prompts.py`)

Prompts are the **personality and job description** you give the AI. Two prompts live here:

### `SYSTEM_PROMPT` — The main persona

```python
SYSTEM_PROMPT = """You are a Platform Health Insight Assistant designed to help engineers
understand, troubleshoot, and maintain cloud infrastructure platforms.

Core Identity
- Always identify yourself as a Platform Health Insight Assistant.
- Never reference your underlying AI model or technical infrastructure.
- Refer to your information sources as "platform documentation" or "team knowledge base".

Knowledge Domains
You have access to documentation covering:
- AWS Health Analyzer (Bedrock, EventBridge, SNS, Lambda, staged pipeline)
- Infrastructure-as-Code (Terraform, CDK)
- Data Platform (Lakehouse architecture, permissions, Databricks)
...

Response Guidelines
- Always consult platform documentation before responding.
- ALWAYS cite your sources at the end of your response...
"""
```

**Key prompt-engineering patterns:**

| Pattern | Example | Why it matters |
|---------|---------|----------------|
| **Identity anchoring** | "Always identify yourself as…" | Prevents the AI from breaking character. |
| **Negative instructions** | "Never reference your underlying AI model" | Removes confusing meta-answers. |
| **Source grounding** | "Always consult platform documentation" | Forces the AI to use the RAG tool rather than guessing. |
| **Citation format** | "📚 **Sources:** …" | Gives users verifiable references. |
| **Safety rails** | "confirm with the user before proceeding" | Prevents accidental destructive actions. |

### `ROUTER_PROMPT` — The intent classifier

```python
ROUTER_PROMPT = """Based on the user's message, determine which workflow to route to:

1. incident_triage — User reports a problem, error, or unexpected behavior
2. change_impact — User asks about the effect of changing a component
3. onboarding — User is new and needs guidance
4. general_qa — General architecture, design, or technical question

Respond with ONLY the workflow name, nothing else.
"""
```

This is deliberately minimal — it asks for a single word. Short, focused prompts produce more reliable structured outputs.

---

## 14.5 Tools — The Agent's Hands

Tools are how the AI **interacts with the outside world**. The LLM decides *which* tool to call and *what arguments* to pass; the backend executes the actual code.

### `kb_tool.py` — Knowledge Base Search (Bedrock)

Think of this as the agent's **search engine** — it queries the Bedrock Knowledge Base (which indexes your S3 documents, Confluence pages, etc.).

```python
async def kb_search(query: str, top_k: int = 5) -> KBSearchResponse:
    client = boto3.client("bedrock-agent-runtime", region_name=AWS_REGION)

    response = client.retrieve(
        knowledgeBaseId=KNOWLEDGE_BASE_ID,
        retrievalQuery={"text": query},
        retrievalConfiguration={
            "vectorSearchConfiguration": {
                "numberOfResults": top_k
            }
        }
    )
    # ... parse results into KBSearchResult objects
```

**How it works, step by step:**

1. The LLM says: "Call `rag_search` with query `EventBridge cron timezone`."
2. `kb_search()` sends that query to the Bedrock Retrieve API.
3. Bedrock turns the query into a vector (embedding), searches the vector store, and returns the top-K most similar document chunks.
4. Each result comes with a `source_uri` (e.g., `s3://my-bucket/runbook.md`) and a relevance `score`.
5. `format_context_for_llm()` formats these results for the LLM to read:
   ```
   [Source 1: runbook.md (s3) — relevance: 0.87]
   EventBridge cron expressions use UTC by default...
   ```

The helper `_classify_source_type()` looks at the URI to tag each source as `s3`, `web`, `confluence`, or `file`.

### `dynamodb_tool.py` — Checklist Storage

Think of this as a **to-do list manager** backed by DynamoDB.

```python
async def create_checklist(title: str, items: list[str]) -> ChecklistResponse:
    table = _get_table()
    checklist_id = str(uuid.uuid4())

    checklist_items = [
        {"item_text": item, "completed": False}
        for item in items
    ]

    table.put_item(Item={
        "checklist_id": checklist_id,
        "title": title,
        "items": checklist_items,
        "created_at": now,
        "updated_at": now,
    })
```

When the agent decides the user needs a checklist (e.g., "deployment steps for EventBridge migration"), it calls `create_checklist`, which writes a new item to DynamoDB. Each checklist item starts with `completed: False` so it can be tracked later.

### `escalation_tool.py` — Human Handoff

Think of this as the **"transfer to manager" button**. When the AI can't confidently handle something, it creates an escalation record.

```python
async def escalate(reason: str, conversation_summary: str, priority: str = "medium") -> EscalationResponse:
    table = _get_table()
    escalation_id = str(uuid.uuid4())

    table.put_item(Item={
        "escalation_id": escalation_id,
        "reason": reason,
        "conversation_summary": conversation_summary,
        "priority": priority,
        "status": "pending",
        "created_at": now,
    })
```

The escalation includes a summary of the conversation so far, a reason, and a priority level — everything a human engineer needs to pick up where the AI left off.

### `history.py` — Chat History (EFS)

Think of this as a **filing cabinet** where each conversation is a folder. It uses the EFS (Elastic File System) mount so that history survives container restarts.

```
/mnt/efs/sessions/
└── {session_id}/
    ├── metadata.json    # title, created_at, last_active, message_count
    └── messages.json    # [{role, content, timestamp, metadata}]
```

Key functions:

| Function | What it does |
|----------|-------------|
| `ensure_sessions_dir()` | Creates `/mnt/efs/sessions/` on startup if missing. |
| `create_session(id)` | Creates a new session folder with empty JSON files. |
| `save_message(id, role, content)` | Appends a message to `messages.json` and updates `metadata.json`. |
| `list_sessions()` | Scans all session folders, returns metadata sorted by last active. |
| `get_session_history(id)` | Reads `messages.json` for a session. |

**Atomic writes:** `_write_json` writes to a `.tmp` file first, then uses `os.replace()` to atomically swap it in. This prevents data corruption if the container crashes mid-write.

### `incident_tool.py` — Incident Triage

Think of this as a **medical textbook** — it has a dictionary of known component patterns and cross-references them with the knowledge base.

```python
KNOWN_COMPONENTS = {
    "eventbridge": {
        "keywords": ["schedule", "cron", "trigger", "rule", "target"],
        "common_issues": [
            "Cron expression timezone mismatch (use Australia/Sydney)",
            "EventBridge Scheduler IAM role missing lambda:InvokeFunction",
            ...
        ],
    },
    "lambda": { ... },
    "bedrock": { ... },
    "terraform": { ... },
    "lakehouse": { ... },
}
```

The `assess_incident()` function follows three steps:

1. **Pattern match** — Does the component name match a known component? (e.g., "my Lambda is timing out" matches `lambda`.)
2. **KB search** — Search the knowledge base for `"{component} {symptoms} troubleshooting fix"`.
3. **Score confidence** — Known pattern + docs = 0.7 (high). Docs only = 0.4 (medium). Nothing found = 0.2 (low).

The confidence score drives the routing decision in the incident triage workflow (known_fix vs. investigate vs. escalate).

---

## 14.6 Incident Triage Workflow (`incident_triage.py`)

This file implements the **right branch** of the graph — the structured incident pipeline. Think of it like a hospital triage form that gets passed from nurse to doctor to specialist.

### Node 1: `gather_symptoms_node`

Extracts structured data from the user's free-text message using an LLM call:

```python
extraction_prompt = f"""Extract incident details from the user's message.
Return ONLY valid JSON, no other text.

User message: "{user_msg}"

Return format:
{{"component": "...", "symptoms": "...", "severity": "low|medium|high|critical", "environment": "..."}}
"""
```

The response is parsed into a dictionary and stored in `workflow_data`. If the JSON parsing fails (the LLM sometimes wraps it in markdown fences), there's a fallback:

```python
except (json.JSONDecodeError, IndexError):
    extracted = {"component": "unknown", "symptoms": user_msg, "severity": "medium", "environment": "unknown"}
```

### Node 2: `search_docs_node`

Calls `assess_incident()` (from `incident_tool.py`) using the extracted symptoms. Stores the result in `incident_result` and logs the tool call.

### Branching: `route_after_search`

```python
def route_after_search(state: AgentState) -> str:
    confidence = incident.get("confidence", 0)
    severity = state.get("workflow_data", {}).get("severity", "medium")

    if severity == "critical":
        return "escalate"          # Always escalate critical
    elif confidence >= 0.6:
        return "known_fix"         # We know what's wrong
    elif confidence >= 0.3:
        return "investigate"       # Partial match, need more info
    else:
        return "escalate"          # No idea — get a human
```

### Terminal nodes

| Node | When | What it does |
|------|------|-------------|
| `known_fix_node` | confidence ≥ 0.6 | Searches docs again, creates a fix checklist, asks the LLM to write an actionable response. |
| `investigate_node` | 0.3 ≤ confidence < 0.6 | Creates a *diagnostic* checklist (check logs, recent deploys, IAM, quotas, etc.), asks the LLM to write next-step guidance. |
| `escalate_node` | confidence < 0.3 or critical | Creates an escalation record in DynamoDB, asks the LLM to inform the user with the escalation ID. |

---

## 14.7 API Server (`main.py`)

This is the **front door** — it receives HTTP requests and returns responses. Think of it like a restaurant host: it takes your order, sends it to the kitchen (the LangGraph agent), and brings back the food.

### Startup (lifespan)

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent_graph
    agent_graph = create_agent_graph()   # Compile the graph once
    from tools.history import ensure_sessions_dir
    ensure_sessions_dir()                # Create EFS folder
    yield                                # App runs here
    print("🛑 Agent backend shutting down...")
```

The graph is compiled **once** at startup and reused for every request. This avoids the overhead of rebuilding the graph on each call.

### Request/Response models

```python
class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None

class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    tool_calls: list[dict] = []
    sources: list[dict] = []
    workflow_status: str = "complete"
    latency_ms: int = 0
```

Pydantic `BaseModel` classes automatically validate incoming JSON. If someone sends `{"msg": "hi"}` instead of `{"message": "hi"}`, FastAPI returns a helpful 422 error.

### `POST /chat` — Non-streaming

The synchronous endpoint. It:

1. Builds the initial state (with the user's message).
2. Calls `agent_graph.ainvoke(initial_state, config)` — this runs the *entire* graph to completion.
3. Extracts the final `AIMessage` (walking backwards through messages to find the last one without tool calls).
4. Extracts RAG sources from `tool_calls_log`.
5. Saves both user and assistant messages to EFS history.
6. Returns a `ChatResponse` with everything bundled up.

### `POST /chat/stream` — SSE Streaming

The real-time endpoint. Instead of waiting for the full response, it **streams tokens as they're generated**, using Server-Sent Events (SSE).

```python
async def stream():
    async for event in agent_graph.astream_events(initial_state, config, version="v2"):
        kind = event.get("event", "")
        node = event.get("metadata", {}).get("langgraph_node", "")

        if kind == "on_chain_start" and node == "tools":
            yield f"data: {json.dumps({'step': 'tool_start', ...})}\n\n"

        elif kind == "on_chat_model_stream":
            # Stream each token to the browser
            yield f"data: {json.dumps({'step': 'token', 'content': text})}\n\n"

    # At the end:
    yield f"data: {json.dumps({'step': 'sources', 'sources': unique})}\n\n"
    yield f"data: {json.dumps({'step': 'complete', ...})}\n\n"
```

**SSE event types the frontend listens for:**

| `step` | Meaning |
|--------|---------|
| `tool_start` | A tool is about to run (show a spinner). |
| `tool_end` | A tool finished (hide the spinner, show tool name). |
| `token` | A piece of the AI's answer (append to the chat bubble). |
| `sources` | Deduplicated list of documents cited. |
| `complete` | All done — includes `conversation_id` and `latency_ms`. |

**Filtering trick:** Tokens from `router`, `gather_symptoms`, and `search_docs` nodes are skipped — those are internal LLM calls, not the user-facing answer.

### Other endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Returns `{"status": "healthy", "agent": true}` — used by Docker and ALB health checks. |
| `/sessions` | GET | Lists all chat sessions from EFS. |
| `/sessions/{id}/history` | GET | Returns full message history for a session. |

### Middleware

```python
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    latency = int((time.time() - start) * 1000)
    logger.info(f"{request.method} {request.url.path} → {response.status_code} ({latency}ms)")
    return response
```

Every request gets logged with its latency. This is invaluable for debugging slow responses.

---

## 14.8 Docker (`Dockerfile` + `requirements.txt`)

### `Dockerfile`

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/health')" || exit 1

# Run with uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
```

**Line-by-line:**

| Line | What it does |
|------|-------------|
| `FROM python:3.12-slim` | Starts from a minimal Python 3.12 image (~150 MB vs ~900 MB for the full image). |
| `COPY requirements.txt .` + `RUN pip install` | Installs dependencies *before* copying code. This is a **layer caching trick** — if your code changes but dependencies don't, Docker reuses the cached pip layer. |
| `EXPOSE 8001` | Documents that the container listens on port 8001 (doesn't actually open the port). |
| `HEALTHCHECK` | Docker (and ECS) will ping `/health` every 30 seconds. If it fails 3 times in a row, the container is marked unhealthy and restarted. |
| `CMD [...]` | Starts the FastAPI app with Uvicorn, listening on all interfaces (`0.0.0.0`). |

### `requirements.txt`

```
fastapi>=0.115.0
uvicorn>=0.32.0
langchain-core>=0.3.0
langchain-aws>=0.2.0
langgraph>=0.2.0
boto3>=1.35.0
pydantic>=2.0.0
```

| Package | Role |
|---------|------|
| `fastapi` | The web framework — handles HTTP routing, validation, docs. |
| `uvicorn` | ASGI server — the thing that actually listens on port 8001. |
| `langchain-core` | Core abstractions: messages, tools, prompts. |
| `langchain-aws` | `ChatBedrockConverse` — the LangChain wrapper for AWS Bedrock. |
| `langgraph` | The graph-based agent orchestration framework. |
| `boto3` | The AWS SDK for Python — used for DynamoDB, Bedrock, etc. |
| `pydantic` | Data validation — powers the request/response models and tool outputs. |

---

## 14.9 Local vs AWS Differences

The codebase is designed to run in two environments. Here's what changes:

| Aspect | Local Development | AWS (ECS) Deployment |
|--------|-------------------|----------------------|
| **AWS credentials** | `AWS_PROFILE` env var or `~/.aws/credentials` | ECS Task Role — automatic, no profile needed |
| **RAG / Search** | Local FAISS vector store (`rag_tool.py`) | Bedrock Knowledge Base (`kb_tool.py`) |
| **Checklist storage** | SQLite / PostgreSQL (`db_tool.py`) | DynamoDB (`dynamodb_tool.py`) |
| **Chat history** | Local filesystem or in-memory | EFS mount at `/mnt/efs` (`history.py`) |
| **Escalation storage** | SQLite / PostgreSQL | DynamoDB (`escalation_tool.py`) |
| **Config injection** | `.env` file | ECS Task Definition environment variables |
| **Model ID** | Same (configurable via env var) | Same (but often uses `apac.` inference profile prefix) |
| **Port** | Usually `8000` (uvicorn default) | `8001` (set in Dockerfile CMD) |
| **Health checks** | Manual (`curl localhost:8000/health`) | Docker HEALTHCHECK + ALB target group |
| **Container** | `python main.py` or `uvicorn main:app` | Docker image on ECR, deployed by ECS |
| **Scaling** | Single instance | ECS Service with desired count, ALB distributes traffic |

### Why the tools are swappable

Notice that `graph.py` imports tools dynamically inside `execute_tool()`:

```python
if name == "rag_search":
    from tools.kb_tool import kb_search, format_context_for_llm
    ...
elif name == "create_checklist":
    from tools.dynamodb_tool import create_checklist
    ...
```

The LLM always sees the same tool names (`rag_search`, `create_checklist`). Only the **implementation** behind each name changes between local and AWS. This is a clean separation — the AI's "brain" doesn't need to know whether it's talking to FAISS or Bedrock.

---

## Summary — How a Request Flows

Let's trace a complete request: *"My EventBridge schedule isn't triggering the Lambda."*

1. **`POST /chat/stream`** — FastAPI receives the message, creates a `conversation_id`.
2. **`router_node`** — Quick LLM call: "Is this an incident?" → Yes → sets `current_workflow = "incident_triage"`.
3. **`gather_symptoms_node`** — LLM extracts: `{component: "EventBridge", symptoms: "schedule not triggering Lambda", severity: "medium"}`.
4. **`search_docs_node`** — Calls `assess_incident()` which:
   - Pattern matches `eventbridge` in `KNOWN_COMPONENTS`.
   - Searches Bedrock KB for related docs.
   - Returns confidence 0.7 → branch to `known_fix`.
5. **`known_fix_node`** — Creates a fix checklist in DynamoDB, asks the LLM to write a clear response with steps.
6. **SSE stream** — Tokens flow back to the browser in real time. Sources are emitted at the end.
7. **`history.py`** — Both user and assistant messages are saved to EFS for future sessions.

That's the entire backend — from HTTP request to AI-powered response, stored for posterity. 🎉
