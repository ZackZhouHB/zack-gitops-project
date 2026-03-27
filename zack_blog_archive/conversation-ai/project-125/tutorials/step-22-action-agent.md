# Step 22 — Action Agent: RAG + Jira + Slack in One Brain

## 22.1 Goal

Build a **LangGraph ReAct agent** that can:
- Search the local RAG knowledge base (Weaviate)
- Search, create, and update Jira tickets
- Send Slack messages and rich notifications
- Chain these tools together in a single conversation turn

By the end of this tutorial, you'll understand how an AI agent decides **which tools to call, in what order**, and how to enforce **safety rules** (read-before-write, confirm-before-acting).

---

## 22.2 Prerequisites

| Requirement | Check |
|---|---|
| platform-health-agent Docker stack running | `docker ps` shows weaviate + postgres |
| Jira Cloud project (key: SCRUM) | Verified via jira_test.py |
| Slack bot installed in channel | Verified via slack_test.py |
| `.env` configured with all credentials | See .env.example |
| Python venv with dependencies | `pip install -r agent-backend/requirements.txt` |

---

## 22.3 Key Concepts

### 22.3.1 What Is a ReAct Agent?

**ReAct** = **Re**ason + **Act**. The agent follows a loop:

```
User Message → LLM Thinks → Calls Tool → Observes Result → Thinks Again → ... → Final Answer
```

Unlike a simple chain (A→B→C), a ReAct agent **decides at each step** what to do next. It can:
- Call zero tools (just answer from knowledge)
- Call one tool, then answer
- Call multiple tools in sequence, adapting based on each result

### 22.3.2 Tool Categories

We organize our 11 tools into two categories:

| Category | Tools | Risk Level |
|---|---|---|
| **READ** (safe) | `rag_search`, `search_issues`, `get_ticket`, `list_channels` | Low — only reads data |
| **WRITE** (dangerous) | `create_ticket`, `update_ticket`, `add_comment`, `send_message`, `create_thread`, `reply_in_thread`, `send_rich_notification` | High — creates/modifies external state |

**Why this matters**: Write tools are irreversible. You can't "un-send" a Slack message. Our system prompt enforces:
1. **Read before write** — search for duplicates before creating
2. **Confirm before acting** — present a plan, don't just execute

### 22.3.3 LangGraph StateGraph vs ReAct

LangGraph gives us two patterns:

| Pattern | Use Case | Control |
|---|---|---|
| **StateGraph** (manual) | Custom workflows with specific routes | You define every edge |
| **ReAct** (agentic) | General-purpose tool use | LLM decides the flow |

Our platform-health-agent used a **StateGraph** with explicit routing:
```
classify → route → (rag / health_check / runbook / general)
```

project-125 uses a **ReAct loop** because the agent needs flexibility to chain arbitrary tools:
```
agent_node → should_continue? → tool_node → agent_node → ... → END
```

---

## 22.4 Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    FastAPI Server (:8010)                  │
├──────────────────────────────────────────────────────────┤
│                                                          │
│   User Message                                           │
│       │                                                  │
│       ▼                                                  │
│   ┌────────────┐    tool_calls?    ┌──────────────────┐ │
│   │ agent_node │──── YES ─────────▶│   tool_node      │ │
│   │ (LLM +     │                   │ (dispatches to   │ │
│   │  tools def)│◀──────────────────│  correct tool fn)│ │
│   └────────────┘    result         └──────────────────┘ │
│       │                                                  │
│       │ no more tool_calls                               │
│       ▼                                                  │
│   Final Response                                         │
│                                                          │
│   Tools:                                                 │
│   ┌─────────────┐  ┌──────────────┐  ┌───────────────┐ │
│   │ rag_search  │  │ Jira Tools   │  │ Slack Tools   │ │
│   │ (Weaviate   │  │ (REST API    │  │ (Web API      │ │
│   │  :8080)     │  │  v3 client)  │  │  client)      │ │
│   └─────────────┘  └──────────────┘  └───────────────┘ │
└──────────────────────────────────────────────────────────┘
```

---

## 22.5 Code Walkthrough

### 22.5.1 Agent State (`agent/__init__.py`)

```python
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]  # LangGraph message history
    tool_calls_log: list                      # Audit trail of all tool invocations
    iteration_count: int                      # Safety: prevent infinite loops
    pending_approval: Optional[dict]          # For HITL (Phase E)
    approval_response: Optional[str]          # For HITL (Phase E)
```

**Why `messages` uses `Annotated[list, add_messages]`**: This tells LangGraph to **append** new messages instead of replacing the list. Each agent/tool turn adds messages, building up the conversation history.

**Why `tool_calls_log`**: Unlike `messages` (which the LLM sees), this is our own audit log. We track every tool call with timing, success/failure, and whether it was a write operation.

### 22.5.2 Tool Definitions (`agent/graph.py`)

Each tool is defined as a dict matching LangChain's tool format:

```python
{
    "type": "function",
    "function": {
        "name": "search_issues",
        "description": "Search Jira issues using JQL query string",
        "parameters": {          # ← MUST be "parameters", NOT "input_schema"
            "type": "object",
            "properties": {
                "jql": {
                    "type": "string",
                    "description": "JQL query (e.g., 'project = SCRUM AND status = Open')"
                }
            },
            "required": ["jql"]
        }
    }
}
```

> ⚠️ **Real-World Issue**: `ChatBedrockConverse` expects `parameters` key. If you use `input_schema` (the raw Bedrock API format), you get `KeyError: 'parameters'`. LangChain converts `parameters` → Bedrock's `inputSchema` internally. See TROUBLESHOOTING.md #3.

### 22.5.3 Tool Execution Dispatch

When the LLM responds with tool calls, we route to the correct function:

```python
async def _execute_tool(tool_name: str, tool_input: dict) -> str:
    if tool_name == "rag_search":
        return await rag_search(tool_input["query"])
    elif tool_name == "search_issues":
        return jira_client.search_issues(tool_input["jql"])
    elif tool_name == "create_ticket":
        return jira_client.create_issue(
            summary=tool_input["summary"],
            description=tool_input.get("description", ""),
            priority=tool_input.get("priority", "Medium"),
            labels=tool_input.get("labels", [])
        )
    # ... more tools
```

**Why not use `@tool` decorators?** LangChain's `@tool` decorator auto-generates schemas and handles invocation. We chose explicit dispatch because:
1. Our Jira/Slack clients already exist (in mcp-servers/)
2. We want to control error handling per tool
3. We need the audit trail (timing, write classification)

### 22.5.4 The ReAct Loop

```python
def create_agent_graph():
    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)      # LLM decides
    graph.add_node("tools", tool_node)        # Execute tools
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {
        "continue": "tools",   # Has tool calls → execute them
        "end": END             # No tool calls → return response
    })
    graph.add_edge("tools", "agent")          # After tools → back to LLM
    return graph.compile()
```

The **conditional edge** `should_continue` checks:
1. Does the last message have `tool_calls`? → "continue" 
2. Have we exceeded `MAX_ITERATIONS` (10)? → "end" (safety)
3. Otherwise → "end" (final answer)

### 22.5.5 System Prompt Rules

The system prompt is critical for safety:

```
## Rules
1. Always search before creating (avoid duplicates)
2. For WRITE actions, present your plan FIRST. Do NOT execute until confirmed.
3. Include relevant KB context in tickets/messages
4. Use structured formatting (headers, bullets, links)
```

This is a **proto-HITL** approach: the agent presents what it *would* do, waits for user confirmation, then executes. In Phase E, we'll enforce this with `LangGraph.interrupt()`.

---

## 22.6 Running the Agent

### Start Dependencies
```bash
# 1. Start platform-health-agent's Docker stack (Weaviate + PostgreSQL)
cd ../platform-health-agent
docker compose up -d

# 2. Verify Weaviate is ready
curl -s http://localhost:8080/v1/meta | python3 -c "import sys,json; print(json.load(sys.stdin)['version'])"
# → 1.35.16
```

### Start the Agent Server
```bash
# 3. Activate venv and start
cd ../project-125
source .venv/bin/activate
cd agent-backend
python main.py
# → INFO: Uvicorn running on http://0.0.0.0:8010
```

### Test Queries

**RAG-only query:**
```bash
curl -s -X POST http://localhost:8010/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What do we know about Terraform?"}' | python3 -m json.tool
```

**Jira search:**
```bash
curl -s -X POST http://localhost:8010/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Search for open tickets about API latency"}' | python3 -m json.tool
```

**Multi-tool chain (the big test):**
```bash
curl -s -X POST http://localhost:8010/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Create a P2 ticket for EKS node scaling and notify #all-platform-health-lab"}' | python3 -m json.tool
```

Expected behavior: Agent searches KB → checks for duplicates → presents plan (doesn't execute writes until confirmed).

---

## 22.7 How the Multi-Tool Flow Works

Let's trace what happens with: *"Create a ticket for API latency and notify Slack"*

```
Turn 1: LLM reads system prompt + user message
         → Decides to call rag_search("API latency")
         → Returns: 5 KB sources about latency patterns

Turn 2: LLM sees KB context
         → Decides to call search_issues("project = SCRUM AND text ~ 'API latency'")
         → Returns: 4 existing tickets found

Turn 3: LLM sees duplicates exist
         → Instead of creating (rule: search first!), presents findings
         → "Found 4 existing tickets. Do you still want me to create a new one?"
```

If the user says "yes, create it":
```
Turn 4: LLM presents plan:
         "I'll create: [summary, priority, labels] and notify: [channel, message]"

Turn 5 (after confirmation): LLM calls create_ticket(...) → gets SCRUM-9
Turn 6: LLM calls send_message(...) with ticket link → Slack confirms
Turn 7: Final response with links to both
```

---

## 22.8 Real-World Issues Encountered

### Issue: `ChatBedrockConverse` Tool Format
**Problem**: All tool definitions used `input_schema` (raw Bedrock format). `ChatBedrockConverse` expects `parameters` (LangChain format).

**Error**: `KeyError: 'parameters'` in `bedrock_converse.py:_format_tools()`

**Fix**: Rename `input_schema` → `parameters` in all tool definitions.

**Lesson**: When using LangChain wrappers, always use LangChain's format. The wrapper handles provider-specific conversion.

### Issue: Port Conflict
**Problem**: Port 8001 is used by platform-health-agent.

**Fix**: project-125 agent runs on port 8010.

**Lesson**: When running multiple services, document port assignments centrally.

---

## 22.9 Key Takeaways

| Concept | What You Learned |
|---|---|
| ReAct pattern | LLM decides tool order dynamically (not hardcoded) |
| Tool categories | READ vs WRITE separation enables safety rules |
| System prompt rules | "Search before create" prevents duplicates |
| Confirmation flow | Agent presents plan, waits for approval |
| Audit trail | `tool_calls_log` tracks every action with timing |
| Tool format | `ChatBedrockConverse` needs `parameters`, not `input_schema` |

---

## 22.10 What's Next

In **Step 23**, we'll upgrade the confirmation flow from a prompt-based approach to a proper **Human-in-the-Loop** system using `LangGraph.interrupt()`:
- Agent pauses execution before write actions
- Streamlit UI shows approval dialog
- User can approve, reject, or modify
- Agent resumes from the exact checkpoint

This transforms our "suggest and confirm" pattern into a real **workflow pause/resume** — critical for production AI agents.
