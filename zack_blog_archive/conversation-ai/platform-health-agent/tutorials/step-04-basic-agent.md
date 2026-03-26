# Tutorial Step 4: The Basic Agent — LangGraph, ReAct, and Tool Calling

> **Goal:** Build an AI agent that reasons, uses tools, and answers questions in a loop  
> **Time:** ~20 minutes  
> **Prerequisites:** Steps 1–3 (infrastructure running, documents ingested, RAG tool built)  

---

## What We're Building in This Step

In Step 3 we built a search tool. But a tool sitting in a file does nothing on its own — it needs a **brain** to decide *when* to use it. That brain is our **LangGraph agent**.

```
┌──────────────────────────────────────────────────────┐
│               What We Build Here                      │
│                                                       │
│   AgentState        — the agent's memory              │
│   llm_node          — calls Claude to think           │
│   tool_node         — executes tools Claude requests  │
│   should_continue   — decides: loop again or stop?    │
│   create_agent_graph — wires it all into a graph      │
│   FastAPI endpoints — /chat and /chat/stream          │
│                                                       │
│   The result: a working AI agent you can talk to      │
│   via API that searches knowledge and answers         │
│   questions accurately.                               │
└──────────────────────────────────────────────────────┘
```

---

## Key Concepts (Explained for Beginners)

### What Is LangGraph?

**LangGraph** is a Python library for building AI agents as **graphs** (nodes connected by edges). It's made by the same team as LangChain, but solves a different problem:

| | LangChain | LangGraph |
|---|---|---|
| Structure | **Chain** — linear A → B → C | **Graph** — nodes with conditional edges and loops |
| Control flow | Fixed sequence | Dynamic — can loop, branch, skip |
| Best for | Simple pipelines (translate → summarize) | Agents that reason and decide what to do next |
| State | Passed forward only | Shared state that all nodes read/write |

**Analogy:** LangChain is like an assembly line — parts move in one direction. LangGraph is like a flowchart — you can loop back, take different branches, and make decisions at each step.

**Why LangGraph for this project?** Because our agent needs to:
1. Receive a question
2. **Decide** whether it needs to search (not always!)
3. If yes → search → read results → **decide** again (maybe search differently?)
4. When it has enough info → generate a final answer

That decision-making loop is exactly what graphs enable and chains can't do.

### The ReAct Pattern (Reason + Act)

Our agent uses a pattern called **ReAct**, which stands for **Reason + Act**. Here's how it works:

```
┌─────────────────────────────────────────────────────────────────┐
│                    The ReAct Loop                                │
│                                                                  │
│    ┌──────────┐     has tool calls?     ┌──────────┐            │
│    │          │ ──── YES ─────────────► │          │            │
│    │   LLM    │                         │  TOOLS   │            │
│    │  (think) │ ◄───────────────────── │ (act)    │            │
│    │          │     return results       │          │            │
│    └────┬─────┘                         └──────────┘            │
│         │                                                        │
│         │ NO tool calls (has final answer)                       │
│         ▼                                                        │
│    ┌──────────┐                                                  │
│    │   END    │  → Return response to user                      │
│    └──────────┘                                                  │
│                                                                  │
│  Each trip around the loop:                                      │
│    1. REASON: Claude reads everything so far and thinks          │
│    2. DECIDE: Call a tool? Or answer directly?                   │
│    3. ACT:    If tool → execute it → feed results back → repeat │
│    4. ANSWER: If no tool → we're done                           │
└─────────────────────────────────────────────────────────────────┘
```

**Example conversation trace:**

```
User: "What PD hours do I need to maintain accreditation?"

Loop 1 — REASON:
  Claude thinks: "I need to search for PD hour requirements"
  Claude returns: tool_call(rag_search, query="PD hours maintain accreditation")
  
Loop 1 — ACT:
  rag_search runs → finds 4 relevant chunks → returns formatted context

Loop 2 — REASON:
  Claude reads the search results
  Claude thinks: "I have enough info to answer now"
  Claude returns: "To maintain your accreditation, you need 100 hours of PD
                   over 5 years, including 50 hours of NESA-registered PD..."
  
Loop 2 — no tool calls → END
```

**When does Claude answer directly (no tools)?**

- Greeting: "Hi there!" → No search needed
- Clarification: "Can you explain what you mean?" → Just a follow-up
- Simple known facts: Things in the system prompt

Claude decides this automatically based on the conversation context and available tools. If the question *might* be in the knowledge base, Claude will search. If it's clearly a conversational response, it won't.

---

## The Code: Four Files Working Together

```
agent-backend/
├── agent/
│   ├── state.py     ← AgentState (the shared memory)
│   ├── prompts.py   ← System prompt (the agent's personality)
│   └── graph.py     ← The ReAct graph (the brain)
└── main.py          ← FastAPI server (the interface)
```

Let's walk through each one.

---

### File 1: `agent/state.py` — The Agent's Memory

```python
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """State passed through the LangGraph workflow."""

    # Conversation — add_messages appends new messages (never overwrites)
    messages: Annotated[list, add_messages]

    # Workflow tracking
    current_workflow: str     # e.g., "general_qa", "eligibility_check"
    workflow_step: int        # Which step we're on
    workflow_status: str      # "in_progress", "completed", "escalated"

    # Tool tracking (observability)
    tool_calls_log: list[dict]   # [{name, input, output, latency_ms}]
    iteration_count: int          # How many times the LLM has been called
```

**What is TypedDict?** A regular Python `dict` can hold anything — `{"age": 25, "name": "Alice", 42: True}`. A `TypedDict` says "this dict must have exactly these keys with these types." It's like a form with labelled fields vs a blank piece of paper.

**Why not a regular class?** LangGraph requires the state to be a `TypedDict` (or similar). This is because LangGraph needs to inspect the type annotations to know how to merge updates from different nodes. A regular class wouldn't give LangGraph that information.

**What does `Annotated[list, add_messages]` do?**

This is the cleverest part. The `add_messages` annotation tells LangGraph: "When a node returns new messages, **append** them to the list — don't replace it."

```python
# Without add_messages (default behavior):
state["messages"] = [msg1, msg2]   # Node returns [msg3]
state["messages"] = [msg3]          # ❌ msg1 and msg2 are GONE

# With add_messages:
state["messages"] = [msg1, msg2]   # Node returns [msg3]
state["messages"] = [msg1, msg2, msg3]  # ✅ Appended!
```

This is called a **reducer** — it defines *how* to combine the old state with new updates. Without it, every node would wipe out the conversation history.

**Analogy:** Think of `messages` as a notebook that every node can write in. The `add_messages` reducer means "only add pages — never rip out old ones."

---

### File 2: `agent/prompts.py` — The Agent's Personality

```python
SYSTEM_PROMPT = """You are a NESA accreditation assistant designed to help
New South Wales Education Standards Authority (NESA) staff and teachers
with accreditation processes.

Core Identity
- Always identify yourself as a NESA accreditation assistant.
- Never reference your underlying AI model, knowledge bases, or technical infrastructure.
- Refer to your information sources only as "NESA information" or "NESA documentation".

Capabilities
- You can search NESA documentation to answer accreditation questions.
- You can guide users through multi-step accreditation workflows.
...

Available Tools
You have access to tools. Use them to:
- Search the knowledge base for policy information
- Check accreditation requirements and eligibility
...

IMPORTANT: For any action that modifies data (create, update, delete),
always confirm with the user before proceeding.
"""
```

**Why does the prompt matter so much?** The system prompt is the single most important piece of configuration. It controls:

1. **Identity** — The agent says "Based on NESA documentation" instead of "As Claude, I..."
2. **Behavior** — "Always consult documentation before responding" means Claude will search first, not guess
3. **Safety** — "Confirm before modifying data" prevents accidental changes
4. **Tool usage** — Telling Claude what tools exist and when to use them guides its decisions

**The router prompt** (`ROUTER_PROMPT`) is for a future feature — it will classify which workflow to use (eligibility check, application guidance, etc.). For now, everything goes through `general_qa`.

---

### File 3: `agent/graph.py` — The Brain

This is the biggest file, so we'll walk through it section by section.

#### Tool Definitions — What Claude Sees

```python
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "rag_search",
            "description": (
                "Search the knowledge base for relevant documents about "
                "accreditation, policies, technical documentation, blog posts, "
                "and Confluence pages. Use this tool whenever the user asks a "
                "question that might be answered by stored documents."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query — rephrase the user's "
                                       "question for optimal retrieval",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of results to return (default 5)",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        },
    },
]
```

**This is NOT the actual function.** This is a JSON **description** of the function that Claude reads. It's like a menu at a restaurant — it tells you what's available and what each dish contains, but it's not the food itself.

Claude reads this description and decides:
- "The user asked about accreditation requirements. The `rag_search` tool searches for accreditation documents. I should call it."
- "The user said 'hello'. No tool is relevant. I'll just respond."

**Key detail:** The description says "rephrase the user's question for optimal retrieval." This tells Claude to transform "what do I need to be a teacher?" into a better search query like "teacher accreditation requirements NSW" — improving search quality.

#### Tool Execution — What Actually Runs

```python
async def execute_tool(name: str, args: dict) -> str:
    """Execute a tool by name and return the result as a string."""
    if name == "rag_search":
        from tools.rag_tool import rag_search, format_context_for_llm
        result = await rag_search(
            query=args.get("query", ""),
            top_k=args.get("top_k", 5),
        )
        # If search succeeded and found results, format them for Claude
        if result.success and result.results:
            return format_context_for_llm(result)
        # Otherwise return the error/empty message
        return result.message
    return f"Unknown tool: {name}"
```

This is the bridge between Claude's tool *request* and the actual Python *function*. When Claude says "call rag_search with query='PD hours'", this function:
1. Looks up "rag_search" in the registry
2. Calls the real `rag_search()` from Step 3
3. Formats the results and returns a string

**Why return a string?** Because the result goes back into the conversation as a `ToolMessage`, and messages are text. Claude will read this text to formulate its answer.

#### The LLM Node — Where Claude Thinks

```python
async def llm_node(state: AgentState) -> dict:
    """Call Claude with current messages and available tools."""
    llm = _get_llm()   # Create Bedrock Claude client

    # Prepend system prompt if not already there
    messages = list(state["messages"])
    if not messages or not isinstance(messages[0], SystemMessage):
        messages.insert(0, SystemMessage(content=SYSTEM_PROMPT))

    # Bind tools so Claude knows what's available
    llm_with_tools = llm.bind_tools(TOOLS)

    # Send everything to Claude and get a response
    response = await llm_with_tools.ainvoke(messages)

    # Track how many times we've looped (for loop protection)
    iteration = state.get("iteration_count", 0) + 1
    return {
        "messages": [response],       # add_messages will APPEND this
        "iteration_count": iteration,
    }
```

**What does `bind_tools(TOOLS)` do?** It tells Claude: "Here are the tools you can use. When you want to use one, return a special `tool_calls` field in your response instead of (or alongside) text."

**What does `ainvoke` return?** An `AIMessage` that contains either:
- **Just text** → Claude has a final answer (e.g., `"Hello! How can I help?"`)
- **`tool_calls`** → Claude wants to use a tool (e.g., `[{name: "rag_search", args: {query: "..."}}]`)

The return value `{"messages": [response]}` adds Claude's response to the state. Thanks to `add_messages`, it's appended to the conversation history — the existing user message and any previous tool results are preserved.

#### The Tool Node — Where Actions Happen

```python
async def tool_node(state: AgentState) -> dict:
    """Execute all tool calls from the last LLM response."""
    messages = state["messages"]
    last_message = messages[-1]    # The AIMessage with tool_calls

    tool_messages = []
    tool_log = list(state.get("tool_calls_log", []))

    for tool_call in last_message.tool_calls:
        name = tool_call["name"]          # "rag_search"
        args = tool_call["args"]          # {"query": "PD hours", "top_k": 5}
        tool_call_id = tool_call["id"]    # Unique ID to match request ↔ response

        start = time.time()
        try:
            result = await execute_tool(name, args)
        except Exception as e:
            result = f"Tool error: {str(e)}"   # Don't crash, return error as text
        latency_ms = int((time.time() - start) * 1000)

        # Create a ToolMessage — this is how results get back to Claude
        tool_messages.append(
            ToolMessage(content=result, tool_call_id=tool_call_id)
        )

        # Log it for observability
        tool_log.append({
            "name": name,
            "input": args,
            "output_length": len(result),
            "latency_ms": latency_ms,
        })

    return {
        "messages": tool_messages,     # Appended to conversation
        "tool_calls_log": tool_log,    # Updated log
    }
```

**What is a `ToolMessage`?** It's a special message type that says "this is the result of a tool call." The `tool_call_id` links it back to the specific request, so Claude knows which tool returned what.

**The message flow looks like this:**

```
messages = [
  SystemMessage("You are a NESA accreditation assistant..."),
  HumanMessage("What PD hours do I need?"),
  AIMessage(tool_calls=[{name: "rag_search", id: "call_123", ...}]),
  ToolMessage(content="[Source 1: ...] ...", tool_call_id="call_123"),
  AIMessage("Based on NESA documentation, you need 100 hours...")  ← final answer
]
```

Each message builds on the previous ones. Claude can see the *entire* conversation, including its own tool requests and the results.

#### The Router — Should We Continue or Stop?

```python
def should_continue(state: AgentState) -> str:
    """Decide if we should continue the loop or stop."""
    messages = state["messages"]
    last_message = messages[-1]

    # Loop protection — don't let the agent run forever
    iteration = state.get("iteration_count", 0)
    if iteration >= RECURSION_LIMIT:    # Default: 10
        return "end"

    # If the last message has tool calls, execute them
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"

    # Otherwise, Claude gave a final answer — we're done
    return "end"
```

This is a **conditional edge** — it runs after every LLM call and decides where to go next. The logic is simple:

1. **Hit the loop limit?** → Stop (safety valve against infinite loops)
2. **Claude wants tools?** → Go to tool_node
3. **Claude gave a text answer?** → Done, go to END

**Why loop protection?** Imagine Claude keeps searching but never finds a satisfying answer. Without a limit, it would loop forever, burning API credits and never responding. The `RECURSION_LIMIT` (default 10) ensures the agent always eventually stops.

#### Building the Graph — Wiring It All Together

```python
def create_agent_graph():
    """Create and compile the LangGraph agent."""
    graph = StateGraph(AgentState)   # Create a graph that uses AgentState

    # Add nodes (the things that DO stuff)
    graph.add_node("llm", llm_node)      # Node that calls Claude
    graph.add_node("tools", tool_node)   # Node that executes tools

    # Entry point: always start with the LLM
    graph.set_entry_point("llm")

    # Conditional edge: after LLM, check if we need tools or are done
    graph.add_conditional_edges(
        "llm",                              # From this node...
        should_continue,                    # Run this function...
        {"tools": "tools", "end": END},     # Map return values to destinations
    )

    # After tools execute, always go back to LLM
    graph.add_edge("tools", "llm")

    return graph.compile()   # Compile into an executable graph
```

**Here's the complete graph as ASCII art:**

```
                    ┌─────────────────────────────┐
                    │          START               │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
                    ┌─────────────────────────────┐
              ┌───► │        llm_node              │
              │     │  (Claude thinks + decides)   │
              │     └──────────────┬───────────────┘
              │                    │
              │           should_continue()
              │                 /      \
              │          "tools"        "end"
              │              /              \
              │             ▼                ▼
              │  ┌──────────────────┐   ┌────────┐
              │  │    tool_node     │   │  END   │
              │  │ (execute tools)  │   │        │
              │  └────────┬─────────┘   └────────┘
              │           │
              └───────────┘
                always loops back
```

**What does `graph.compile()` do?** It takes the graph definition (nodes, edges, entry point) and creates an executable object. Think of it like compiling code — you write the source (the graph definition), then compile it into something that can actually run. Once compiled, you call `graph.ainvoke()` or `graph.astream_events()` to run it.

**Why compile?** Compilation validates the graph (checks for unreachable nodes, missing edges, etc.) and optimises it for execution. You compile once at startup, then run it many times — one per conversation.

---

### File 4: `main.py` — The FastAPI Server

This is the web server that lets you talk to the agent via HTTP.

#### Startup — Compile Once, Use Many Times

```python
agent_graph = None   # Global variable for the compiled graph

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    global agent_graph
    print("🚀 Agent backend starting...")
    agent_graph = create_agent_graph()   # Compile the graph ONCE
    print("✅ LangGraph agent compiled")
    yield                                 # Server is running
    print("🛑 Agent backend shutting down...")
```

**Why compile at startup?** Graph compilation is slow-ish (it validates everything). By doing it once at startup, every request reuses the same compiled graph. This is like preheating an oven — you heat it once, then bake many things.

#### The `/chat` Endpoint — One-Shot Responses

```python
@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Handle a chat message — invoke the LangGraph agent."""
    conversation_id = request.conversation_id or str(uuid.uuid4())

    config = {
        "configurable": {"thread_id": conversation_id},
        "recursion_limit": RECURSION_LIMIT,
    }

    result = await agent_graph.ainvoke(
        {
            "messages": [HumanMessage(content=request.message)],
            "current_workflow": "general_qa",
            "workflow_step": 0,
            "workflow_status": "in_progress",
            "tool_calls_log": [],
            "iteration_count": 0,
        },
        config,
    )
```

**What's happening step by step:**

1. **Generate a conversation ID** — if the user didn't provide one, create a new UUID
2. **Set config** — `thread_id` identifies this conversation; `recursion_limit` is the safety limit
3. **Invoke the graph** — pass the initial state with the user's message
4. **Wait for completion** — the graph runs the full ReAct loop and returns the final state

**Extracting the final response:**

```python
    # Walk backwards through messages to find the last text response
    final_message = ""
    for msg in reversed(result["messages"]):
        if isinstance(msg, AIMessage) and msg.content and not msg.tool_calls:
            final_message = msg.content
            break
```

Why walk backwards? Because the messages list looks like:
```
[System, Human, AI(tool_call), Tool, AI(tool_call), Tool, AI("Here's your answer...")]
```

The last `AIMessage` without tool calls IS the final answer.

#### The `/chat/stream` Endpoint — Real-Time Progress

```python
@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Stream agent responses with step-by-step progress."""
    async def stream():
        async for event in agent_graph.astream_events(..., version="v2"):
            kind = event.get("event", "")

            if kind == "on_tool_start":
                # Tell the frontend: "I'm searching now..."
                yield f"data: {json.dumps({'step': 'tool_start', ...})}\n\n"
            elif kind == "on_tool_end":
                # Tell the frontend: "Search complete!"
                yield f"data: {json.dumps({'step': 'tool_end', ...})}\n\n"
            elif kind == "on_chat_model_stream":
                # Stream individual tokens as they arrive
                yield f"data: {json.dumps({'step': 'token', 'content': ...})}\n\n"

        yield f"data: {json.dumps({'step': 'complete', ...})}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")
```

**What is Server-Sent Events (SSE)?** It's a way for the server to push updates to the client in real-time. Instead of waiting 5 seconds for the full response, the frontend sees:

```
data: {"step": "tool_start", "tool": "rag_search"}     ← "Searching..."
data: {"step": "tool_end", "tool": "rag_search"}       ← "Found results!"
data: {"step": "token", "content": "Based"}             ← Typing...
data: {"step": "token", "content": " on"}
data: {"step": "token", "content": " NESA"}
data: {"step": "token", "content": " documentation"}
...
data: {"step": "complete", "conversation_id": "abc123"}
```

This is what makes chatbots feel responsive — you see the answer being "typed out" word by word.

---

## How Tool Calling Actually Works (The Full Picture)

Let's trace exactly what happens when a user asks a question:

```
1. User sends: POST /chat {"message": "What PD hours do I need?"}

2. main.py creates initial state:
   {
     messages: [HumanMessage("What PD hours do I need?")],
     iteration_count: 0,
     tool_calls_log: [],
     ...
   }

3. Graph starts → llm_node:
   - Prepends SystemMessage (the NESA assistant prompt)
   - Calls Claude with messages + TOOLS
   - Claude returns: AIMessage(tool_calls=[{
       name: "rag_search",
       args: {query: "professional development PD hours requirements accreditation"},
       id: "call_abc123"
     }])
   - State updates: messages now has [Human, AI(tool_call)], iteration=1

4. should_continue() → last message has tool_calls → return "tools"

5. Graph goes to → tool_node:
   - Reads tool_calls from the AIMessage
   - Calls execute_tool("rag_search", {query: "...", top_k: 5})
   - rag_search runs (embed → vector search → format)
   - Creates ToolMessage(content="[Source 1: ...] ...", tool_call_id="call_abc123")
   - State updates: messages now has [Human, AI(tool_call), Tool]

6. Graph goes to → llm_node (second time):
   - Claude now sees: System + Human + AI(tool_call) + Tool(search results)
   - Claude reads the search results and generates a text answer
   - Returns: AIMessage("Based on NESA documentation, you need 100 hours...")
   - State updates: messages now has [Human, AI(tool_call), Tool, AI(answer)], iteration=2

7. should_continue() → last message has NO tool_calls → return "end"

8. Graph goes to → END

9. main.py extracts the final AIMessage and returns:
   {
     "response": "Based on NESA documentation, you need 100 hours...",
     "conversation_id": "...",
     "tool_calls": [{name: "rag_search", input: {...}, latency_ms: 342}],
     "sources": [],
     "workflow_status": "complete"
   }
```

---

## Testing with curl

### Start the server

```bash
cd ~/zz/Documents/conversation-ai/teacher-accreditation-agent/agent-backend
uvicorn main:app --reload --port 8000
```

### Health check

```bash
curl http://localhost:8000/health
```
```json
{"status": "healthy", "agent": true}
```

### Send a chat message (non-streaming)

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What are the requirements for Proficient Teacher accreditation?"}'
```
```json
{
  "response": "Based on NESA documentation, Proficient Teacher accreditation requires...",
  "conversation_id": "a1b2c3d4-...",
  "tool_calls": [
    {
      "name": "rag_search",
      "input": {"query": "Proficient Teacher accreditation requirements"},
      "output_length": 2341,
      "latency_ms": 342
    }
  ],
  "sources": [],
  "workflow_status": "complete"
}
```

### Send a streaming message

```bash
curl -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "How do I maintain my accreditation?"}' \
  --no-buffer
```
```
data: {"step": "tool_start", "tool": "rag_search"}
data: {"step": "tool_end", "tool": "rag_search"}
data: {"step": "token", "content": "To"}
data: {"step": "token", "content": " maintain"}
data: {"step": "token", "content": " your"}
...
data: {"step": "complete", "conversation_id": "e5f6g7h8-..."}
```

### Continue an existing conversation

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What about for Highly Accomplished?", "conversation_id": "a1b2c3d4-..."}'
```

---

## Key Concepts Summary

### Compiled Graph

The graph is defined declaratively (add nodes, add edges), then **compiled** into an executable. Think of it like writing a recipe (definition) vs actually cooking (execution). You write the recipe once, compile it, and run it many times.

```python
graph = StateGraph(AgentState)    # Start writing the recipe
graph.add_node("llm", llm_node)  # Add steps
graph.add_edge("tools", "llm")   # Connect steps
compiled = graph.compile()        # "Recipe ready to cook"
result = compiled.ainvoke(state)  # Actually cook (for each request)
```

### Conditional Edges

Normal edges are fixed: "after A, always go to B." Conditional edges run a function to decide: "after A, run `should_continue()` — if it returns `'tools'` go to B, if `'end'` go to C."

```python
# Fixed edge — always goes from tools back to llm
graph.add_edge("tools", "llm")

# Conditional edge — depends on the result of should_continue()
graph.add_conditional_edges(
    "llm",                             # From this node
    should_continue,                   # Run this function
    {"tools": "tools", "end": END},    # Map outputs to destinations
)
```

### Loop Protection

Without protection, a confused agent could loop forever (search → not satisfied → search again → repeat). The `iteration_count` in `AgentState` prevents this:

```python
# In should_continue():
if iteration >= RECURSION_LIMIT:   # Default: 10
    return "end"                    # Force stop after 10 loops
```

In practice, most questions resolve in 1–2 loops. Hitting the limit usually means something is wrong (bad prompt, missing documents, etc.).

---

## What We Have Now

```
BEFORE this step:        AFTER this step:
──────────────────       ─────────────────
RAG tool exists          Agent USES the RAG tool intelligently
No reasoning loop        ReAct loop: think → search → think → answer
No API                   FastAPI with /chat and /chat/stream
No conversation flow     Messages accumulate through the loop
No safety limits         Loop protection via RECURSION_LIMIT
```

---

## Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| `agent is None` on `/chat` | Server didn't start properly | Check startup logs for errors |
| `NoCredentialsError` | AWS profile not configured | Set `AWS_PROFILE` in `.env` |
| Agent loops without answering | System prompt or tool description issue | Check `RECURSION_LIMIT`, review prompts |
| Empty response | No documents match the query | Check Weaviate has documents (Step 2) |
| `Connection refused` on port 8000 | Server not running | Run `uvicorn main:app --port 8000` |
| Slow responses (>10s) | Bedrock cold start or large context | First call is always slower; subsequent calls are faster |

---

## Next Step

**Step 5: Multi-Step Workflows** — we'll add conditional routing so the agent can run different workflows (eligibility checks, application guidance, maintenance renewal) depending on what the user needs.
