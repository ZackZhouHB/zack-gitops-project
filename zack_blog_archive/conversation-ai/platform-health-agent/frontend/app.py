"""Streamlit frontend for the Platform Health Insight Assistant.

Features:
- Streaming responses (tokens appear as they're generated, like ChatGPT)
- Source citations with confidence scores
- Response timing display
- Tool usage indicators
"""

import os
import time
import uuid
import json

import requests
import sseclient
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
                        st.markdown(
                            f"- **{s['title']}** ({s['source_type']}) — {score_pct}% match"
                        )

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
                            st.markdown(
                                f"- **{s['title']}** ({s['source_type']}) — {score_pct}% match"
                            )

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

# Sidebar
with st.sidebar:
    st.markdown("### Session Info")
    st.text(f"ID: {st.session_state.conversation_id[:8]}...")
    if st.button("New Conversation"):
        st.session_state.conversation_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()
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
