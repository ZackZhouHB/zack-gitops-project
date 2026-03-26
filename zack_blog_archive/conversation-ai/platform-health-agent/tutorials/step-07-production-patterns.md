# Tutorial Step 7: Production Patterns — Making the Agent Reliable

> **Goal:** Understand the patterns that make an AI agent safe to deploy to real users  
> **Time:** ~20 minutes  
> **Prerequisites:** Steps 5–6 (Multi-Tool Agent, Eligibility Workflow)  

---

## What We're Building in This Step

In Steps 5–6, we built an agent that works. In this step, we make it work **reliably**. The difference between a demo and a production system is everything that happens when things go wrong.

Think of it like building a car vs selling a car:
- **Demo:** Engine works, it drives → great demo!
- **Production:** What if the engine overheats? What if the brakes fail? What if a sensor breaks? Where do warning lights go? How do you know when to service it?

```
┌──────────────────────────────────────────────────────────┐
│              Production Patterns We'll Cover              │
│                                                          │
│  🔒 Loop protection    → Agent can't run forever         │
│  🛡️ Error handling     → Tools fail gracefully           │
│  📊 Observability      → We can see what the agent did   │
│  ⏱️ Request timing     → We know how long things take    │
│  📝 Structured logging → Searchable, parseable logs      │
│  🌊 Streaming          → Users see progress in real time │
│                                                          │
│  Plus: concepts for the future                           │
│  🔌 Circuit breakers   → Stop calling broken services    │
│  💾 Checkpointing      → Resume interrupted workflows    │
│  📈 Monitoring         → Alerts when things break        │
└──────────────────────────────────────────────────────────┘
```

---

## Key Concepts (Explained for Beginners)

### Why Production Patterns Matter

AI agents are unpredictable in ways traditional software isn't:

| Traditional Software | AI Agent |
|---|---|
| Takes the same path every time | Takes different paths depending on LLM output |
| Fails in predictable ways | Can hallucinate, loop forever, or call wrong tools |
| Fixed execution time | Could take 1 second or 60 seconds |
| Errors have stack traces | LLM "errors" are often wrong answers, not exceptions |

You need patterns to handle this unpredictability. Let's go through each one as it appears in our codebase.

---

## Pattern 1: Structured Logging with Timing

Every time our agent does something, it logs **what** happened and **how long** it took. This is our primary debugging tool.

### In graph nodes (`agent/graph.py`)

```python
import time
import logging

# Create a named logger — "agent" namespace
logger = logging.getLogger("agent")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
    #       ↑ timestamp  ↑ logger name  ↑ level     ↑ message
    # Output: 2025-01-15 10:30:45 [agent] INFO: LLM call #1: 842ms, tools=['rag_search']
)
```

Inside the LLM node, we time every call:

```python
async def llm_node(state: AgentState) -> dict:
    # ... setup ...

    start = time.time()                                  # Start timer
    response = await llm_with_tools.ainvoke(messages)    # Call Claude
    latency = int((time.time() - start) * 1000)          # Calculate ms

    iteration = state.get("iteration_count", 0) + 1
    tool_names = [tc["name"] for tc in (response.tool_calls or [])]

    # Log: which iteration, how long, what tools were requested
    logger.info(f"LLM call #{iteration}: {latency}ms, tools={tool_names or 'none'}")
    #            ↑ "LLM call #1: 842ms, tools=['rag_search']"
    #            ↑ "LLM call #2: 512ms, tools=none"  (final response, no tools)

    return {
        "messages": [response],
        "iteration_count": iteration,    # Increment the counter
    }
```

**Why timing matters:** If your LLM calls suddenly take 5 seconds instead of 1 second, something is wrong — maybe the model is overloaded, or your messages are too long. Without timing logs, you'd never know.

### In tool execution

```python
async def tool_node(state: AgentState) -> dict:
    for tool_call in last_message.tool_calls:
        name = tool_call["name"]
        args = tool_call["args"]

        start = time.time()
        try:
            result = await execute_tool(name, args)
        except Exception as e:
            result = f"Tool error: {str(e)}"       # ← Error handling (Pattern 3)
            logger.error(f"Tool {name} failed: {e}")
        latency_ms = int((time.time() - start) * 1000)

        # Log: which tool, how long, how big the output was
        logger.info(f"Tool {name}: {latency_ms}ms, output={len(result)} chars")
        #            ↑ "Tool rag_search: 234ms, output=2847 chars"
        #            ↑ "Tool check_eligibility: 156ms, output=423 chars"
```

**Example log output for a single request:**

```
2025-01-15 10:30:45 [agent] INFO: Router → eligibility_check
2025-01-15 10:30:46 [agent] INFO: LLM call #1: 842ms, tools=['check_eligibility']
2025-01-15 10:30:46 [agent] INFO: Tool check_eligibility: 156ms, output=423 chars
2025-01-15 10:30:47 [agent] INFO: LLM call #2: 512ms, tools=none
```

You can read this like a story: "Router sent it to eligibility. LLM called check_eligibility. Tool returned 423 chars in 156ms. LLM wrote the final response."

---

## Pattern 2: Request Timing Middleware

Every HTTP request to our FastAPI server gets timed automatically:

```python
# From main.py
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log every request with timing."""
    start = time.time()
    response = await call_next(request)          # Run the actual handler
    latency = int((time.time() - start) * 1000)  # Total request time

    logger.info(f"{request.method} {request.url.path} → {response.status_code} ({latency}ms)")
    #            ↑ "POST /chat → 200 (2341ms)"
    #            ↑ "GET /health → 200 (1ms)"
    return response
```

**What is middleware?** Think of it as a security guard at a building entrance. Every person (request) who enters gets their badge scanned (timing started), and when they leave (response), the time is recorded. The guard doesn't care what they did inside — they just track entry and exit.

```
Request arrives → middleware starts timer
                     │
                     ▼
               Handler runs (agent does its thing)
                     │
                     ▼
Response ready → middleware logs total time → Response sent
```

**Why this matters separately from node timing:** Node timing tells you *where* time was spent inside the agent. Request timing tells you the *total* time the user waited. If nodes took 1500ms but the request took 3000ms, something else is slow (maybe JSON serialization, or network latency).

---

## Pattern 3: Loop Protection

This is critical for AI agents. In a ReAct loop, the LLM can keep calling tools forever:

```
LLM: "I'll search for that" → rag_search → 
LLM: "Let me search again with different terms" → rag_search → 
LLM: "One more search..." → rag_search → 
LLM: "Maybe if I try..." → rag_search →
... (infinite loop, burning money with every API call)
```

We prevent this with two mechanisms:

### Mechanism 1: `iteration_count` in state

```python
# In llm_node — increment counter on every LLM call
iteration = state.get("iteration_count", 0) + 1
return {
    "messages": [response],
    "iteration_count": iteration,   # Keeps going up: 1, 2, 3, 4...
}
```

### Mechanism 2: `should_continue` checks the limit

```python
# From agent/graph.py
def should_continue(state: AgentState) -> str:
    """Decide if we should continue the loop or stop."""
    messages = state["messages"]
    last_message = messages[-1]

    # LOOP PROTECTION — hard limit on iterations
    iteration = state.get("iteration_count", 0)
    if iteration >= RECURSION_LIMIT:    # RECURSION_LIMIT comes from config.py
        return "end"                     # Force stop, no matter what Claude wants

    # Normal check: does Claude want to call tools?
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"

    return "end"
```

### Mechanism 3: LangGraph's built-in recursion limit

```python
# From main.py — when invoking the graph
config = {
    "configurable": {"thread_id": conversation_id},
    "recursion_limit": RECURSION_LIMIT,    # LangGraph will raise an error if exceeded
}

result = await agent_graph.ainvoke(initial_state, config)
```

**We have TWO layers of protection:**

```
Layer 1: should_continue()     → Graceful stop (agent gives best response so far)
Layer 2: LangGraph recursion   → Hard stop (raises RecursionError if our check fails)
```

**Analogy:** Layer 1 is like a timer on a washing machine — it stops when the cycle is done. Layer 2 is like a circuit breaker — it cuts power if something goes wrong. You want both.

**What is `RECURSION_LIMIT`?** It's a number (like 10 or 25) set in `config.py`. It means "the agent can loop at most N times before we force it to stop." Higher = more capable but more expensive. Lower = safer but might cut off complex answers.

---

## Pattern 4: Tool Error Handling

Tools can fail — the database might be down, the vector search might timeout, the API might return garbage. The `tool_node` handles this gracefully:

```python
async def tool_node(state: AgentState) -> dict:
    tool_messages = []

    for tool_call in last_message.tool_calls:
        name = tool_call["name"]
        args = tool_call["args"]

        start = time.time()
        try:
            result = await execute_tool(name, args)       # Try to run the tool
        except Exception as e:
            result = f"Tool error: {str(e)}"              # ← Catch ANY exception
            logger.error(f"Tool {name} failed: {e}")      # Log it for debugging

        # The tool message ALWAYS gets created, even on failure
        tool_messages.append(
            ToolMessage(content=result, tool_call_id=tool_call_id)
        )
```

**What happens when a tool fails:**

```
Without error handling:
  Tool crashes → Python exception → Agent dies → User sees 500 error

With error handling:
  Tool crashes → Caught → "Tool error: connection refused"
  → Sent back to Claude as a ToolMessage
  → Claude reads it and responds: "I'm having trouble checking that right now..."
```

**This is clever:** Instead of crashing, we tell Claude that the tool failed. Claude is smart enough to handle this — it might try a different approach, apologize, or escalate to a human. The conversation continues gracefully.

---

## Pattern 5: Observability — `tool_calls_log`

Every tool invocation is recorded in the `tool_calls_log` list in state:

```python
# In tool_node
tool_log.append({
    "name": name,                    # Which tool: "rag_search"
    "input": args,                   # What was passed: {"query": "NSW requirements"}
    "output_length": len(result),    # How big the response was: 2847
    "latency_ms": latency_ms,        # How long it took: 234
})

return {
    "messages": tool_messages,
    "tool_calls_log": tool_log,      # Accumulated log of ALL tool calls
}
```

This log gets returned to the API caller:

```python
# From main.py — ChatResponse
return ChatResponse(
    response=final_message,
    conversation_id=conversation_id,
    tool_calls=result.get("tool_calls_log", []),  # ← Full tool log returned
    sources=[],
    workflow_status=result.get("workflow_status", "complete"),
)
```

**Why this matters:** When a user reports "the agent gave me wrong information about Proficient accreditation," you can look at the tool log and see:

```json
[
  {"name": "rag_search", "input": {"query": "Proficient requirements"}, "output_length": 2847, "latency_ms": 234},
  {"name": "check_eligibility", "input": {"qualification": "B.Ed", "jurisdiction": "NSW"}, "output_length": 423, "latency_ms": 156}
]
```

Now you know exactly what the agent searched for, what it found, and what eligibility check it ran. You can trace the problem to its source — was it bad search results? Wrong business rules? Or did Claude misinterpret good data?

---

## Pattern 6: Streaming with Server-Sent Events (SSE)

The `/chat` endpoint waits until the entire response is ready, then sends it all at once. The `/chat/stream` endpoint sends data as it becomes available — so the user sees progress in real time.

```python
# From main.py
@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Stream agent responses with step-by-step progress."""
    conversation_id = request.conversation_id or str(uuid.uuid4())

    # Same initial state as /chat
    initial_state = { ... }

    async def stream():
        # astream_events gives us a live feed of everything happening in the graph
        async for event in agent_graph.astream_events(
            initial_state,
            config,
            version="v2",      # LangGraph v2 event format
        ):
            kind = event.get("event", "")

            # When a tool starts running
            if kind == "on_tool_start":
                data = json.dumps({"step": "tool_start", "tool": event.get("name", "")})
                yield f"data: {data}\n\n"
                # Client sees: {"step": "tool_start", "tool": "rag_search"}

            # When a tool finishes
            elif kind == "on_tool_end":
                data = json.dumps({"step": "tool_end", "tool": event.get("name", "")})
                yield f"data: {data}\n\n"

            # When Claude generates a token (word/piece of word)
            elif kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    data = json.dumps({"step": "token", "content": chunk.content})
                    yield f"data: {data}\n\n"
                    # Client sees: {"step": "token", "content": "Great"}
                    # Client sees: {"step": "token", "content": " news"}
                    # Client sees: {"step": "token", "content": "!"}

        # Signal that we're done
        yield f"data: {json.dumps({'step': 'complete', 'conversation_id': conversation_id})}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")
```

### What Is SSE (Server-Sent Events)?

SSE is a web standard where the server sends a stream of messages to the client over a single HTTP connection. Each message follows this format:

```
data: {"step": "tool_start", "tool": "rag_search"}\n\n
data: {"step": "tool_end", "tool": "rag_search"}\n\n
data: {"step": "token", "content": "Based"}\n\n
data: {"step": "token", "content": " on"}\n\n
data: {"step": "token", "content": " the"}\n\n
data: {"step": "complete", "conversation_id": "abc-123"}\n\n
```

**Each line starts with `data: ` and ends with `\n\n`** (two newlines). The browser/client reads these as they arrive. This is how ChatGPT shows text appearing word by word.

### Why Streaming Matters

```
Without streaming:
  User clicks send → waits 5 seconds → entire response appears at once
  User thinks: "Is it broken? Did it freeze?"

With streaming:
  User clicks send →
    "🔍 Searching knowledge base..."    (tool_start)
    "✅ Search complete"                (tool_end)
    "Based on the policy documents..."  (tokens appear word by word)
  User thinks: "Cool, it's working!"
```

**The UX difference is dramatic.** Even if the total time is the same, streaming makes the agent feel responsive and alive.

### How a Frontend Would Consume This

```javascript
// Example frontend code (not in our codebase, but shows the pattern)
const response = await fetch('/chat/stream', {
    method: 'POST',
    body: JSON.stringify({ message: "Am I eligible?" })
});

const reader = response.body.getReader();
while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const text = new TextDecoder().decode(value);
    const event = JSON.parse(text.replace('data: ', ''));

    if (event.step === 'tool_start') showSpinner(event.tool);
    if (event.step === 'tool_end') hideSpinner(event.tool);
    if (event.step === 'token') appendToChat(event.content);
    if (event.step === 'complete') markDone();
}
```

---

## Future Patterns: What You'd Add for a Real Deployment

The patterns above are already in our codebase. Here are three more you'd add for a high-traffic production deployment.

### Circuit Breakers — Stop Calling Broken Services

**What it is:** If a service (like Weaviate or Bedrock) fails 3 times in a row, stop trying for 30 seconds. Don't keep hammering a broken service.

**Analogy:** If you call a restaurant and get a busy signal three times, you wait 10 minutes before trying again — you don't keep dialing.

```
Normal:  Request → Weaviate → Success ✅
         Request → Weaviate → Success ✅
         Request → Weaviate → Timeout ❌ (failure 1)
         Request → Weaviate → Timeout ❌ (failure 2)
         Request → Weaviate → Timeout ❌ (failure 3) → CIRCUIT OPENS 🔴

Open:    Request → Skip Weaviate → "Search temporarily unavailable"
         (for 30 seconds, we don't even try)

Half-open: Request → Try Weaviate → Success? → CIRCUIT CLOSES 🟢
                                   → Fail? → Stay open 🔴
```

**When you'd add this:** When your agent handles hundreds of requests per minute and a downstream service goes down. Without a circuit breaker, all those requests pile up waiting for timeouts.

### Checkpointing — Resume Interrupted Workflows

**What it is:** Save the workflow state to the database after each step, so if the server restarts mid-workflow, the user can resume where they left off.

Our codebase has the foundation for this in `db_tool.py`:

```python
# From tools/db_tool.py — already exists but not wired into the main workflow yet
async def save_progress(conversation_id: str, workflow_state: dict) -> dict:
    """Save workflow progress to PostgreSQL for later resume."""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO workflow_progress (conversation_id, state, updated_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (conversation_id) DO UPDATE SET state = %s, updated_at = NOW()
        """, (conversation_id, json.dumps(workflow_state), json.dumps(workflow_state)))
        conn.commit()
        return {"saved": True, "conversation_id": conversation_id}
    finally:
        conn.close()
```

**When you'd add this:** When your workflows have many steps (5+) and users might close their browser mid-flow. Losing progress after step 4 of 7 is a terrible user experience.

**How it works conceptually:**

```
Step 1: gather_info → save state to DB
Step 2: check_policy → save state to DB
                        ← SERVER CRASHES HERE
User comes back →
  Load state from DB → resume at step 3 (branching)
  User doesn't know anything went wrong
```

### Monitoring — Know When Things Break

In production, you wouldn't just log to stdout. You'd send metrics to a monitoring system:

```
┌───────────────────────────────────────────────────┐
│              What to Monitor                       │
│                                                   │
│  Latency metrics:                                 │
│  • p50, p95, p99 response times                   │
│  • LLM call latency (are API calls getting slow?) │
│  • Tool execution latency (is the DB slow?)       │
│                                                   │
│  Error rates:                                     │
│  • Tool failure rate (>5%? investigate!)           │
│  • LLM error rate (API quota? model issues?)      │
│  • Escalation rate (>20%? agent isn't helpful)     │
│                                                   │
│  Business metrics:                                │
│  • Questions answered vs escalated                │
│  • Average tools called per request               │
│  • Which tools are used most                      │
│  • Workflow completion rate                        │
│                                                   │
│  Cost tracking:                                   │
│  • Tokens used per request                        │
│  • LLM API cost per day                           │
│  • Most expensive queries                         │
└───────────────────────────────────────────────────┘
```

**Alerting rules you'd set up:**

| Alert | Condition | Action |
|---|---|---|
| High latency | p95 > 10 seconds | Check LLM API status |
| High error rate | Tool failures > 5% in 5 min | Check Weaviate / PostgreSQL health |
| High escalation | Escalation rate > 30% in 1 hour | Review agent prompts, add knowledge |
| Cost spike | Token usage > 2x daily average | Check for looping agents |
| Service down | Health check fails 3 times | Restart service, page on-call |

**Tools you'd use:** AWS CloudWatch (since we're on AWS), Datadog, Grafana, or even a simple dashboard reading from the `tool_call_log` PostgreSQL table.

---

## Putting It All Together — The Full Request Lifecycle

Here's what happens for a single `/chat` request with all production patterns active:

```
1. REQUEST ARRIVES
   │
   ├─ Middleware: Start timer ⏱️
   │
   ▼
2. INITIAL STATE CREATED
   │  messages: [user_message]
   │  iteration_count: 0
   │  tool_calls_log: []
   │
   ▼
3. ROUTER NODE
   │  LLM classifies intent
   │  Logger: "Router → eligibility_check"
   │
   ▼
4. GATHER_INFO NODE
   │  LLM extracts JSON
   │  State: workflow_data = {qualification: "B.Ed", ...}
   │
   ▼
5. CHECK_POLICY NODE
   │  Calls check_eligibility()
   │  tool_calls_log: [{name: "check_eligibility", latency: 156ms}]
   │  State: policy_result = {eligible: true, ...}
   │
   ▼
6. ROUTE_AFTER_POLICY
   │  Reads policy_result.eligible → True
   │  Routes → eligible_path
   │
   ▼
7. ELIGIBLE_PATH NODE
   │  Creates checklist in PostgreSQL
   │  LLM writes friendly response
   │  State: workflow_status = "completed"
   │
   ▼
8. RESPONSE BUILT
   │  Extract final AI message
   │  Include tool_calls_log
   │  Include workflow_status
   │
   ├─ Middleware: Stop timer ⏱️ → "POST /chat → 200 (2341ms)"
   │
   ▼
9. JSON RESPONSE SENT
   {
     "response": "Great news! You're eligible...",
     "conversation_id": "abc-123",
     "tool_calls": [{...}],
     "workflow_status": "completed"
   }
```

**Every step is logged. Every tool is timed. Every error is caught. The loop is bounded. The state is tracked.** That's what production-ready looks like.

---

## What We Have Now

```
BEFORE this step:              AFTER this step:
──────────────────             ──────────────────
Agent works                    Agent works RELIABLY
No logging                     Structured logs with timing
No loop limits                 Bounded iterations + recursion limit
Tool crashes = 500 error       Tool crashes = graceful degradation
No visibility into agent       Full tool call log for debugging
Blocking responses only        Streaming for real-time UX
No cost awareness              Token/latency tracking foundation
```

---

## Key Takeaways

1. **Structured logging with timing** is your #1 debugging tool — log what happened and how long it took
2. **Request middleware** gives you total request latency separate from internal timings
3. **Loop protection needs two layers** — graceful (`should_continue`) and hard (`recursion_limit`)
4. **Tool error handling** turns crashes into conversations — Claude can recover from tool failures
5. **`tool_calls_log`** is your audit trail — trace every decision the agent made
6. **Streaming (SSE)** dramatically improves perceived performance and user trust
7. **Circuit breakers, checkpointing, and monitoring** are your next steps for high-traffic production

---

## Quick Reference: Where Each Pattern Lives

| Pattern | File | Function/Section |
|---|---|---|
| LLM timing | `agent/graph.py` | `llm_node()` |
| Tool timing | `agent/graph.py` | `tool_node()` |
| Tool error handling | `agent/graph.py` | `tool_node()` try/except |
| Loop protection | `agent/graph.py` | `should_continue()` |
| Request middleware | `main.py` | `log_requests()` |
| Tool calls log | `agent/graph.py` | `tool_node()` → `tool_calls_log` |
| Streaming/SSE | `main.py` | `chat_stream()` |
| Recursion limit config | `config.py` | `RECURSION_LIMIT` |
| Checkpoint foundation | `tools/db_tool.py` | `save_progress()` |

---

## What's Next?

You now have a complete picture of the Teacher Accreditation Agent:

- **Step 1:** Infrastructure (Docker, databases)
- **Step 2:** Data ingestion (loading knowledge into Weaviate)
- **Step 3:** RAG search (semantic retrieval)
- **Step 4:** Basic agent (single-tool ReAct)
- **Step 5:** Multi-tool agent (4 tools, autonomous selection)
- **Step 6:** Eligibility workflow (structured branching)
- **Step 7:** Production patterns (reliability, observability, streaming)

From here, you could extend the agent with new workflows, add a frontend, deploy to AWS, or integrate with real NESA systems. The patterns in these tutorials scale to much larger and more complex agents.
