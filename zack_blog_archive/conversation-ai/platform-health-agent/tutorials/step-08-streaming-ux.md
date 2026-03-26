# Tutorial Step 8: Streaming UX — Live Responses, Source Citations, and Timing

> **Goal:** Stream LLM tokens to the browser in real-time, show source citations, and display response timing  
> **Time:** ~25 minutes  
> **Prerequisites:** Steps 5–7 (Multi-Tool Agent, Eligibility Workflow, Production Patterns)  

---

## What We're Building in This Step

Up until now, our agent works like this: the user sends a message, the backend does *all* the thinking, and then a complete response appears at once. That might take 3–8 seconds of staring at a spinner.

In this step, we make the experience feel **alive** — tokens appear as they're generated (like ChatGPT), tool usage is shown in real-time, and source citations appear at the end with confidence scores.

```
┌────────────────────────────────────────────────────────────┐
│              What We Build Here                            │
│                                                            │
│  🔤 Token streaming      → Words appear as they generate   │
│  🔧 Tool indicators      → "Calling rag_search..." shown   │
│  📚 Source citations      → Documents used + confidence %   │
│  ⏱️ Response timing       → "Generated in 2.3s"            │
│  🔄 Graceful fallback    → Falls back to non-streaming     │
│                                                            │
│  Before: [Spinner... 5 seconds... full wall of text]       │
│  After:  [Words flow in one by one like a real person]     │
└────────────────────────────────────────────────────────────┘
```

---

## Key Concepts (Explained for Beginners)

### What Are Server-Sent Events (SSE)?

When you make a normal HTTP request, you send a request and get back **one** response. Done. Connection closed.

SSE is different: you send a request and the server keeps the connection **open**, sending you chunks of data over time. Think of it like a radio broadcast — you tune in (make the request) and the station keeps sending (the server keeps pushing data).

```
Normal HTTP:
  Client  ──request──▶  Server
  Client  ◀──response── Server
  (connection closed)

SSE (Server-Sent Events):
  Client  ──request──▶  Server
  Client  ◀──chunk 1─── Server
  Client  ◀──chunk 2─── Server
  Client  ◀──chunk 3─── Server
  Client  ◀──chunk N─── Server
  (connection stays open until done)
```

**The SSE format is dead simple.** Each message is a line starting with `data:` followed by JSON, ending with two newlines:

```
data: {"event": "token", "content": "Hello"}

data: {"event": "token", "content": " world"}

data: {"event": "complete", "latency_ms": 2340}

```

That's it. No special protocol, no handshake, no binary framing. Just text lines over HTTP.

**Why SSE instead of WebSockets?**

| Feature | SSE | WebSockets |
|---|---|---|
| Direction | One-way (server → client) | Two-way |
| Complexity | Just HTTP, very simple | Separate protocol, more setup |
| Reconnection | Built-in auto-reconnect | You implement it yourself |
| Good for | Streaming responses | Chat, games, real-time collab |

For our use case — streaming an LLM response — data only flows **one way** (server to browser). SSE is the simpler, better fit.

---

### What Is `astream_events`?

LangGraph (the framework our agent runs on) provides a method called `astream_events()` that lets you **watch everything the graph does** as it happens. Instead of waiting for the graph to finish and getting the final result, you get a stream of events:

```python
async for event in agent_graph.astream_events(state, config, version="v2"):
    print(event["event"])  # What happened?
    # "on_chain_start"         → A graph node started running
    # "on_chat_model_stream"   → The LLM produced a token
    # "on_chain_end"           → A graph node finished
```

Think of it like a sports commentator. Without streaming, you get: "Final score: 3-1." With `astream_events`, you get: "Kickoff... pass to the left... SHOT... GOAL! 1-0... another pass..."

**Event types we care about:**

| Event | When It Fires | What We Do |
|---|---|---|
| `on_chain_start` | A graph node begins executing | Show "🔧 Calling tool_name..." |
| `on_chat_model_stream` | The LLM produces one token | Send that token to the browser |
| `on_chain_end` | A graph node finishes | Extract sources from tool results |

**The critical detail:** Every event includes `metadata.langgraph_node` — this tells you **which node** in the graph produced the event. This is how we avoid leaking intermediate outputs (more on this below).

---

## The Streaming Problem: Content Blocks

Before we get to the implementation, there's a gotcha that bit us in three places.

**The problem:** AWS Bedrock's Converse API doesn't return LLM output as a simple string. It returns a **list of content blocks**:

```python
# What you might expect:
response.content = "Hello, I can help with that."

# What Bedrock Converse actually returns:
response.content = [
    {"type": "text", "text": "Hello, I can help with that.", "index": 0}
]
```

This is a list with one dictionary inside, not a string. If your code does `response.content.strip()` or `"keyword" in response.content`, it will either crash or give wrong results.

**The fix is simple but needs to be applied everywhere:**

```python
def extract_text(content):
    """Safely extract text whether content is a string or list of blocks."""
    if isinstance(content, list):
        # Bedrock Converse format: list of content blocks
        return " ".join(
            block.get("text", "") 
            for block in content 
            if isinstance(block, dict) and block.get("type") == "text"
        )
    return str(content)  # Already a string, just return it
```

**Where this bit us:**

| Location | What Broke | Fix |
|---|---|---|
| `router_node` in `graph.py` | Router checks if output is "general_qa" or "incident_triage" — failed because content was a list, not a string | Wrap in `extract_text()` before comparing |
| `_call_llm()` in `incident_triage.py` | Tried to use `.strip()` on a list | Wrap in `extract_text()` |
| Streaming token handler | Token chunks arrived as content blocks instead of plain text | Check `isinstance(content, list)` and extract text from blocks |

**Lesson:** When using AWS Bedrock Converse, always defensively check `isinstance(content, list)` before treating LLM output as a string. This is a Bedrock-specific quirk — OpenAI and Anthropic direct APIs return plain strings.

---

## Backend Implementation: The `/chat/stream` Endpoint

This is the core of the streaming UX. Let's walk through it piece by piece.

### The Endpoint Structure

```python
@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Stream LLM response tokens, tool events, and sources via SSE."""
    
    async def stream():
        start_time = time.time()
        
        # Build the initial state for the graph
        state = {
            "messages": [HumanMessage(content=request.message)],
            "iteration_count": 0,
            "tool_calls_log": [],
        }
        config = {"recursion_limit": settings.RECURSION_LIMIT}
        
        async for event in agent_graph.astream_events(state, config, version="v2"):
            kind = event.get("event", "")
            node = event.get("metadata", {}).get("langgraph_node", "")
            
            # ... handle different event types (see below) ...
        
        # After all events, send completion with timing
        latency_ms = int((time.time() - start_time) * 1000)
        yield f"data: {json.dumps({'event': 'complete', 'latency_ms': latency_ms})}\n\n"
    
    return StreamingResponse(stream(), media_type="text/event-stream")
```

**What's happening:**
1. We define an `async def stream()` generator — this is a function that `yield`s values one at a time instead of returning once
2. We iterate over `astream_events` — each event is something the graph did
3. For each event, we format it as SSE (`data: {...}\n\n`) and `yield` it
4. FastAPI's `StreamingResponse` sends each yielded chunk to the client immediately

### Handling Token Events

```python
# Inside the stream() generator:

if kind == "on_chat_model_stream":
    # A token arrived from the LLM
    
    # CRITICAL: Only stream tokens from the answer node, not the router
    if node in ("router", "gather_symptoms", "search_docs"):
        continue  # Skip — these are intermediate nodes
    
    chunk = event.get("data", {}).get("chunk")
    if chunk and hasattr(chunk, "content"):
        content = chunk.content
        
        # Handle Bedrock content blocks
        if isinstance(content, list):
            text = "".join(
                block.get("text", "") 
                for block in content 
                if isinstance(block, dict)
            )
        else:
            text = content
        
        # Don't stream tool call JSON to the user
        if text and not chunk.tool_call_chunks:
            yield f"data: {json.dumps({'event': 'token', 'content': text})}\n\n"
```

Two critical filters here. Let's understand why both are needed.

### Why Filter by Node?

Our agent graph has multiple nodes that call the LLM:

```
User message → [router] → [tools] → [llm] → Response
                  ↑                     ↑
            Calls LLM to          Calls LLM to
            classify intent       generate answer
```

The **router** node calls the LLM to decide: "Is this a general_qa question or an incident_triage?" The LLM's response might be just the text `"general_qa"`. Without node filtering, that would appear in the user's chat as the first word of the response!

By checking `node in ("router", "gather_symptoms", "search_docs")`, we skip tokens from non-answer nodes and only stream the actual response meant for the user.

```python
# Without filtering (BAD):
# User sees: "general_qa Weaviate is a vector database that..."
#             ↑ leaked router output!

# With filtering (GOOD):
# User sees: "Weaviate is a vector database that..."
```

### Why Filter Tool Call Chunks?

When the LLM decides it needs to call a tool, it doesn't output human-readable text. Instead, it outputs **JSON** — the tool name and arguments:

```json
{"name": "rag_search", "args": {"query": "Weaviate vector database"}}
```

This JSON comes through as token events too. Without the `chunk.tool_call_chunks` filter, the user would see raw JSON in their response:

```python
# Without filtering (BAD):
# User sees: '{"name": "rag_search", "args": {"query"...'

# With filtering (GOOD):
# User sees: (nothing — tool call happens silently in the background)
```

The check `not chunk.tool_call_chunks` catches these and skips them.

### Handling Tool Events

```python
if kind == "on_chain_start" and node == "tools":
    # A tool is about to execute
    yield f"data: {json.dumps({'event': 'tool_start', 'node': 'tools'})}\n\n"

if kind == "on_chain_end" and node == "tools":
    # A tool just finished executing
    output = event.get("data", {}).get("output", {})
    
    # Extract tool name from the output
    tool_name = "unknown"
    tool_calls_log = output.get("tool_calls_log", [])
    if tool_calls_log:
        tool_name = tool_calls_log[-1].get("tool", tool_name)
    
    yield f"data: {json.dumps({'event': 'tool_end', 'tool': tool_name})}\n\n"
    
    # Extract sources from RAG results (see Source Citation Pipeline below)
    sources = extract_sources(tool_calls_log)
    if sources:
        yield f"data: {json.dumps({'event': 'sources', 'sources': sources})}\n\n"
```

This gives the frontend enough information to show: "🔧 Calling rag_search..." while the tool runs, then switch to streaming the answer.

### SSE Event Types Summary

Here's every event type our streaming endpoint emits:

| SSE Event | Payload | When |
|---|---|---|
| `tool_start` | `{"event": "tool_start", "node": "tools"}` | Agent begins calling a tool |
| `tool_end` | `{"event": "tool_end", "tool": "rag_search"}` | Tool finished executing |
| `token` | `{"event": "token", "content": "Hello"}` | One token from the LLM response |
| `sources` | `{"event": "sources", "sources": [...]}` | RAG results with scores |
| `complete` | `{"event": "complete", "latency_ms": 2340}` | Response fully generated |

---

## Frontend Implementation: Streamlit Streaming

The frontend (`frontend/app.py`) reads the SSE stream and updates the UI in real-time.

### Opening the Stream

```python
import requests
import json

def stream_response(message: str):
    """Send a message and stream the response."""
    url = f"{BACKEND_URL}/chat/stream"
    
    try:
        response = requests.post(
            url,
            json={"message": message},
            stream=True,          # KEY: tells requests to not wait for full response
            timeout=60,
        )
        response.raise_for_status()
        
        # Process each SSE line as it arrives
        for line in response.iter_lines(decode_unicode=True):
            if line and line.startswith("data: "):
                data = json.loads(line[6:])  # Strip "data: " prefix
                yield data                    # Yield parsed event to caller
                
    except requests.RequestException:
        # Fallback to non-streaming endpoint
        yield from fallback_chat(message)
```

**Key detail:** `stream=True` tells the `requests` library not to download the entire response before returning. Instead, it gives us access to `iter_lines()` which reads one line at a time as they arrive from the server.

### Rendering Tokens in Real-Time

```python
# In the Streamlit chat handler:

full_response = ""
sources = []
placeholder = st.empty()  # Creates a placeholder we can update

for event in stream_response(user_message):
    event_type = event.get("event", "")
    
    if event_type == "token":
        # Append the new token and update the display
        full_response += event["content"]
        placeholder.markdown(full_response + "▌")  # ▌ = cursor effect
    
    elif event_type == "tool_start":
        st.status("🔧 Calling rag_search...", state="running")
    
    elif event_type == "sources":
        sources = event["sources"]
    
    elif event_type == "complete":
        # Remove cursor, show final response
        placeholder.markdown(full_response)
        
        # Show timing
        latency = event.get("latency_ms", 0)
        st.caption(f"⏱️ Generated in {latency / 1000:.1f}s")

# After streaming completes, show sources
if sources:
    with st.expander("📚 Sources"):
        for src in sources:
            title = src.get("title", "Unknown")
            score = src.get("score", 0)
            source_type = src.get("source_type", "document")
            st.markdown(f"- **{title}** ({source_type}) — {score:.0%} confidence")
```

**The cursor trick:** Notice `full_response + "▌"` — that block character (`▌`) at the end creates a blinking cursor effect, just like ChatGPT. When the response is complete, we re-render without the cursor. It's a small detail that makes the UX feel polished.

**The `st.empty()` pattern:** Streamlit's `st.empty()` creates a container that can be updated in place. Each time we call `placeholder.markdown(...)`, it replaces the previous content rather than adding a new element. This is how we "append" tokens to the response without the page growing with duplicate content.

### Fallback to Non-Streaming

If the streaming endpoint fails (network issue, server error), we fall back gracefully:

```python
def fallback_chat(message: str):
    """Non-streaming fallback — send message, get complete response."""
    try:
        response = requests.post(
            f"{BACKEND_URL}/chat",
            json={"message": message},
            timeout=60,
        )
        data = response.json()
        # Yield the full response as a single "token" event
        yield {"event": "token", "content": data.get("response", "Error")}
        yield {"event": "complete", "latency_ms": 0}
    except Exception as e:
        yield {"event": "token", "content": f"Error: {str(e)}"}
        yield {"event": "complete", "latency_ms": 0}
```

The fallback yields the same event format, so the rendering code doesn't need to know whether it's streaming or not. This is a nice pattern: **make the fallback speak the same interface as the primary path.**

---

## Source Citation Pipeline

Sources don't magically appear — they flow through a specific pipeline from the RAG tool to the user's screen. Here's the full journey:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Source Citation Pipeline                      │
│                                                                 │
│  1. RAG tool searches Weaviate                                  │
│     └── Returns: [{title, source_type, score, content}, ...]    │
│                                                                 │
│  2. tool_node in graph.py captures results                      │
│     └── Stores in state["tool_calls_log"]:                      │
│         {"tool": "rag_search", "rag_results": [...]}            │
│                                                                 │
│  3. Streaming endpoint catches on_chain_end for node="tools"    │
│     └── Reads tool_calls_log from event output                  │
│     └── Deduplicates by title (same doc may appear twice)       │
│     └── Emits SSE: {"event": "sources", "sources": [...]}      │
│                                                                 │
│  4. Frontend receives sources event                             │
│     └── Stores sources list                                     │
│     └── After response completes, renders expandable section    │
│     └── Shows: title, source_type, confidence percentage        │
└─────────────────────────────────────────────────────────────────┘
```

### Step 2 in Detail: Capturing RAG Results

In `agent/graph.py`, the `execute_tool()` function returns a tuple when RAG results are available:

```python
async def execute_tool(name: str, args: dict) -> tuple:
    """Execute a tool and return (text_result, rag_results)."""
    if name == "rag_search":
        results = await rag_search(args["query"])
        text = format_results_as_text(results)
        # Return both the text (for the LLM) and raw results (for citations)
        return text, results
    else:
        result = await other_tool(name, args)
        return result, None
```

The `tool_node` then stores these in `tool_calls_log`:

```python
async def tool_node(state: AgentState) -> dict:
    tool_calls_log = []
    for tool_call in last_message.tool_calls:
        text, rag_results = await execute_tool(tool_call["name"], tool_call["args"])
        
        log_entry = {"tool": tool_call["name"]}
        if rag_results:
            log_entry["rag_results"] = rag_results
        tool_calls_log.append(log_entry)
    
    return {
        "messages": [tool_response_messages],
        "tool_calls_log": tool_calls_log,  # ← This is how sources reach the stream
    }
```

### Step 3 in Detail: Deduplication

The same document might appear in multiple RAG results (if the user's question matches several chunks from the same document). We deduplicate by title:

```python
def extract_sources(tool_calls_log: list) -> list:
    """Extract and deduplicate sources from tool call results."""
    seen_titles = set()
    sources = []
    
    for log_entry in tool_calls_log:
        for result in log_entry.get("rag_results", []):
            title = result.get("title", "")
            if title and title not in seen_titles:
                seen_titles.add(title)
                sources.append({
                    "title": title,
                    "source_type": result.get("source_type", "document"),
                    "score": result.get("score", 0.0),
                })
    
    return sources
```

---

## Testing the Streaming

### Watch Tokens Arrive in Real-Time

```bash
# The -N flag disables buffering so you see tokens immediately
curl -s -N -X POST http://localhost:8001/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message":"What is Weaviate used for?"}'
```

You should see individual `data:` lines appearing one by one, not all at once:

```
data: {"event": "tool_start", "node": "tools"}
data: {"event": "tool_end", "tool": "rag_search"}
data: {"event": "sources", "sources": [{"title": "Weaviate Overview", "score": 0.92}]}
data: {"event": "token", "content": "Weaviate"}
data: {"event": "token", "content": " is"}
data: {"event": "token", "content": " a"}
data: {"event": "token", "content": " vector"}
data: {"event": "token", "content": " database"}
...
data: {"event": "complete", "latency_ms": 2340}
```

### Check for Tool Events and Sources

```bash
# Filter for just the structural events (skip individual tokens)
curl -s -N -X POST http://localhost:8001/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message":"How does EventBridge work?"}' | grep -E "(tool_|sources|complete)"
```

### Test the Non-Streaming Fallback

```bash
# The original /chat endpoint still works as a fallback
curl -s -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"What is Weaviate?"}' | python3 -m json.tool
```

This should return a complete JSON response (not streamed), confirming the fallback path works.

---

## Key Takeaways

1. **SSE is simpler than WebSockets** for one-way streaming — it's just `data: {...}\n\n` lines over HTTP, with built-in browser reconnection
2. **LangGraph's `astream_events`** gives fine-grained control over what to stream — you can watch every node, every tool call, every token
3. **Node-level filtering is essential** — without it, router classification tokens ("general_qa") and intermediate outputs leak into the user's response
4. **Tool call chunk filtering is also essential** — without it, raw JSON tool arguments appear as text in the response
5. **Always handle both `str` and `list` content** from Bedrock Converse — this affects the router, triage workflow, and streaming handler
6. **Source extraction requires capturing metadata in the tool execution pipeline** — results flow from RAG tool → tool_calls_log → SSE event → frontend
7. **Fallback patterns (streaming → non-streaming)** make the UX robust — if streaming breaks, the app still works

---

## What Changed (Files Modified)

| File | What Changed |
|---|---|
| `agent-backend/main.py` | New `/chat/stream` endpoint with SSE, source extraction from `tool_calls_log`, latency tracking |
| `agent-backend/agent/graph.py` | `execute_tool()` returns `(text, rag_results)` tuple; content block handling added to router node |
| `agent-backend/agent/prompts.py` | Added source citation instruction to system prompt |
| `agent-backend/agent/workflows/incident_triage.py` | Content block handling in `_call_llm()` for Bedrock Converse |
| `frontend/app.py` | Full rewrite: streaming token display, expandable sources, timing badge, fallback to non-streaming |
| `frontend/requirements.txt` | Added `sseclient-py` dependency |

---

## What's Next?

You now have a complete, production-quality conversational AI agent:

- **Step 1:** Infrastructure (Docker, databases)
- **Step 2:** Data ingestion (loading knowledge into Weaviate)
- **Step 3:** RAG search (semantic retrieval)
- **Step 4:** Basic agent (single-tool ReAct)
- **Step 5:** Multi-tool agent (4 tools, autonomous selection)
- **Step 6:** Eligibility workflow (structured branching)
- **Step 7:** Production patterns (reliability, observability, logging)
- **Step 8:** Streaming UX (live responses, citations, timing) ← **You are here**

The agent now handles the full lifecycle: retrieving knowledge, reasoning about it, executing structured workflows, and presenting results in a polished, real-time streaming interface. From here, you could add conversation memory, multi-user sessions, or deploy to production infrastructure.
