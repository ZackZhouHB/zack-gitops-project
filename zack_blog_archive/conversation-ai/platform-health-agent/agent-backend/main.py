"""FastAPI entry point for the agent backend."""

import json
import time
import uuid
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_core.messages import AIMessage, HumanMessage

from agent.graph import create_agent_graph
from config import RECURSION_LIMIT

logger = logging.getLogger("api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")


# Global graph instance (compiled once at startup)
agent_graph = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    global agent_graph
    print("🚀 Agent backend starting...")
    agent_graph = create_agent_graph()
    print("✅ LangGraph agent compiled")
    yield
    print("🛑 Agent backend shutting down...")


app = FastAPI(title="Platform Health Insight Assistant", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log every request with timing."""
    start = time.time()
    response = await call_next(request)
    latency = int((time.time() - start) * 1000)
    logger.info(f"{request.method} {request.url.path} → {response.status_code} ({latency}ms)")
    return response


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    tool_calls: list[dict] = []
    sources: list[dict] = []  # [{title, source_type, score}]
    workflow_status: str = "complete"
    latency_ms: int = 0


@app.get("/health")
async def health():
    return {"status": "healthy", "agent": agent_graph is not None}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Handle a chat message — invoke the LangGraph agent."""
    start = time.time()
    conversation_id = request.conversation_id or str(uuid.uuid4())

    config = {
        "configurable": {"thread_id": conversation_id},
        "recursion_limit": RECURSION_LIMIT,
    }

    initial_state = {
        "messages": [HumanMessage(content=request.message)],
        "current_workflow": "general_qa",
        "workflow_step": 0,
        "workflow_status": "in_progress",
        "workflow_data": {},
        "incident_result": {},
        "tool_calls_log": [],
        "iteration_count": 0,
    }

    result = await agent_graph.ainvoke(initial_state, config)

    # Extract the final AI response
    final_message = ""
    for msg in reversed(result["messages"]):
        if isinstance(msg, AIMessage) and msg.content and not msg.tool_calls:
            final_message = msg.content
            break

    # Extract sources from RAG tool calls
    sources = []
    for tc in result.get("tool_calls_log", []):
        if tc["name"] == "rag_search" and "rag_results" in tc:
            for r in tc["rag_results"]:
                sources.append({
                    "title": r["title"],
                    "source_type": r["source_type"],
                    "score": r["score"],
                })

    latency_ms = int((time.time() - start) * 1000)

    return ChatResponse(
        response=final_message or "I couldn't generate a response.",
        conversation_id=conversation_id,
        tool_calls=result.get("tool_calls_log", []),
        sources=sources,
        workflow_status=result.get("workflow_status", "complete"),
        latency_ms=latency_ms,
    )


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Stream agent responses with step-by-step progress."""
    conversation_id = request.conversation_id or str(uuid.uuid4())

    config = {
        "configurable": {"thread_id": conversation_id},
        "recursion_limit": RECURSION_LIMIT,
    }

    initial_state = {
        "messages": [HumanMessage(content=request.message)],
        "current_workflow": "general_qa",
        "workflow_step": 0,
        "workflow_status": "in_progress",
        "workflow_data": {},
        "incident_result": {},
        "tool_calls_log": [],
        "iteration_count": 0,
    }

    async def stream():
        start_time = time.time()
        all_sources = []
        active_tools = []
        
        async for event in agent_graph.astream_events(
            initial_state,
            config,
            version="v2",
        ):
            kind = event.get("event", "")
            node = event.get("metadata", {}).get("langgraph_node", "")

            # Detect tool node start/end via chain events
            if kind == "on_chain_start" and node == "tools":
                yield f"data: {json.dumps({'step': 'tool_start', 'tool': 'searching knowledge base'})}\n\n"

            elif kind == "on_chain_end" and node == "tools":
                # Extract sources from tool_calls_log in the output
                output = event.get("data", {}).get("output", {})
                tool_log = output.get("tool_calls_log", []) if isinstance(output, dict) else []
                for tc in tool_log:
                    if tc.get("name") == "rag_search" and "rag_results" in tc:
                        for r in tc["rag_results"]:
                            all_sources.append({
                                "title": r["title"],
                                "source_type": r["source_type"],
                                "score": r["score"],
                            })
                tool_names = [tc.get("name", "tool") for tc in tool_log] if tool_log else ["tool"]
                yield f"data: {json.dumps({'step': 'tool_end', 'tool': ', '.join(tool_names)})}\n\n"

            elif kind == "on_chat_model_stream":
                # Only stream tokens from answer-producing nodes, not router/intermediates
                if node in ("router", "gather_symptoms", "search_docs"):
                    continue

                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    # Skip tool-calling chunks (they contain JSON, not answer text)
                    if (hasattr(chunk, "tool_calls") and chunk.tool_calls) or \
                       (hasattr(chunk, "tool_call_chunks") and chunk.tool_call_chunks):
                        continue
                    # Extract text from content (may be string or list of blocks)
                    content = chunk.content
                    if isinstance(content, list):
                        text = "".join(
                            block.get("text", "") if isinstance(block, dict) else str(block)
                            for block in content
                        )
                    else:
                        text = str(content)
                    if text:
                        data = json.dumps({"step": "token", "content": text})
                        yield f"data: {data}\n\n"

        # Emit deduplicated sources before complete
        if all_sources:
            seen = set()
            unique = []
            for s in all_sources:
                key = s["title"]
                if key not in seen:
                    seen.add(key)
                    unique.append(s)
            yield f"data: {json.dumps({'step': 'sources', 'sources': unique})}\n\n"

        latency_ms = int((time.time() - start_time) * 1000)
        yield f"data: {json.dumps({'step': 'complete', 'conversation_id': conversation_id, 'latency_ms': latency_ms})}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")
