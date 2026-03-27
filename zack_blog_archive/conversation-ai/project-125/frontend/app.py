"""
Project 125 — Platform Health Action Agent Chat UI

A Streamlit chat interface that lets you:
  1. Ask questions (RAG search, Jira search — auto-complete)
  2. Request actions (create ticket, send Slack — triggers HITL approval)
  3. Approve / Reject / Edit proposed actions before they execute

Start:
  cd project-125 && source .venv/bin/activate
  # Terminal 1: Start the agent backend
  cd agent-backend && python main.py
  # Terminal 2: Start the UI
  cd frontend && streamlit run app.py
"""

import streamlit as st
import requests
import json
import time
import os

AGENT_URL = os.getenv("AGENT_BACKEND_URL", "http://localhost:8010")

# ── Page Config ──
st.set_page_config(
    page_title="Platform Health Agent",
    page_icon="🏥",
    layout="wide",
)

# ── Custom CSS ──
st.markdown("""
<style>
    .approval-box {
        border: 2px solid #ff9800;
        border-radius: 10px;
        padding: 20px;
        background-color: #fff8e1;
        margin: 10px 0;
    }
    .approved-box {
        border: 2px solid #4caf50;
        border-radius: 10px;
        padding: 15px;
        background-color: #e8f5e9;
        margin: 10px 0;
    }
    .rejected-box {
        border: 2px solid #f44336;
        border-radius: 10px;
        padding: 15px;
        background-color: #ffebee;
        margin: 10px 0;
    }
    .tool-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.8em;
        margin: 2px;
    }
    .read-badge { background-color: #e3f2fd; color: #1565c0; }
    .write-badge { background-color: #fce4ec; color: #c62828; }
</style>
""", unsafe_allow_html=True)

# ── Session State ──
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_thread" not in st.session_state:
    st.session_state.pending_thread = None
if "pending_action" not in st.session_state:
    st.session_state.pending_action = None
if "agent_healthy" not in st.session_state:
    st.session_state.agent_healthy = False


def check_health():
    """Check if the agent backend is running."""
    try:
        r = requests.get(f"{AGENT_URL}/health", timeout=3)
        data = r.json()
        st.session_state.agent_healthy = data.get("status") == "healthy"
        return data
    except Exception:
        st.session_state.agent_healthy = False
        return None


def send_message(user_msg: str) -> dict:
    """Send a message to the agent and return the response."""
    try:
        r = requests.post(
            f"{AGENT_URL}/chat",
            json={"message": user_msg},
            timeout=120,
        )
        return r.json()
    except requests.exceptions.Timeout:
        return {"error": "Agent timed out (>120s). Try a simpler query."}
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to agent. Is it running on port 8010?"}
    except Exception as e:
        return {"error": str(e)}


def approve_action(thread_id: str) -> dict:
    """Approve the pending write action."""
    try:
        r = requests.post(f"{AGENT_URL}/chat/{thread_id}/approve", timeout=60)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def reject_action(thread_id: str) -> dict:
    """Reject the pending write action."""
    try:
        r = requests.post(f"{AGENT_URL}/chat/{thread_id}/reject", timeout=30)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def edit_action(thread_id: str, edited_args: dict) -> dict:
    """Edit and approve the pending action."""
    try:
        r = requests.post(
            f"{AGENT_URL}/chat/{thread_id}/edit",
            json={"edited_args": edited_args},
            timeout=60,
        )
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def render_tool_calls(tool_calls: list):
    """Render tool call badges."""
    if not tool_calls:
        return
    cols = st.columns([1, 3])
    with cols[0]:
        st.caption("🔧 Tools used:")
    with cols[1]:
        badges = []
        for tc in tool_calls:
            tool = tc.get("tool", "?")
            is_write = tc.get("is_write", False)
            approval = tc.get("approval", "")
            latency = tc.get("latency_ms", "?")
            if is_write:
                icon = "🔴" if approval == "rejected" else "🟠" if not approval else "🟢"
                label = f"{icon} {tool}"
                if approval:
                    label += f" ({approval})"
            else:
                label = f"🔵 {tool}"
            badges.append(f"`{label} {latency}ms`")
        st.markdown(" ".join(badges))


def render_sources(sources: list):
    """Render RAG sources."""
    if not sources:
        return
    with st.expander(f"📚 Sources ({len(sources)})"):
        for s in sources:
            score = s.get("score", 0)
            score_pct = f"{score:.0%}" if isinstance(score, float) else str(score)
            st.markdown(f"- **{s.get('title', '?')}** ({s.get('source_type', '?')}) — {score_pct}")


def render_pending_approval(action: dict, thread_id: str):
    """Render the approval UI for a pending write action."""
    tool = action.get("tool", "unknown")
    args = action.get("args", {})

    st.warning("⏸️ **Action requires your approval**")

    with st.container():
        st.markdown(f"### 🔐 Approve: `{tool}`")

        # Show proposed args in a readable format
        if tool == "create_ticket":
            st.markdown(f"**Summary**: {args.get('summary', '?')}")
            st.markdown(f"**Priority**: {args.get('priority', '?')}")
            if args.get("labels"):
                st.markdown(f"**Labels**: {', '.join(args['labels'])}")
            if args.get("description"):
                with st.expander("📝 Full description"):
                    st.markdown(args["description"])

        elif tool in ("send_message", "create_thread"):
            st.markdown(f"**Channel**: {args.get('channel', '?')}")
            st.markdown(f"**Message preview**:")
            st.info(args.get("text", args.get("summary", "?"))[:500])

        elif tool == "add_comment":
            st.markdown(f"**Ticket**: {args.get('issue_key', '?')}")
            st.markdown(f"**Comment**: {args.get('comment_text', '?')[:300]}")

        elif tool == "update_ticket":
            st.markdown(f"**Ticket**: {args.get('issue_key', '?')}")
            for k, v in args.items():
                if k != "issue_key":
                    st.markdown(f"**{k}**: {v}")

        elif tool == "send_rich_notification":
            st.markdown(f"**Channel**: {args.get('channel', '?')}")
            st.markdown(f"**Title**: {args.get('title', '?')}")

        else:
            st.json(args)

        # Show raw args in expander
        with st.expander("🔍 Raw tool arguments"):
            st.json(args)

        # Action buttons
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("✅ Approve", key="approve_btn", type="primary", use_container_width=True):
                with st.spinner("Executing approved action..."):
                    result = approve_action(thread_id)
                handle_agent_response(result, is_approval=True)

        with col2:
            if st.button("❌ Reject", key="reject_btn", use_container_width=True):
                with st.spinner("Rejecting..."):
                    result = reject_action(thread_id)
                handle_agent_response(result, is_rejection=True)

        with col3:
            if st.button("✏️ Edit & Approve", key="edit_btn", use_container_width=True):
                st.session_state.show_edit_form = True

        # Edit form (shown when Edit button is clicked)
        if st.session_state.get("show_edit_form"):
            st.markdown("---")
            st.markdown("**Edit the arguments:**")
            edited_json = st.text_area(
                "Modify the JSON below:",
                value=json.dumps(args, indent=2),
                height=200,
                key="edit_json",
            )
            if st.button("Submit Edit", key="submit_edit"):
                try:
                    edited_args = json.loads(edited_json)
                    with st.spinner("Executing with edits..."):
                        result = edit_action(thread_id, edited_args)
                    st.session_state.show_edit_form = False
                    handle_agent_response(result, is_edit=True)
                except json.JSONDecodeError:
                    st.error("Invalid JSON. Please fix and try again.")


def handle_agent_response(data: dict, is_approval=False, is_rejection=False, is_edit=False):
    """Process agent response — either complete or pending approval."""
    if "error" in data:
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"❌ Error: {data['error']}",
        })
        st.session_state.pending_thread = None
        st.session_state.pending_action = None
        st.rerun()
        return

    status = data.get("status", "complete")

    if status == "pending_approval":
        # Store pending state for the approval UI
        st.session_state.pending_thread = data["conversation_id"]
        st.session_state.pending_action = data.get("pending_action")

        # Add partial response if any
        if data.get("response"):
            prefix = ""
            if is_approval:
                prefix = "✅ Previous action approved. "
            st.session_state.messages.append({
                "role": "assistant",
                "content": prefix + data["response"],
                "tool_calls": data.get("tool_calls", []),
                "sources": data.get("sources", []),
                "latency_ms": data.get("latency_ms"),
            })
        st.rerun()

    else:
        # Complete — clear pending state
        prefix = ""
        if is_approval:
            prefix = "✅ **Action approved and executed!**\n\n"
        elif is_rejection:
            prefix = "❌ **Action rejected.**\n\n"
        elif is_edit:
            prefix = "✏️ **Action edited and executed!**\n\n"

        st.session_state.messages.append({
            "role": "assistant",
            "content": prefix + data.get("response", ""),
            "tool_calls": data.get("tool_calls", []),
            "sources": data.get("sources", []),
            "latency_ms": data.get("latency_ms"),
        })
        st.session_state.pending_thread = None
        st.session_state.pending_action = None
        st.session_state.show_edit_form = False
        st.rerun()


# ── Sidebar ──
with st.sidebar:
    st.title("🏥 Platform Health Agent")

    health = check_health()
    if health:
        st.success(f"Agent: Connected")
        st.caption(f"HITL: {'✅ Enabled' if health.get('hitl_enabled') else '❌ Disabled'}")
        st.caption(f"Pending approvals: {health.get('pending_approvals', 0)}")
        st.caption(f"Tools: {len(health.get('tools', []))}")
    else:
        st.error("Agent: Not connected")
        st.caption("Start: `cd agent-backend && python main.py`")

    st.divider()

    st.markdown("### 💡 Try these prompts")
    examples = [
        "What is the architecture of our EKS RAG system?",
        "Search Jira for open EKS tickets",
        "Are there any tickets about Bedrock costs?",
        "Create a ticket for a Redis cache miss spike",
        "Send a status update to #all-platform-health-lab about the DNS fix",
        "The Lambda health analyzer is timing out — investigate and create a ticket",
    ]
    for ex in examples:
        if st.button(ex, key=f"ex_{hash(ex)}", use_container_width=True):
            st.session_state.next_message = ex

    st.divider()

    if st.button("🗑️ Clear chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.pending_thread = None
        st.session_state.pending_action = None
        st.rerun()

    st.divider()
    st.markdown("### 🔧 How it works")
    st.markdown("""
    1. **Read tools** (RAG, Jira search) execute automatically
    2. **Write tools** (create ticket, send Slack) pause for your approval
    3. You can **approve**, **reject**, or **edit** before execution
    """)


# ── Main Chat Area ──
st.title("💬 Platform Health Chat")

# Render chat history
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant":
            render_tool_calls(msg.get("tool_calls", []))
            render_sources(msg.get("sources", []))
            if msg.get("latency_ms"):
                st.caption(f"⏱️ {msg['latency_ms']}ms")

# Show pending approval UI if there is one
if st.session_state.pending_action and st.session_state.pending_thread:
    render_pending_approval(
        st.session_state.pending_action,
        st.session_state.pending_thread,
    )

# Chat input
next_msg = st.session_state.pop("next_message", None)
user_input = st.chat_input("Ask about platform health, create tickets, or send notifications...")

message_to_send = next_msg or user_input

if message_to_send:
    # Add user message
    st.session_state.messages.append({"role": "user", "content": message_to_send})

    with st.chat_message("user"):
        st.markdown(message_to_send)

    with st.chat_message("assistant"):
        with st.spinner("🤔 Thinking..."):
            data = send_message(message_to_send)
        handle_agent_response(data)
