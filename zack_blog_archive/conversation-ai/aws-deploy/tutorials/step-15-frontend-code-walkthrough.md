# Step 15: Frontend Code Walkthrough — Streamlit Chat UI

> **Audience:** Beginners who have never used Streamlit or built a web UI in Python.
> **Goal:** Understand every line of the chat frontend, how it streams responses, manages sessions, and runs inside Docker.

---

## 15.1 What is Streamlit?

Streamlit is a **Python-only web framework**. You write regular Python — no HTML, no CSS, no JavaScript — and Streamlit turns it into a fully interactive web application in your browser.

### Why Streamlit?

| Traditional Web App | Streamlit |
|---|---|
| HTML templates + CSS + JavaScript + backend | Just Python |
| Hours to build a simple form | Minutes |
| Learn multiple languages | Know Python? You're done |
| Complex state management | `st.session_state` handles it |

Streamlit was designed for **data apps and prototypes**. It's the fastest way to put a Python script behind a web interface. Companies use it for internal dashboards, ML demos, and — like we're doing here — chat UIs.

### The Rerun Model (This Is Important!)

Streamlit has a **unique execution model** that trips up every beginner, so let's get this right:

> **Every time the user interacts with the app (clicks a button, types in an input, etc.), Streamlit reruns the ENTIRE Python script from top to bottom.**

That means:
- Line 1 runs. Then line 2. Then line 3. All the way to the end.
- User clicks a button.
- Line 1 runs again. Then line 2. Then line 3. All the way to the end *again*.

This is completely different from traditional web frameworks where you write event handlers for specific actions. In Streamlit, the whole script is the event handler.

### `st.session_state` — Memory That Survives Reruns

Since the script reruns every time, any regular Python variable gets reset:

```python
counter = 0          # This resets to 0 on EVERY rerun!
counter += 1         # This will always be 1. Always.
```

To persist data across reruns, you use `st.session_state`:

```python
if "counter" not in st.session_state:
    st.session_state.counter = 0       # Only runs the FIRST time
st.session_state.counter += 1          # Now this actually increments!
```

Think of `st.session_state` as a dictionary that lives in the browser tab's memory. It persists as long as the tab is open.

---

## 15.2 The Complete Frontend Code (app.py)

Here is the exact code powering our chat frontend. Read through it once, then we'll break it down piece by piece.

```python
"""Streamlit frontend for the Platform Health Insight Assistant (AWS).

Features:
- Streaming responses (tokens appear as generated)
- Source citations with confidence scores and clickable links
- Response timing display
- Session management (list, switch, load history)
"""

import os
import time
import uuid
import json

import requests
import streamlit as st

AGENT_BACKEND_URL = os.getenv("AGENT_BACKEND_URL", "http://localhost:8001")

st.set_page_config(
    page_title="Platform Health Insight Assistant",
    page_icon="🔧",
    layout="centered",
)

st.title("🔧 Platform Health Insight Assistant")
st.caption("AI-powered assistant for infrastructure troubleshooting and architecture Q&A")

# Session state
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar — Session Management
with st.sidebar:
    st.markdown("### 💬 Sessions")

    if st.button("➕ New Conversation"):
        st.session_state.conversation_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()

    # Load sessions list from backend
    try:
        sessions_resp = requests.get(f"{AGENT_BACKEND_URL}/sessions", timeout=5)
        if sessions_resp.ok:
            sessions = sessions_resp.json().get("sessions", [])
            for session in sessions[:20]:  # Show last 20
                sid = session.get("session_id", "")
                title = session.get("title", "Untitled")
                count = session.get("message_count", 0)
                is_active = sid == st.session_state.conversation_id
                label = f"{'▶ ' if is_active else ''}{title} ({count} msgs)"
                if st.button(label, key=f"session_{sid}", disabled=is_active):
                    # Load this session
                    st.session_state.conversation_id = sid
                    hist_resp = requests.get(
                        f"{AGENT_BACKEND_URL}/sessions/{sid}/history", timeout=10
                    )
                    if hist_resp.ok:
                        hist_messages = hist_resp.json().get("messages", [])
                        st.session_state.messages = [
                            {
                                "role": m["role"],
                                "content": m["content"],
                                "metadata": m.get("metadata", {}),
                            }
                            for m in hist_messages
                        ]
                    st.rerun()
    except requests.exceptions.ConnectionError:
        st.caption("⚠️ Backend not connected")

    st.markdown("---")
    st.markdown("### Workflows")
    st.markdown("""
    - 🔍 Architecture Q&A
    - 🚨 Incident Triage
    - 📋 Change Impact Analysis
    - 🎓 Onboarding Guide
    """)
    st.markdown("---")
    st.markdown("### How to test")
    st.markdown("""
    Try these:
    - *"How does EventBridge work?"*
    - *"Lambda is timing out"*
    - *"How to set up RAG on EKS?"*
    - *"CRITICAL: Bedrock 500 errors"*
    """)

# Display conversation history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("metadata"):
            meta = msg["metadata"]
            cols = st.columns(3)
            if meta.get("latency_ms"):
                cols[0].caption(f"⏱️ {meta['latency_ms']/1000:.1f}s")
            if meta.get("tool_count"):
                cols[1].caption(f"🔧 {meta['tool_count']} tool(s)")
            if meta.get("source_count"):
                cols[2].caption(f"📚 {meta['source_count']} source(s)")

# Chat input
if prompt := st.chat_input("Ask about platform architecture, report an incident..."):
    # Show user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Stream response from agent
    with st.chat_message("assistant"):
        start_time = time.time()

        # Try streaming first, fall back to non-streaming
        try:
            response = requests.post(
                f"{AGENT_BACKEND_URL}/chat/stream",
                json={
                    "message": prompt,
                    "conversation_id": st.session_state.conversation_id,
                },
                stream=True,
                timeout=120,
            )
            response.raise_for_status()

            # Stream tokens into the UI
            placeholder = st.empty()
            full_response = ""
            tool_events = []
            sources = []
            tool_status = st.status("Processing...", expanded=True)
            server_latency_ms = 0

            for line in response.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data: "):
                    continue
                try:
                    data = json.loads(line[6:])  # Strip "data: " prefix
                except json.JSONDecodeError:
                    continue

                step = data.get("step", "")

                if step == "token":
                    content = data.get("content", "")
                    full_response += content
                    placeholder.markdown(full_response + "▌")

                elif step == "tool_start":
                    tool_name = data.get("tool", "unknown")
                    tool_events.append(tool_name)
                    tool_status.write(f"🔧 Calling **{tool_name}**...")

                elif step == "tool_end":
                    tool_name = data.get("tool", "unknown")
                    tool_status.write(f"✅ **{tool_name}** complete")

                elif step == "sources":
                    sources = data.get("sources", [])

                elif step == "complete":
                    server_latency_ms = data.get("latency_ms", 0)
                    break

            # Remove cursor and show final response
            placeholder.markdown(full_response)
            tool_status.update(label="Complete", state="complete", expanded=False)

            # Show timing and metadata
            elapsed_ms = server_latency_ms if server_latency_ms else int((time.time() - start_time) * 1000)
            cols = st.columns(3)
            cols[0].caption(f"⏱️ {elapsed_ms/1000:.1f}s")
            cols[1].caption(f"🔧 {len(tool_events)} tool(s)")
            cols[2].caption(f"📚 {len(sources)} source(s)")

            # Show sources if any
            if sources:
                with st.expander("📚 Sources", expanded=False):
                    for s in sources:
                        score_pct = int(s.get("score", 0) * 100)
                        uri = s.get("source_uri", "")
                        title = s.get("title", "Unknown")
                        if uri:
                            st.markdown(f"- [{title}]({uri}) ({s.get('source_type', '')}) — {score_pct}% match")
                        else:
                            st.markdown(f"- **{title}** ({s.get('source_type', '')}) — {score_pct}% match")

            st.session_state.messages.append({
                "role": "assistant",
                "content": full_response,
                "metadata": {
                    "latency_ms": elapsed_ms,
                    "tool_count": len(tool_events),
                    "source_count": len(sources),
                },
            })

        except requests.exceptions.ConnectionError:
            st.error("❌ Cannot connect to agent backend. Is it running on port 8001?")
        except Exception as e:
            # Fall back to non-streaming
            try:
                response = requests.post(
                    f"{AGENT_BACKEND_URL}/chat",
                    json={
                        "message": prompt,
                        "conversation_id": st.session_state.conversation_id,
                    },
                    timeout=120,
                )
                response.raise_for_status()
                data = response.json()

                elapsed_ms = data.get("latency_ms", int((time.time() - start_time) * 1000))
                st.markdown(data["response"])

                cols = st.columns(3)
                cols[0].caption(f"⏱️ {elapsed_ms/1000:.1f}s")
                cols[1].caption(f"🔧 {len(data.get('tool_calls', []))} tool(s)")
                cols[2].caption(f"📚 {len(data.get('sources', []))} source(s)")

                if data.get("sources"):
                    with st.expander("📚 Sources", expanded=False):
                        for s in data["sources"]:
                            score_pct = int(s.get("score", 0) * 100)
                            uri = s.get("source_uri", "")
                            title = s.get("title", "Unknown")
                            if uri:
                                st.markdown(f"- [{title}]({uri}) ({s.get('source_type', '')}) — {score_pct}% match")
                            else:
                                st.markdown(f"- **{title}** ({s.get('source_type', '')}) — {score_pct}% match")

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": data["response"],
                    "metadata": {
                        "latency_ms": elapsed_ms,
                        "tool_count": len(data.get("tool_calls", [])),
                        "source_count": len(data.get("sources", [])),
                    },
                })
            except Exception as e2:
                st.error(f"Error: {e2}")
```

That's 249 lines. Let's break every section down.

---

### Page Configuration

```python
st.set_page_config(
    page_title="Platform Health Insight Assistant",
    page_icon="🔧",
    layout="centered",
)
```

This **must** be the first Streamlit command in the script (after imports). It configures:

| Parameter | What It Does |
|---|---|
| `page_title` | Sets the browser tab title (what you see in the tab bar) |
| `page_icon` | Sets the favicon — the tiny icon in the browser tab. Emojis work! |
| `layout="centered"` | Content is centered in a ~700px column. The alternative is `"wide"` which uses the full browser width. |

Then we set the visible page title and subtitle:

```python
st.title("🔧 Platform Health Insight Assistant")
st.caption("AI-powered assistant for infrastructure troubleshooting and architecture Q&A")
```

`st.title()` renders as a large `<h1>` heading. `st.caption()` renders as small, gray secondary text underneath.

---

### Session State Initialization

```python
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []
```

Remember: the script reruns on every interaction. These `if` checks ensure we only initialize values **once** — when the user first opens the page.

| State Variable | Purpose | Initial Value |
|---|---|---|
| `conversation_id` | Unique ID for this conversation, sent to the backend so it knows which thread we're in | A random UUID like `"a3f8c1d2-..."` |
| `messages` | Chat history for the current session. Each entry has `role` ("user" or "assistant"), `content` (the text), and optional `metadata` | Empty list `[]` |

**Why UUID?** `uuid.uuid4()` generates a random 128-bit identifier. It's practically guaranteed to be unique — the chance of collision is astronomically small. This lets us create new conversations without asking the backend for an ID first.

---

### Session Sidebar

The sidebar is the panel on the left side of the Streamlit app. Everything inside the `with st.sidebar:` block appears there.

```python
with st.sidebar:
    st.markdown("### 💬 Sessions")
```

#### The "New Conversation" Button

```python
if st.button("➕ New Conversation"):
    st.session_state.conversation_id = str(uuid.uuid4())
    st.session_state.messages = []
    st.rerun()
```

When clicked:
1. Generate a fresh UUID → new conversation
2. Clear the message history
3. `st.rerun()` → force the script to rerun immediately so the UI updates

#### Loading Past Sessions from the Backend

```python
try:
    sessions_resp = requests.get(f"{AGENT_BACKEND_URL}/sessions", timeout=5)
    if sessions_resp.ok:
        sessions = sessions_resp.json().get("sessions", [])
        for session in sessions[:20]:  # Show last 20
```

This makes an HTTP GET request to the backend's `/sessions` endpoint. The backend returns a JSON list of past conversations. We show the most recent 20.

For each session, we create a button in the sidebar:

```python
sid = session.get("session_id", "")
title = session.get("title", "Untitled")
count = session.get("message_count", 0)
is_active = sid == st.session_state.conversation_id
label = f"{'▶ ' if is_active else ''}{title} ({count} msgs)"
if st.button(label, key=f"session_{sid}", disabled=is_active):
```

The active session gets a `▶` prefix and is disabled (you can't click it — you're already in it). Each button has a unique `key` to prevent Streamlit from confusing them.

When you click a session button:

```python
st.session_state.conversation_id = sid
hist_resp = requests.get(
    f"{AGENT_BACKEND_URL}/sessions/{sid}/history", timeout=10
)
if hist_resp.ok:
    hist_messages = hist_resp.json().get("messages", [])
    st.session_state.messages = [
        {
            "role": m["role"],
            "content": m["content"],
            "metadata": m.get("metadata", {}),
        }
        for m in hist_messages
    ]
st.rerun()
```

1. Set the `conversation_id` to the selected session
2. Fetch the full message history from `GET /sessions/{sid}/history`
3. Parse each message into our local format
4. `st.rerun()` to redraw the page with the loaded history

#### Connection Error Handling

```python
except requests.exceptions.ConnectionError:
    st.caption("⚠️ Backend not connected")
```

If the backend isn't running, we show a small warning instead of crashing the entire app. This is graceful degradation — the chat still loads, you just can't see past sessions.

#### Sidebar Help Content

The rest of the sidebar shows static content — workflow descriptions and example prompts:

```python
st.markdown("### Workflows")
st.markdown("""
- 🔍 Architecture Q&A
- 🚨 Incident Triage
...
""")
```

This is purely informational. It tells users what the assistant can do and gives them example questions to try.

---

### Chat Display

```python
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
```

This loops through every message in the conversation and renders it as a chat bubble.

- `st.chat_message("user")` → shows a **user avatar** on the left with a white bubble
- `st.chat_message("assistant")` → shows a **bot avatar** on the left with a gray bubble

The `with` block means everything inside it appears within that chat bubble.

#### Metadata Display

```python
if msg.get("metadata"):
    meta = msg["metadata"]
    cols = st.columns(3)
    if meta.get("latency_ms"):
        cols[0].caption(f"⏱️ {meta['latency_ms']/1000:.1f}s")
    if meta.get("tool_count"):
        cols[1].caption(f"🔧 {meta['tool_count']} tool(s)")
    if meta.get("source_count"):
        cols[2].caption(f"📚 {meta['source_count']} source(s)")
```

Below each assistant message, we show three small metrics in a three-column layout:
- **Response time** — how long it took to generate
- **Tool count** — how many tools the agent called (RAG search, etc.)
- **Source count** — how many knowledge base documents were cited

`st.columns(3)` creates three equal-width columns. `cols[0]` is the first column, etc.

---

### User Input

```python
if prompt := st.chat_input("Ask about platform architecture, report an incident..."):
```

This is Python's **walrus operator** (`:=`). It does two things at once:
1. Renders a text input at the bottom of the page
2. If the user typed something and hit Enter, assigns it to `prompt` and enters the `if` block

`st.chat_input()` always renders as a sticky text field at the very bottom of the page — like the input box in ChatGPT.

When the user sends a message:

```python
st.session_state.messages.append({"role": "user", "content": prompt})
with st.chat_message("user"):
    st.markdown(prompt)
```

1. Append the user's message to session state (so it persists across reruns)
2. Immediately display it as a chat bubble

---

### Streaming Response

This is the most complex part of the app. Let's walk through it carefully.

```python
with st.chat_message("assistant"):
    start_time = time.time()
```

We open an assistant chat bubble and start a timer.

#### Making the Streaming Request

```python
response = requests.post(
    f"{AGENT_BACKEND_URL}/chat/stream",
    json={
        "message": prompt,
        "conversation_id": st.session_state.conversation_id,
    },
    stream=True,
    timeout=120,
)
response.raise_for_status()
```

Key details:
- **`stream=True`** — this is critical! It tells `requests` not to download the entire response at once. Instead, we get data as it arrives from the server.
- **`timeout=120`** — wait up to 2 minutes for the backend to respond. AI responses can take a while.
- **`raise_for_status()`** — if the backend returns a 4xx or 5xx error, throw an exception.

#### Setting Up the Display

```python
placeholder = st.empty()
full_response = ""
tool_events = []
sources = []
tool_status = st.status("Processing...", expanded=True)
server_latency_ms = 0
```

| Variable | Purpose |
|---|---|
| `placeholder` | An empty Streamlit element we'll repeatedly update with the growing response text |
| `full_response` | Accumulates all tokens into the complete answer |
| `tool_events` | List of tool names that were called |
| `sources` | Knowledge base sources for citation display |
| `tool_status` | A collapsible status widget showing "Processing..." |
| `server_latency_ms` | Backend-reported response time |

#### Processing the Stream

```python
for line in response.iter_lines(decode_unicode=True):
    if not line or not line.startswith("data: "):
        continue
    try:
        data = json.loads(line[6:])  # Strip "data: " prefix
    except json.JSONDecodeError:
        continue
```

`response.iter_lines()` gives us one line at a time as they arrive from the server. We skip empty lines and lines that aren't SSE data events. Then we parse the JSON payload (everything after `"data: "`).

#### Handling Each Event Type

**Token events** — the actual words of the response:
```python
if step == "token":
    content = data.get("content", "")
    full_response += content
    placeholder.markdown(full_response + "▌")
```
Each token (usually a word or word fragment) is appended to `full_response`. The `placeholder.markdown()` call **replaces** the previous content of the placeholder with the updated text. The `"▌"` character is a blinking cursor effect — it makes it look like the AI is typing.

**Tool start events** — the agent is calling a tool:
```python
elif step == "tool_start":
    tool_name = data.get("tool", "unknown")
    tool_events.append(tool_name)
    tool_status.write(f"🔧 Calling **{tool_name}**...")
```

**Tool end events** — a tool call finished:
```python
elif step == "tool_end":
    tool_name = data.get("tool", "unknown")
    tool_status.write(f"✅ **{tool_name}** complete")
```

**Source events** — knowledge base documents used:
```python
elif step == "sources":
    sources = data.get("sources", [])
```

**Complete event** — response is done:
```python
elif step == "complete":
    server_latency_ms = data.get("latency_ms", 0)
    break
```

#### Finalizing the Display

```python
placeholder.markdown(full_response)
tool_status.update(label="Complete", state="complete", expanded=False)
```

Remove the cursor character and collapse the status widget.

#### Showing Metadata and Sources

```python
elapsed_ms = server_latency_ms if server_latency_ms else int((time.time() - start_time) * 1000)
cols = st.columns(3)
cols[0].caption(f"⏱️ {elapsed_ms/1000:.1f}s")
cols[1].caption(f"🔧 {len(tool_events)} tool(s)")
cols[2].caption(f"📚 {len(sources)} source(s)")
```

We prefer the server-reported latency (`server_latency_ms`). If the server didn't send it, we fall back to our own client-side timer.

Sources get an expandable section:

```python
if sources:
    with st.expander("📚 Sources", expanded=False):
        for s in sources:
            score_pct = int(s.get("score", 0) * 100)
            uri = s.get("source_uri", "")
            title = s.get("title", "Unknown")
            if uri:
                st.markdown(f"- [{title}]({uri}) ({s.get('source_type', '')}) — {score_pct}% match")
            else:
                st.markdown(f"- **{title}** ({s.get('source_type', '')}) — {score_pct}% match")
```

Each source shows its title, type, and a confidence percentage. If a URI is available, the title becomes a clickable link.

#### Saving to Session State

```python
st.session_state.messages.append({
    "role": "assistant",
    "content": full_response,
    "metadata": {
        "latency_ms": elapsed_ms,
        "tool_count": len(tool_events),
        "source_count": len(sources),
    },
})
```

The assistant's response is saved so it persists when the script reruns.

---

### Error Handling

The app has a two-tier error handling strategy:

**Tier 1: Connection errors**
```python
except requests.exceptions.ConnectionError:
    st.error("❌ Cannot connect to agent backend. Is it running on port 8001?")
```
If the backend is completely unreachable, show a clear error with a hint about what to check.

**Tier 2: Streaming fails → fall back to non-streaming**
```python
except Exception as e:
    try:
        response = requests.post(
            f"{AGENT_BACKEND_URL}/chat",       # Note: /chat not /chat/stream
            json={ ... },
            timeout=120,
        )
```
If the streaming endpoint fails for any other reason (server error, malformed SSE, etc.), the app automatically retries with the non-streaming `/chat` endpoint. This returns the complete response as a single JSON object — no word-by-word animation, but the user still gets their answer.

**Tier 3: Everything fails**
```python
except Exception as e2:
    st.error(f"Error: {e2}")
```
Last resort — show the raw error message.

---

## 15.3 SSE Streaming in Detail

SSE stands for **Server-Sent Events**. It's a simple protocol built on top of HTTP where the server can push data to the client over a single long-lived connection.

### The Wire Format

Here's what the raw HTTP response from `/chat/stream` looks like:

```
HTTP/1.1 200 OK
Content-Type: text/event-stream

data: {"step": "tool_start", "tool": "rag_search"}

data: {"step": "tool_end", "tool": "rag_search"}

data: {"step": "token", "content": "Based"}

data: {"step": "token", "content": " on"}

data: {"step": "token", "content": " the"}

data: {"step": "token", "content": " documentation"}

data: {"step": "token", "content": ","}

data: {"step": "token", "content": " Event"}

data: {"step": "token", "content": "Bridge"}

data: {"step": "token", "content": " is"}

data: {"step": "token", "content": "..."}

data: {"step": "sources", "sources": [{"title": "EventBridge Architecture", "source_type": "confluence", "score": 0.92, "source_uri": "https://..."}]}

data: {"step": "complete", "latency_ms": 5200}
```

Every line starts with `data: ` followed by a JSON object. Blank lines separate events. That's the entire protocol.

### How the Frontend Handles Each Event Type

| Event | JSON Shape | Frontend Action |
|---|---|---|
| `token` | `{"step": "token", "content": "Hello"}` | Append text to `full_response`, update the placeholder to show growing text with cursor |
| `tool_start` | `{"step": "tool_start", "tool": "rag_search"}` | Add tool name to `tool_events`, show "🔧 Calling **rag_search**..." in status widget |
| `tool_end` | `{"step": "tool_end", "tool": "rag_search"}` | Show "✅ **rag_search** complete" in status widget |
| `sources` | `{"step": "sources", "sources": [...]}` | Store array in `sources` variable for later display |
| `complete` | `{"step": "complete", "latency_ms": 5200}` | Record server timing, break out of the loop |

### Why SSE Instead of WebSockets?

SSE is **simpler**:
- One-way: server → client (which is all we need for streaming a response)
- Works over standard HTTP (no upgrade handshake)
- Automatically handles reconnection
- The `requests` library supports it natively with `stream=True`

WebSockets would be overkill — we only need the server to push tokens to the client, not bidirectional communication.

### The Typing Effect

```python
placeholder.markdown(full_response + "▌")
```

The `▌` (Unicode block character U+258C) appears at the end of the text while tokens are still arriving. This creates the "cursor blinking while AI types" effect you see in ChatGPT. When streaming finishes:

```python
placeholder.markdown(full_response)  # No cursor
```

The cursor disappears, signaling the response is complete.

---

## 15.4 Session Management

### How `conversation_id` Is Generated

```python
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = str(uuid.uuid4())
```

On first load, a UUID v4 is generated: `"a3f8c1d2-7e4b-4a9f-b5d1-8c3e2f1a0b9d"`. This ID is sent with every `/chat/stream` request so the backend can associate messages with the correct conversation thread.

### How Sessions Are Loaded from the Backend

```
GET /sessions → [{"session_id": "abc-123", "title": "EventBridge Q&A", "message_count": 4}, ...]
```

The sidebar fetches this list on every script rerun (every time the page refreshes). It shows the 20 most recent sessions as clickable buttons.

### How History Is Restored

When you click a past session:

```
GET /sessions/abc-123/history → {"messages": [{"role": "user", "content": "How does..."}, ...]}
```

The response contains all messages in chronological order. The frontend parses them into the `st.session_state.messages` format and calls `st.rerun()`. On the next rerun, the chat display loop renders all the loaded messages.

### How New Sessions Are Created

Clicking "➕ New Conversation":
1. Generates a new UUID
2. Clears the message list
3. Calls `st.rerun()`

The new session doesn't exist on the backend yet. It gets created implicitly when the user sends the first message — the backend sees a `conversation_id` it hasn't seen before and creates a new session record.

---

## 15.5 Docker Configuration

### Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1

# Run Streamlit
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.headless=true", "--server.address=0.0.0.0"]
```

Let's break down each section:

**Base image:**
```dockerfile
FROM python:3.12-slim
```
`python:3.12-slim` is a minimal Debian image with Python 3.12. The `slim` variant excludes development tools, keeping the image small (~150MB vs ~900MB for the full image).

**Working directory:**
```dockerfile
WORKDIR /app
```
All subsequent commands run inside `/app` in the container.

**Dependencies first (for Docker cache):**
```dockerfile
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
```
We copy `requirements.txt` separately and install before copying the app code. Docker caches each layer — if `requirements.txt` hasn't changed, Docker reuses the cached layer and skips `pip install`. This makes rebuilds much faster during development.

`--no-cache-dir` tells pip not to store downloaded packages, keeping the image smaller.

**App code:**
```dockerfile
COPY . .
```
Copy everything in the `frontend/` directory into `/app` in the container.

**Port declaration:**
```dockerfile
EXPOSE 8501
```
Documents that the container listens on port 8501. This doesn't actually publish the port — it's metadata for orchestrators like ECS.

**Health check:**
```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1
```
ECS uses this to determine if the container is healthy. Every 30 seconds, it hits Streamlit's built-in health endpoint. If it fails 3 times in a row, ECS considers the container unhealthy and replaces it.

| Parameter | Meaning |
|---|---|
| `--interval=30s` | Check every 30 seconds |
| `--timeout=5s` | Each check must respond within 5 seconds |
| `--start-period=10s` | Wait 10 seconds after startup before checking (gives the app time to initialize) |
| `--retries=3` | Container is "unhealthy" after 3 consecutive failures |

**Startup command:**
```dockerfile
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.headless=true", "--server.address=0.0.0.0"]
```

| Flag | Why It's Needed |
|---|---|
| `--server.port=8501` | Streamlit's default port. Explicit here for clarity. |
| `--server.headless=true` | Prevents Streamlit from trying to open a browser window. There's no browser inside a Docker container! |
| `--server.address=0.0.0.0` | **Critical.** By default, Streamlit listens on `127.0.0.1` (localhost). Inside a container, that means only processes *inside the container* can reach it. `0.0.0.0` means "listen on all network interfaces" — which allows traffic from outside the container (the host, ALB, etc.) to reach Streamlit. |

### requirements.txt

```
streamlit>=1.40.0
requests>=2.32.0
```

Just two dependencies:
- **streamlit** — the web framework
- **requests** — HTTP client for calling the backend API

That's it. The entire frontend has only two Python dependencies.

---

## 15.6 How Frontend Connects to Backend

The backend URL is configured via an environment variable:

```python
AGENT_BACKEND_URL = os.getenv("AGENT_BACKEND_URL", "http://localhost:8001")
```

### Locally (Development)

```bash
export AGENT_BACKEND_URL=http://localhost:8001
streamlit run app.py
```

Both frontend and backend run on your machine. The backend is at `localhost:8001`.

### In ECS (Production)

```bash
AGENT_BACKEND_URL=http://agent-backend.platform-health.local:8001
```

In AWS ECS, containers can't use `localhost` to talk to each other — each container has its own network namespace. Instead, we use **AWS Cloud Map** for service discovery.

Cloud Map registers each service with a DNS name:
```
agent-backend.platform-health.local → 10.0.1.47 (private IP of the backend container)
```

When the frontend makes a request to `http://agent-backend.platform-health.local:8001/chat/stream`, the DNS resolver inside the VPC translates that hostname to the backend container's private IP address. The request travels over the private subnet — never touching the public internet.

### All API Endpoints Used

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/sessions` | List all past conversation sessions |
| `GET` | `/sessions/{id}/history` | Load message history for a specific session |
| `POST` | `/chat/stream` | Send a message and receive a streaming SSE response |
| `POST` | `/chat` | Fallback: send a message and receive a complete JSON response |

---

## 15.7 The User Experience Flow

Let's walk through the complete experience step by step, with ASCII mockups of what the user sees at each stage.

### Step 1: Open the App

The user navigates to the ALB URL (e.g., `http://platform-health-alb-123.us-east-1.elb.amazonaws.com`).

```
┌─────────────────────────────────────────────────────────────────┐
│ 🔧 Platform Health Insight Assistant                            │
│ AI-powered assistant for infrastructure troubleshooting         │
│                                                                 │
│ ┌─────────────┐                                                 │
│ │ 💬 Sessions │                                                 │
│ │             │                                                 │
│ │ [➕ New     │       (empty chat area)                         │
│ │  Conversa-  │                                                 │
│ │  tion]      │                                                 │
│ │             │                                                 │
│ │ EventBridge │                                                 │
│ │ Q&A (4 msgs)│                                                 │
│ │             │                                                 │
│ │ Lambda      │                                                 │
│ │ Debug (2    │                                                 │
│ │ msgs)       │                                                 │
│ │             │                                                 │
│ │ ─────────── │                                                 │
│ │ Workflows   │                                                 │
│ │ 🔍 Arch Q&A │                                                 │
│ │ 🚨 Incident │                                                 │
│ │ 📋 Change   │                                                 │
│ │ 🎓 Onboard  │                                                 │
│ └─────────────┘                                                 │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Ask about platform architecture, report an incident...      │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Step 2: User Types a Question

The user types "How does EventBridge work in our architecture?" and presses Enter.

```
┌─────────────────────────────────────────────────────────────────┐
│ 🔧 Platform Health Insight Assistant                            │
│                                                                 │
│   👤 How does EventBridge work in our architecture?             │
│                                                                 │
│   🤖 ┌──────────────────────────────────────────────────────┐  │
│      │ ▌                                                     │  │
│      └──────────────────────────────────────────────────────┘  │
│      ┌─ Processing... ──────────────────────────────────────┐  │
│      │ 🔧 Calling **rag_search**...                         │  │
│      └──────────────────────────────────────────────────────┘  │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Ask about platform architecture, report an incident...      │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

The cursor `▌` blinks while the backend searches the knowledge base.

### Step 3: Tokens Start Streaming

```
┌─────────────────────────────────────────────────────────────────┐
│ 🔧 Platform Health Insight Assistant                            │
│                                                                 │
│   👤 How does EventBridge work in our architecture?             │
│                                                                 │
│   🤖 ┌──────────────────────────────────────────────────────┐  │
│      │ Based on the documentation, EventBridge serves as     │  │
│      │ the central event bus in our architecture. It         │  │
│      │ routes events between microservices using content-    │  │
│      │ based filtering rules.▌                               │  │
│      └──────────────────────────────────────────────────────┘  │
│      ┌─ Processing... ──────────────────────────────────────┐  │
│      │ 🔧 Calling **rag_search**...                         │  │
│      │ ✅ **rag_search** complete                            │  │
│      └──────────────────────────────────────────────────────┘  │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Ask about platform architecture, report an incident...      │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

Words appear one-by-one, just like ChatGPT. The status widget shows the tool search completed.

### Step 4: Response Complete

```
┌─────────────────────────────────────────────────────────────────┐
│ 🔧 Platform Health Insight Assistant                            │
│                                                                 │
│   👤 How does EventBridge work in our architecture?             │
│                                                                 │
│   🤖 ┌──────────────────────────────────────────────────────┐  │
│      │ Based on the documentation, EventBridge serves as     │  │
│      │ the central event bus in our architecture. It routes  │  │
│      │ events between microservices using content-based      │  │
│      │ filtering rules.                                      │  │
│      │                                                        │  │
│      │ Key features:                                          │  │
│      │ • Event routing with pattern matching                  │  │
│      │ • Dead-letter queues for failed deliveries             │  │
│      │ • Integration with 20+ AWS services                    │  │
│      │ • Schema registry for event validation                 │  │
│      └──────────────────────────────────────────────────────┘  │
│      ⏱️ 5.2s          🔧 1 tool(s)         📚 3 source(s)     │
│      ▶ Complete                                                 │
│                                                                 │
│      ▶ 📚 Sources                                               │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Ask about platform architecture, report an incident...      │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

The cursor is gone. Timing, tool count, and source count appear below the answer. The status widget collapses to "Complete".

### Step 5: Click the Sources Expander

```
┌─────────────────────────────────────────────────────────────────┐
│      ...                                                        │
│      ⏱️ 5.2s          🔧 1 tool(s)         📚 3 source(s)     │
│                                                                 │
│      ▼ 📚 Sources                                               │
│      ┌──────────────────────────────────────────────────────┐  │
│      │ • EventBridge Architecture (confluence) — 92% match   │  │
│      │ • Event-Driven Design Patterns (s3) — 87% match       │  │
│      │ • AWS Integration Guide (confluence) — 71% match      │  │
│      └──────────────────────────────────────────────────────┘  │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Ask about platform architecture, report an incident...      │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

Each source shows a title, type (confluence, s3, etc.), and a confidence percentage. If the source has a URI, the title is a clickable link.

### Step 6: Session Saved

After the exchange completes, the session automatically appears in the sidebar the next time the page refreshes. Future visits will show this conversation in the history, and clicking it will reload the full message exchange.

---

## Summary

| Concept | What We Learned |
|---|---|
| **Streamlit rerun model** | Entire script reruns on every interaction; use `st.session_state` to persist data |
| **Chat UI components** | `st.chat_message()`, `st.chat_input()`, `st.expander()`, `st.columns()` |
| **SSE streaming** | Backend sends `data: {...}` events; frontend parses and renders incrementally |
| **Session management** | UUID-based session IDs; backend stores history; sidebar loads and switches sessions |
| **Docker deployment** | `0.0.0.0` for container networking; `--server.headless=true` for no-browser environments |
| **Error handling** | Three-tier: connection error → streaming fallback → generic error |
| **Backend connection** | Environment variable URL; Cloud Map DNS in ECS |

**Next step:** [Step 16](step-16-backend-code-walkthrough.md) — we'll look at the backend that receives these requests and orchestrates the AI agent.
