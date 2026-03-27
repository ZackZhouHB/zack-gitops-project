"""
FastAPI entry point — Project 125 Action Agent with Human-in-the-Loop

Endpoints:
  GET  /health                       — Health check
  POST /chat                         — Chat (auto-detects HITL interrupts)
  POST /chat/{thread_id}/approve     — Approve a pending write action
  POST /chat/{thread_id}/reject      — Reject a pending write action
  POST /chat/{thread_id}/edit        — Edit and approve a pending action
  GET  /chat/{thread_id}/status      — Check thread status (pending/complete)
  POST /chat/stream                  — SSE streaming chat
"""

import json
import time
import uuid
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langgraph.types import Command

from agent.graph import create_agent_graph
from agent import AgentState
from eval.guardrails import run_input_guardrails, run_output_guardrails

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("main")

# -- App State --
agent_graph = None
checkpointer = None
# Track threads that are waiting for human approval
pending_threads: dict[str, dict] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: compile the agent graph with checkpointer."""
    global agent_graph, checkpointer
    logger.info("Compiling agent graph with HITL support...")
    agent_graph, checkpointer = create_agent_graph()
    logger.info("Agent graph ready — RAG + Jira + Slack tools loaded, HITL enabled")
    yield
    logger.info("Shutting down")


app = FastAPI(title="Project 125 Action Agent (HITL)", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# -- Request/Response Models --

class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    sources: list[dict]
    tool_calls: list[dict]
    latency_ms: int
    status: str = "complete"  # "complete" | "pending_approval" | "blocked"
    pending_action: dict | None = None
    guardrail_warnings: list[dict] | None = None


class ApprovalRequest(BaseModel):
    edited_args: dict | None = None  # For edit+approve


def _extract_response(result: dict) -> str:
    """Extract text response from graph result."""
    for msg in reversed(result["messages"]):
        if hasattr(msg, "content") and msg.type == "ai":
            if isinstance(msg.content, str) and msg.content:
                return msg.content
            elif isinstance(msg.content, list):
                text = ""
                for block in msg.content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text += block["text"]
                if text:
                    return text
    return ""


def _extract_sources(result: dict) -> list[dict]:
    """Extract RAG sources from tool call logs."""
    sources = []
    for log_entry in result.get("tool_calls_log", []):
        if "rag_results" in log_entry:
            for r in log_entry["rag_results"][:5]:
                sources.append({
                    "title": r.get("title", ""),
                    "source_type": r.get("source_type", ""),
                    "score": r.get("score", 0),
                    "url": r.get("url", ""),
                })
    return sources


# -- Endpoints --

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "agent": agent_graph is not None,
        "hitl_enabled": True,
        "pending_approvals": len(pending_threads),
        "tools": list(sorted(
            {"rag_search", "search_issues", "create_ticket", "get_ticket",
             "update_ticket", "add_comment", "send_message", "create_thread",
             "reply_in_thread", "list_channels", "send_rich_notification", "web_search"}
        )),
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat endpoint with HITL support.

    If the agent wants to call a write tool, returns status="pending_approval"
    with the proposed action. Use /chat/{thread_id}/approve to continue.
    """
    start = time.time()
    conversation_id = request.conversation_id or str(uuid.uuid4())

    # ── INPUT GUARDRAILS ──
    input_check = run_input_guardrails(request.message)
    guardrail_warnings = [
        {"guardrail": v.guardrail, "severity": v.severity, "message": v.message}
        for v in input_check.violations
    ]

    if not input_check.passed:
        blocked_reasons = [v.message for v in input_check.violations if v.severity == "block"]
        logger.warning(f"Input guardrails blocked: {blocked_reasons}")
        return ChatResponse(
            response=f"⚠️ Request blocked by guardrails: {'; '.join(blocked_reasons)}. "
                     "Please rephrase your request within the platform health domain.",
            conversation_id=conversation_id,
            sources=[],
            tool_calls=[],
            latency_ms=int((time.time() - start) * 1000),
            status="blocked",
            guardrail_warnings=guardrail_warnings,
        )

    # Use sanitized text if PII was detected and masked
    message_text = input_check.sanitized_text or request.message

    initial_state: AgentState = {
        "messages": [("human", message_text)],
        "tool_calls_log": [],
        "iteration_count": 0,
        "pending_approval": None,
        "approval_response": None,
    }

    config = {"configurable": {"thread_id": conversation_id}}

    try:
        result = await agent_graph.ainvoke(initial_state, config)
    except Exception as e:
        # Check if this is a GraphInterrupt (HITL pause)
        if "GraphInterrupt" in type(e).__name__ or "interrupt" in str(type(e)).lower():
            raise
        raise

    latency_ms = int((time.time() - start) * 1000)

    # Check if the graph was interrupted (HITL)
    graph_state = await agent_graph.aget_state(config)

    if graph_state.next:
        # Graph is paused — waiting for human approval
        interrupts = graph_state.tasks
        pending_action = None
        for task in interrupts:
            if hasattr(task, "interrupts") and task.interrupts:
                pending_action = task.interrupts[0].value
                break

        if pending_action:
            pending_threads[conversation_id] = {
                "action": pending_action,
                "created_at": time.time(),
                "config": config,
            }

            logger.info(f"HITL: Thread {conversation_id} paused for approval — {pending_action.get('tool', '?')}")

            return ChatResponse(
                response=_extract_response(graph_state.values),
                conversation_id=conversation_id,
                sources=_extract_sources(graph_state.values),
                tool_calls=graph_state.values.get("tool_calls_log", []),
                latency_ms=latency_ms,
                status="pending_approval",
                pending_action=pending_action,
            )

    # Graph completed normally (no write tools, or all reads)
    logger.info(f"Chat completed: {latency_ms}ms, {len(result.get('tool_calls_log', []))} tool calls")

    # ── OUTPUT GUARDRAILS ──
    response_text = _extract_response(result)
    tool_results = [str(tc.get("result_preview", "")) for tc in result.get("tool_calls_log", [])]
    output_check = run_output_guardrails(response_text, tool_results, result.get("tool_calls_log", []))
    guardrail_warnings += [
        {"guardrail": v.guardrail, "severity": v.severity, "message": v.message}
        for v in output_check.violations
    ]

    return ChatResponse(
        response=response_text,
        conversation_id=conversation_id,
        sources=_extract_sources(result),
        tool_calls=result.get("tool_calls_log", []),
        latency_ms=latency_ms,
        status="complete",
        guardrail_warnings=guardrail_warnings or None,
    )


@app.post("/chat/{thread_id}/approve", response_model=ChatResponse)
async def approve_action(thread_id: str):
    """Approve a pending write action and resume the agent."""
    if thread_id not in pending_threads:
        raise HTTPException(404, f"No pending approval for thread {thread_id}")

    start = time.time()
    config = pending_threads[thread_id]["config"]
    action = pending_threads.pop(thread_id)

    logger.info(f"HITL: Approving action for thread {thread_id}")

    result = await agent_graph.ainvoke(
        Command(resume={"decision": "approve"}),
        config,
    )

    # Check if there are MORE write tools pending (agent may chain writes)
    graph_state = await agent_graph.aget_state(config)

    latency_ms = int((time.time() - start) * 1000)

    if graph_state.next:
        pending_action = None
        for task in graph_state.tasks:
            if hasattr(task, "interrupts") and task.interrupts:
                pending_action = task.interrupts[0].value
                break

        if pending_action:
            pending_threads[thread_id] = {
                "action": pending_action,
                "created_at": time.time(),
                "config": config,
            }
            logger.info(f"HITL: Thread {thread_id} has another pending action — {pending_action.get('tool', '?')}")

            return ChatResponse(
                response=_extract_response(graph_state.values),
                conversation_id=thread_id,
                sources=_extract_sources(graph_state.values),
                tool_calls=graph_state.values.get("tool_calls_log", []),
                latency_ms=latency_ms,
                status="pending_approval",
                pending_action=pending_action,
            )

    logger.info(f"HITL: Thread {thread_id} completed after approval — {latency_ms}ms")

    return ChatResponse(
        response=_extract_response(result),
        conversation_id=thread_id,
        sources=_extract_sources(result),
        tool_calls=result.get("tool_calls_log", []),
        latency_ms=latency_ms,
        status="complete",
    )


@app.post("/chat/{thread_id}/reject", response_model=ChatResponse)
async def reject_action(thread_id: str):
    """Reject a pending write action. Agent will acknowledge and stop."""
    if thread_id not in pending_threads:
        raise HTTPException(404, f"No pending approval for thread {thread_id}")

    start = time.time()
    config = pending_threads[thread_id]["config"]
    pending_threads.pop(thread_id)

    logger.info(f"HITL: Rejecting action for thread {thread_id}")

    result = await agent_graph.ainvoke(
        Command(resume={"decision": "reject"}),
        config,
    )

    # Continue resolving any remaining interrupts with reject
    graph_state = await agent_graph.aget_state(config)
    while graph_state.next:
        result = await agent_graph.ainvoke(
            Command(resume={"decision": "reject"}),
            config,
        )
        graph_state = await agent_graph.aget_state(config)

    latency_ms = int((time.time() - start) * 1000)
    logger.info(f"HITL: Thread {thread_id} completed after rejection — {latency_ms}ms")

    return ChatResponse(
        response=_extract_response(result),
        conversation_id=thread_id,
        sources=_extract_sources(result),
        tool_calls=result.get("tool_calls_log", []),
        latency_ms=latency_ms,
        status="complete",
    )


@app.post("/chat/{thread_id}/edit", response_model=ChatResponse)
async def edit_and_approve(thread_id: str, request: ApprovalRequest):
    """Edit the pending action's arguments and approve it."""
    if thread_id not in pending_threads:
        raise HTTPException(404, f"No pending approval for thread {thread_id}")

    start = time.time()
    config = pending_threads[thread_id]["config"]
    pending_threads.pop(thread_id)

    logger.info(f"HITL: Edit+approve for thread {thread_id}")

    result = await agent_graph.ainvoke(
        Command(resume={"decision": "edit", "edited_args": request.edited_args or {}}),
        config,
    )

    # Check for more interrupts
    graph_state = await agent_graph.aget_state(config)
    latency_ms = int((time.time() - start) * 1000)

    if graph_state.next:
        pending_action = None
        for task in graph_state.tasks:
            if hasattr(task, "interrupts") and task.interrupts:
                pending_action = task.interrupts[0].value
                break

        if pending_action:
            pending_threads[thread_id] = {
                "action": pending_action,
                "created_at": time.time(),
                "config": config,
            }
            return ChatResponse(
                response=_extract_response(graph_state.values),
                conversation_id=thread_id,
                sources=_extract_sources(graph_state.values),
                tool_calls=graph_state.values.get("tool_calls_log", []),
                latency_ms=latency_ms,
                status="pending_approval",
                pending_action=pending_action,
            )

    return ChatResponse(
        response=_extract_response(result),
        conversation_id=thread_id,
        sources=_extract_sources(result),
        tool_calls=result.get("tool_calls_log", []),
        latency_ms=latency_ms,
        status="complete",
    )


@app.get("/chat/{thread_id}/status")
async def thread_status(thread_id: str):
    """Check if a thread has a pending approval."""
    if thread_id in pending_threads:
        info = pending_threads[thread_id]
        return {
            "thread_id": thread_id,
            "status": "pending_approval",
            "pending_action": info["action"],
            "waiting_since": info["created_at"],
        }
    return {"thread_id": thread_id, "status": "complete_or_not_found"}


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """SSE streaming chat endpoint."""
    conversation_id = request.conversation_id or str(uuid.uuid4())

    initial_state: AgentState = {
        "messages": [("human", request.message)],
        "tool_calls_log": [],
        "iteration_count": 0,
        "pending_approval": None,
        "approval_response": None,
    }

    config = {"configurable": {"thread_id": conversation_id}}

    async def event_generator():
        start = time.time()
        tool_calls_log = []

        try:
            async for event in agent_graph.astream_events(initial_state, config, version="v2"):
                kind = event.get("event")

                if kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content"):
                        content = chunk.content
                        if isinstance(content, str) and content:
                            yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"
                        elif isinstance(content, list):
                            for block in content:
                                if isinstance(block, dict) and block.get("type") == "text":
                                    yield f"data: {json.dumps({'type': 'token', 'content': block['text']})}\n\n"

                elif kind == "on_tool_start":
                    tool_name = event.get("name", "")
                    yield f"data: {json.dumps({'type': 'tool_start', 'tool': tool_name})}\n\n"

                elif kind == "on_tool_end":
                    tool_name = event.get("name", "")
                    output = event.get("data", {}).get("output", "")
                    output_preview = str(output)[:300] if output else ""
                    tool_calls_log.append({"tool": tool_name, "output_preview": output_preview})
                    yield f"data: {json.dumps({'type': 'tool_end', 'tool': tool_name})}\n\n"

            # Check for HITL interrupt after streaming
            graph_state = await agent_graph.aget_state(config)
            if graph_state.next:
                pending_action = None
                for task in graph_state.tasks:
                    if hasattr(task, "interrupts") and task.interrupts:
                        pending_action = task.interrupts[0].value
                        break

                if pending_action:
                    pending_threads[conversation_id] = {
                        "action": pending_action,
                        "created_at": time.time(),
                        "config": config,
                    }
                    yield f"data: {json.dumps({'type': 'approval_required', 'conversation_id': conversation_id, 'pending_action': pending_action})}\n\n"

            latency_ms = int((time.time() - start) * 1000)
            yield f"data: {json.dumps({'type': 'complete', 'conversation_id': conversation_id, 'latency_ms': latency_ms, 'tool_calls': len(tool_calls_log)})}\n\n"

        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010)
