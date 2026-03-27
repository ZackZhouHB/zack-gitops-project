# Step 23 — Human-in-the-Loop: Approve, Reject, or Edit Before Execution

## 23.1 Goal

Upgrade the action agent from "present a plan and wait for user to re-prompt" to a **real Human-in-the-Loop (HITL) workflow** where:

1. Agent calls write tools freely (create ticket, send message, etc.)
2. The **graph pauses automatically** before executing any write tool
3. User sees the proposed action and can **approve, reject, or edit** it
4. Agent **resumes from the exact checkpoint** and continues

This is the difference between a chatbot and a **production AI workflow**.

---

## 23.2 Why HITL?

### The Problem with "Confirm Before Acting" Prompts

In Phase D, we told the LLM via system prompt: *"Present your plan and ask the user to confirm."* This works, but has serious limitations:

| Problem | Impact |
|---------|--------|
| LLM can ignore the instruction | Prompt injection or complex chains may bypass it |
| No real pause | The agent just waits for a new chat message — not a structured approval |
| No audit trail | "The user said yes" is not a verifiable approval record |
| No edit capability | User must describe changes in natural language |
| Not resumable | If the server restarts, the "plan" is lost |

### The HITL Solution

| Feature | Prompt-Based | LangGraph interrupt() |
|---------|-------------|----------------------|
| Enforcement | LLM follows a suggestion | Graph physically stops |
| Bypass risk | LLM can ignore prompt | Cannot bypass — graph is halted |
| Approval record | None | Structured: approve/reject/edit with timestamp |
| Editability | "Please change X" in chat | Direct arg modification via API |
| Resumability | Lost on restart | Checkpointed state survives in memory |
| Multi-step | Manual re-prompting | Automatic chaining — each write pauses independently |

---

## 23.3 Key Concepts

### 23.3.1 LangGraph `interrupt()`

`interrupt()` is a LangGraph primitive that **pauses graph execution** and returns control to the caller:

```python
from langgraph.types import interrupt, Command

# Inside a graph node:
approval = interrupt({
    "tool": "create_ticket",
    "args": {"summary": "DNS failure", "priority": "High"},
    "message": "Approve this action?"
})
# Graph is FROZEN here until resumed

# The caller resumes with:
result = await graph.ainvoke(
    Command(resume={"decision": "approve"}),
    config,
)
# interrupt() returns {"decision": "approve"} and execution continues
```

### 23.3.2 Checkpointer

For `interrupt()` to work, the graph needs a **checkpointer** — a backend that saves the graph state so it can be resumed later:

```python
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()
graph = graph_builder.compile(checkpointer=checkpointer)
```

**MemorySaver**: In-memory, fast, lost on restart. Good for development.
**PostgresSaver**: Persistent, survives restarts. Use for production.

### 23.3.3 Thread IDs

Each conversation gets a `thread_id`. The checkpointer uses this to store and retrieve state:

```python
config = {"configurable": {"thread_id": "conv-123"}}
result = await graph.ainvoke(initial_state, config)
# Later, resume the same thread:
result = await graph.ainvoke(Command(resume=...), config)
```

---

## 23.4 Architecture

### Before HITL (Phase D)

```
User -> /chat -> graph.ainvoke() -> [read tools + LLM] -> response
                                     (write tools executed immediately!)
```

### After HITL (Phase E)

```
User -> /chat -> graph.ainvoke()
                   |
                   +-> [read tools] -> LLM decides to call write tool
                   |
                   +-> tool_node: interrupt() <-- graph PAUSES
                   |
                   +-> /chat returns {status: "pending_approval", pending_action: {...}}
                   
User reviews -> /chat/{thread_id}/approve  (or /reject or /edit)
                   |
                   +-> graph.ainvoke(Command(resume={"decision": "approve"}), config)
                   |
                   +-> tool_node: interrupt() returns -> executes write tool
                   |
                   +-> LLM generates final response -> {status: "complete"}
```

### API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/chat` | Start conversation — may return `pending_approval` |
| POST | `/chat/{thread_id}/approve` | Approve and execute the pending action |
| POST | `/chat/{thread_id}/reject` | Reject — action is cancelled |
| POST | `/chat/{thread_id}/edit` | Modify args then execute |
| GET | `/chat/{thread_id}/status` | Check if thread has pending approval |

---

## 23.5 Code Changes

### 23.5.1 Graph: Add `interrupt()` to `tool_node`

The key change is in `tool_node` — we check if the tool is a write tool and interrupt:

```python
async def tool_node(state: AgentState) -> dict:
    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        is_write = tool_name in WRITE_TOOLS

        if is_write:
            # HITL: pause graph and return to caller
            approval = interrupt({
                "tool": tool_name,
                "args": tool_call["args"],
                "is_write": True,
                "message": f"Approve this action? Tool: {tool_name}",
            })

            decision = approval.get("decision", "reject")

            if decision == "reject":
                # Return rejection as tool result — LLM acknowledges
                result_str = json.dumps({"status": "rejected", "message": "Action rejected by user"})
                new_messages.append(ToolMessage(content=result_str, ...))
                continue

            if decision == "edit":
                tool_args = approval.get("edited_args", tool_args)

        # Execute the tool (read tools always, write tools after approval)
        result = await _execute_tool(tool_name, tool_args, jira, slack)
```

**What happens at `interrupt()`**:
1. The graph serializes its state to the checkpointer
2. `graph.ainvoke()` returns to the caller (FastAPI endpoint)
3. The caller checks `graph.aget_state(config).next` — if non-empty, graph is paused
4. The pending action (interrupt value) is extracted and returned to the user
5. When user calls `/approve`, we resume with `Command(resume={"decision": "approve"})`
6. `interrupt()` returns the resume value and execution continues

### 23.5.2 Graph: Compile with Checkpointer

```python
def create_agent_graph():
    checkpointer = MemorySaver()
    # ... build graph ...
    return graph.compile(checkpointer=checkpointer), checkpointer
```

### 23.5.3 System Prompt: Remove Manual Confirmation

The old prompt said: *"Present what you plan to do and ask the user to confirm."*

The new prompt says: *"Write tools have a built-in approval system. When asked to create a ticket or send a message, GO AHEAD and call the tool. The system will automatically pause and ask the user."*

This is critical — if the prompt still tells the LLM to ask for confirmation, it will never call write tools, and `interrupt()` will never trigger.

### 23.5.4 API: Detect Interrupts in `/chat`

```python
@app.post("/chat")
async def chat(request: ChatRequest):
    result = await agent_graph.ainvoke(initial_state, config)
    
    # Check if graph was interrupted
    graph_state = await agent_graph.aget_state(config)
    
    if graph_state.next:
        # Graph is paused — extract the pending action
        for task in graph_state.tasks:
            if hasattr(task, "interrupts") and task.interrupts:
                pending_action = task.interrupts[0].value
        
        return ChatResponse(
            status="pending_approval",
            pending_action=pending_action,
            ...
        )
    
    return ChatResponse(status="complete", ...)
```

### 23.5.5 API: `/approve` Endpoint

```python
@app.post("/chat/{thread_id}/approve")
async def approve_action(thread_id: str):
    result = await agent_graph.ainvoke(
        Command(resume={"decision": "approve"}),
        config,
    )
    
    # Check for MORE interrupts (agent may chain writes)
    graph_state = await agent_graph.aget_state(config)
    if graph_state.next:
        return ChatResponse(status="pending_approval", ...)
    
    return ChatResponse(status="complete", ...)
```

---

## 23.6 Multi-Write Chaining

When the agent wants to create a ticket AND send a Slack notification, it may call both write tools. With HITL, this creates a **chain of approvals**:

```
1. Agent calls create_ticket -> interrupt() -> user approves -> SCRUM-19 created
2. Agent calls send_message  -> interrupt() -> user approves -> Slack message sent
3. Agent generates final response -> complete
```

Each write tool gets its own approval. The user can approve the ticket but reject the Slack message.

The `/approve` endpoint handles this by checking for more interrupts after each resume:

```python
# After approve, check if there are MORE pending writes
graph_state = await agent_graph.aget_state(config)
if graph_state.next:
    # Another write tool is pending — return pending_approval again
    return ChatResponse(status="pending_approval", pending_action=next_action)
```

---

## 23.7 Test Results

### HITL Flow Tests

| Test | Description | Result |
|------|-------------|--------|
| Health check | HITL enabled flag present | ✅ |
| Read-only completes | search_issues returns `complete`, no interrupt | ✅ |
| Write interrupts | create_ticket returns `pending_approval` with full args | ✅ |
| Approve flow | Resume creates ticket (SCRUM-19 in Jira) | ✅ |
| Reject flow | send_message cancelled, no Slack message sent | ✅ |
| Edit flow | Modified priority, created ticket with user's changes | ✅ |
| Status endpoint | `/chat/{id}/status` shows `pending_approval` | ✅ |
| Existing E2E | Read-only scenarios (1-5) still pass | ✅ |

### Approval Decision Matrix

| User Decision | What Happens | Tool Executed? | Agent Response |
|--------------|--------------|----------------|----------------|
| **Approve** | `interrupt()` returns `{decision: "approve"}` | ✅ Yes | "Successfully created SCRUM-19..." |
| **Reject** | `interrupt()` returns `{decision: "reject"}` | ❌ No | "Action rejected. Would you like to modify?" |
| **Edit** | `interrupt()` returns `{decision: "edit", edited_args: {...}}` | ✅ Yes (modified) | "Created ticket with your changes..." |

---

## 23.8 Running the HITL Tests

```bash
cd project-125 && source .venv/bin/activate

# Start the agent
cd agent-backend && python main.py &

# Run HITL-specific tests
cd .. && python scripts/hitl_test.py

# Manual test via curl:

# 1. Trigger a write action
curl -s -X POST http://localhost:8010/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Create a ticket for slow database queries"}' | python3 -m json.tool

# 2. Check status (copy conversation_id from above)
curl -s http://localhost:8010/chat/{THREAD_ID}/status | python3 -m json.tool

# 3a. Approve it
curl -s -X POST http://localhost:8010/chat/{THREAD_ID}/approve | python3 -m json.tool

# 3b. Or reject it
curl -s -X POST http://localhost:8010/chat/{THREAD_ID}/reject | python3 -m json.tool

# 3c. Or edit and approve
curl -s -X POST http://localhost:8010/chat/{THREAD_ID}/edit \
  -H "Content-Type: application/json" \
  -d '{"edited_args": {"priority": "Low", "labels": ["edited"]}}' | python3 -m json.tool
```

---

## 23.9 Real-World Issues Encountered

### Issue: System Prompt Blocked Write Tools

**Problem**: After adding `interrupt()`, the agent never called write tools because the system prompt said "present your plan and ask to confirm."

**Root Cause**: The LLM followed the prompt instruction to NOT call write tools, so `interrupt()` never triggered.

**Fix**: Updated prompt from "confirm before acting" to "write tools have built-in approval — go ahead and call them."

**Lesson**: When adding infrastructure-level safety (like HITL), remove the prompt-level safety that conflicts with it. You can't have both — the prompt-level rule prevents the infrastructure from ever activating.

### Issue: Agent Chains Multiple Writes

**Problem**: After approving `create_ticket`, the agent sometimes tries `send_message` too, causing another interrupt.

**Solution**: The `/approve` endpoint checks for more interrupts and returns `pending_approval` again if needed. Each write gets its own approval cycle.

---

## 23.10 Key Takeaways

| Concept | What You Learned |
|---------|-----------------|
| `interrupt()` | Physically pauses graph execution — cannot be bypassed by LLM |
| `Command(resume=...)` | Sends user's decision back to the paused graph |
| Checkpointer | Saves graph state so it can be resumed (MemorySaver for dev) |
| Thread IDs | Each conversation is a resumable thread |
| Prompt vs Infrastructure | Remove prompt-level safety when you add graph-level enforcement |
| Multi-write chains | Each write tool gets its own approval — user can approve/reject independently |

---

## 23.11 What's Next

In **Step 24 (Phase F — Eval & Guardrails)**, we'll add:
- **Golden test set**: Known-good Q&A pairs for regression testing
- **RAGAS metrics**: Faithfulness, relevance, and answer correctness
- **Bedrock Guardrails**: Content filtering, PII detection, topic restriction
- **Cost tracking**: Token usage and Bedrock API costs per conversation

This ensures the agent is not just functional (it works) but also **reliable** (it works correctly, consistently, and safely).
