from fastapi import FastAPI, HTTPException, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict
import logging
import time
import json
import asyncio

from .config import settings
from .security.auth import User, get_current_user, require_auth, create_token, MOCK_USERS
from .security.audit import AuditLogger
from .security.validation import InputValidator
from .utils.cache import ResponseCache
from .utils.router import ModelRouter
from .utils.memory import ConversationMemory
from .utils.queue import JobQueue, DocumentWorker
from .utils.limits import RateLimiter, TokenTracker
from .connectors.web_connector import WebConnector
from .utils.pipeline import DataPipelineScheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="RAG Cloud API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

rag_service = None
rag_agent = None
audit = AuditLogger()
cache = ResponseCache()
memory = ConversationMemory()
job_queue = JobQueue()
doc_worker = None
rate_limiter = RateLimiter(requests_per_minute=30)
token_tracker = TokenTracker()
pipeline = DataPipelineScheduler()

class QueryRequest(BaseModel):
    question: str
    top_k: int = 5
    search_type: str = "hybrid"
    use_rerank: bool = True
    alpha: float = 0.5
    use_cache: bool = True
    model_tier: str = None
    session_id: str = None  # For conversation memory
    source_filter: str = None  # Filter by source URL (contains match)

class LoginRequest(BaseModel):
    username: str

class AgentRequest(BaseModel):
    query: str

class EvalRequest(BaseModel):
    question: str
    answer: str
    contexts: List[str] = []

@app.on_event("startup")
async def startup():
    global rag_service, rag_agent, doc_worker
    logger.info("Starting RAG Cloud API...")
    
    from .rag.service import RAGService
    rag_service = RAGService()
    
    from .agents.rag_agent import RAGAgent
    rag_agent = RAGAgent(rag_service, rag_service.bedrock, settings.bedrock_model_id)
    
    # Start background worker
    doc_worker = DocumentWorker(job_queue, rag_service)
    await doc_worker.start()
    
    logger.info("RAG service, agent, and worker initialized")

# === Auth Endpoints ===

@app.post("/auth/login")
async def login(req: LoginRequest):
    if req.username not in MOCK_USERS:
        raise HTTPException(status_code=401, detail="Unknown user")
    user = MOCK_USERS[req.username]
    token = create_token(user)
    audit.log_auth(user.user_id, "login", True)
    return {"token": token, "user": user.model_dump()}

@app.get("/auth/me")
async def get_me(user: User = Depends(require_auth)):
    return user.model_dump()

# === Public Endpoints ===

@app.get("/")
async def root():
    return {"status": "healthy", "service": "RAG Cloud"}

@app.get("/health")
async def health():
    return {"status": "healthy", "opensearch": "connected"}

# === Document Endpoints ===

@app.post("/upload")
async def upload(
    file: UploadFile = File(...),
    allowed_groups: str = "",
    user: Optional[User] = Depends(get_current_user)
):
    """Synchronous upload - processes immediately"""
    try:
        groups = [g.strip() for g in allowed_groups.split(",") if g.strip()]
        result = await rag_service.process_document(file, groups)
        
        user_id = user.user_id if user else "anonymous"
        audit.log_upload(user_id, file.filename, result["chunks"], groups)
        return result
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload/async")
async def upload_async(
    file: UploadFile = File(...),
    allowed_groups: str = "",
    user: Optional[User] = Depends(get_current_user)
):
    """Async upload - returns job_id immediately, processes in background"""
    try:
        groups = [g.strip() for g in allowed_groups.split(",") if g.strip()]
        content = await file.read()
        
        # Create job and enqueue
        job_id = job_queue.create_job(file.filename, content, groups)
        await job_queue.enqueue(job_id)
        
        user_id = user.user_id if user else "anonymous"
        audit.log("UPLOAD_ASYNC", user_id, {"filename": file.filename, "job_id": job_id})
        
        return {"job_id": job_id, "status": "queued", "filename": file.filename}
    except Exception as e:
        logger.error(f"Async upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Get processing job status"""
    job = job_queue.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@app.get("/jobs")
async def list_jobs():
    """List recent processing jobs"""
    return {"jobs": job_queue.list_jobs()}

@app.get("/documents")
async def list_documents():
    try:
        return {"documents": rag_service.list_documents()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/documents/{source}")
async def delete_document(source: str, user: Optional[User] = Depends(get_current_user)):
    """Delete all chunks for a document"""
    try:
        result = await rag_service.delete_document(source)
        user_id = user.user_id if user else "anonymous"
        audit.log("DELETE_DOC", user_id, {"source": source})
        return result
    except Exception as e:
        logger.error(f"Delete failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# === Query Endpoints ===

@app.post("/query")
async def query(req: QueryRequest, user: Optional[User] = Depends(get_current_user)):
    try:
        user_id = user.user_id if user else "anonymous"
        
        # Rate limiting
        allowed, retry_after = rate_limiter.check(user_id)
        if not allowed:
            raise HTTPException(status_code=429, detail=f"Rate limit exceeded. Retry after {retry_after}s")
        
        # Validate input
        is_valid, sanitized, warnings = InputValidator.validate_query(req.question)
        if not is_valid:
            raise HTTPException(status_code=400, detail=warnings[0])
        
        # Session ID for memory
        session_id = req.session_id or user_id
        
        # Get conversation history
        history = memory.format_for_prompt(session_id)
        
        # Check cache (skip if using memory context)
        cache_params = {"top_k": req.top_k, "search_type": req.search_type}
        if req.use_cache and not history:
            cached = cache.get(sanitized, cache_params)
            if cached:
                cached["from_cache"] = True
                return cached
        
        start = time.time()
        user_groups = user.groups if user else []
        
        # Route to appropriate model
        model_id, tier = ModelRouter.route(sanitized, req.model_tier)
        
        result = await rag_service.query(
            sanitized, req.top_k, req.search_type,
            req.use_rerank, req.alpha, user_groups, model_id,
            conversation_history=history,
            source_filter=req.source_filter
        )
        
        # Handle no results
        if not result.get("sources"):
            result["answer"] = "I couldn't find relevant information in the knowledge base to answer your question. Try rephrasing or uploading relevant documents."
            result["no_results"] = True
        
        # Track tokens (approximate)
        input_tokens = len(sanitized.split()) * 1.3 + len(str(result.get("sources", []))) * 2
        output_tokens = len(result.get("answer", "").split()) * 1.3
        token_tracker.track(user_id, model_id, int(input_tokens), int(output_tokens))
        
        # Sanitize output
        result["answer"] = InputValidator.sanitize_output(result["answer"])
        result["model_tier"] = tier
        result["warnings"] = warnings
        result["from_cache"] = False
        result["session_id"] = session_id
        result["processing_time_ms"] = round((time.time() - start) * 1000)
        
        # Save to memory
        memory.add_turn(session_id, sanitized, result["answer"])
        
        # Cache result (only if no history context)
        if req.use_cache and not history:
            cache.set(sanitized, result, cache_params)
        
        elapsed = time.time() - start
        sources = [s["source"] for s in result.get("sources", [])]
        audit.log_query(user_id, sanitized, sources, elapsed)
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query/stream")
async def query_stream(req: QueryRequest, user: Optional[User] = Depends(get_current_user)):
    """Streaming response for long answers"""
    is_valid, sanitized, warnings = InputValidator.validate_query(req.question)
    if not is_valid:
        raise HTTPException(status_code=400, detail=warnings[0])
    
    user_groups = user.groups if user else []
    
    async def generate():
        # First yield sources
        result = await rag_service.query(
            sanitized, req.top_k, req.search_type,
            req.use_rerank, req.alpha, user_groups
        )
        yield json.dumps({"type": "sources", "data": result["sources"]}) + "\n"
        
        # Then yield answer in chunks
        answer = result["answer"]
        chunk_size = 50
        for i in range(0, len(answer), chunk_size):
            yield json.dumps({"type": "answer", "data": answer[i:i+chunk_size]}) + "\n"
            await asyncio.sleep(0.05)
        
        yield json.dumps({"type": "done"}) + "\n"
    
    return StreamingResponse(generate(), media_type="application/x-ndjson")

# === Agent Endpoint ===

@app.post("/agent")
async def agent_query(req: AgentRequest, user: Optional[User] = Depends(get_current_user)):
    try:
        is_valid, sanitized, warnings = InputValidator.validate_query(req.query)
        if not is_valid:
            raise HTTPException(status_code=400, detail=warnings[0])
        
        user_groups = user.groups if user else []
        result = await rag_agent.run(sanitized, user_groups)
        
        user_id = user.user_id if user else "anonymous"
        audit.log("AGENT_QUERY", user_id, {"query": sanitized, "tools_used": result["tools_used"]})
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Agent query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# === Evaluation Endpoint ===

@app.post("/evaluate")
async def evaluate(req: EvalRequest, user: User = Depends(require_auth)):
    """Evaluate RAG response quality"""
    try:
        from .rag.evaluator import RAGEvaluator
        evaluator = RAGEvaluator(rag_service.bedrock, settings.bedrock_model_id)
        result = evaluator.evaluate(req.question, req.answer, req.contexts)
        return result
    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# === Connector Endpoints ===

class WebSyncRequest(BaseModel):
    base_url: str = "http://host.docker.internal:8000"
    pattern: str = "/post/"
    limit: int = 20
    auth: Optional[Dict] = None  # {"type": "django_admin", "username": "x", "password": "y"}

@app.post("/connectors/web/sync")
async def sync_web(req: WebSyncRequest, user: User = Depends(require_auth)):
    """Sync documents from internal website"""
    if "admin" not in user.groups:
        raise HTTPException(status_code=403, detail="Admin only")
    
    try:
        connector = WebConnector(req.base_url, req.auth)
        
        if req.auth:
            if not connector.authenticate():
                raise HTTPException(status_code=401, detail="Website authentication failed")
        
        pages = connector.fetch_all(req.pattern, req.limit)
        connector.close()
        
        ingested = 0
        for page in pages:
            if page.content and len(page.content) > 50:
                await rag_service.ingest_text(
                    page.content,
                    source=page.url,
                    metadata={"title": page.title, "content_hash": page.content_hash, **page.metadata}
                )
                ingested += 1
        
        audit.log_action(user.user_id, "web_sync", {"base_url": req.base_url, "ingested": ingested})
        return {"synced": ingested, "source": req.base_url, "pages_found": len(pages)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Web sync failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/connectors/sync")
async def sync_connectors(user: User = Depends(require_auth)):
    """Sync documents from external connectors (mock)"""
    if "admin" not in user.groups:
        raise HTTPException(status_code=403, detail="Admin only")
    
    try:
        from .connectors.base import ConnectorRegistry, MockJiraConnector, MockConfluenceConnector
        
        registry = ConnectorRegistry()
        registry.register(MockJiraConnector())
        registry.register(MockConfluenceConnector())
        
        docs = await registry.fetch_all()
        
        # Ingest fetched docs
        ingested = 0
        for doc in docs:
            await rag_service.ingest_text(doc["content"], doc["source"], doc.get("metadata", {}))
            ingested += 1
        
        return {"synced": ingested, "sources": ["jira", "confluence"]}
    except Exception as e:
        logger.error(f"Connector sync failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# === Admin Endpoints ===

@app.get("/audit")
async def get_audit(user: User = Depends(require_auth)):
    if "admin" not in user.groups:
        raise HTTPException(status_code=403, detail="Admin only")
    return {"events": audit.get_recent(100)}

@app.get("/cache/stats")
async def cache_stats(user: User = Depends(require_auth)):
    if "admin" not in user.groups:
        raise HTTPException(status_code=403, detail="Admin only")
    return cache.stats()

@app.get("/usage")
async def get_usage(user: User = Depends(require_auth)):
    """Get token usage and cost estimates"""
    if "admin" in user.groups:
        return {"total": token_tracker.get_usage(), "by_user": dict(token_tracker.usage)}
    return token_tracker.get_usage(user.user_id)

@app.get("/history/{session_id}")
async def get_history(session_id: str):
    """Get conversation history for session"""
    return {"session_id": session_id, "history": memory.get_history(session_id)}

@app.delete("/history/{session_id}")
async def clear_history(session_id: str):
    """Clear conversation history"""
    memory.clear(session_id)
    return {"message": "History cleared", "session_id": session_id}

# === Data Pipeline Endpoints ===

class PipelineJobRequest(BaseModel):
    name: str
    source_type: str  # "web" or "directory"
    source_config: Dict  # {"base_url": "...", "pattern": "...", "auth": {...}}
    schedule: str = "*/5"  # every 5 min

@app.get("/pipeline/jobs")
async def list_pipeline_jobs(user: User = Depends(require_auth)):
    """List all pipeline jobs"""
    if "admin" not in user.groups:
        raise HTTPException(status_code=403, detail="Admin only")
    return {"jobs": pipeline.list_jobs()}

@app.post("/pipeline/jobs")
async def create_pipeline_job(req: PipelineJobRequest, user: User = Depends(require_auth)):
    """Create a scheduled sync job"""
    if "admin" not in user.groups:
        raise HTTPException(status_code=403, detail="Admin only")
    pipeline.add_job(req.name, req.source_type, req.source_config, req.schedule)
    audit.log_action(user.user_id, "pipeline_job_created", {"name": req.name})
    return {"message": f"Job {req.name} created", "schedule": req.schedule}

@app.delete("/pipeline/jobs/{name}")
async def delete_pipeline_job(name: str, user: User = Depends(require_auth)):
    """Delete a pipeline job"""
    if "admin" not in user.groups:
        raise HTTPException(status_code=403, detail="Admin only")
    pipeline.remove_job(name)
    return {"message": f"Job {name} deleted"}

@app.post("/pipeline/jobs/{name}/run")
async def run_pipeline_job(name: str, user: User = Depends(require_auth)):
    """Manually trigger a pipeline job"""
    if "admin" not in user.groups:
        raise HTTPException(status_code=403, detail="Admin only")
    result = await pipeline.run_job(name, rag_service)
    audit.log_action(user.user_id, "pipeline_job_run", result)
    return result

@app.post("/pipeline/run-all")
async def run_all_pipelines(user: User = Depends(require_auth)):
    """Run all enabled pipeline jobs"""
    if "admin" not in user.groups:
        raise HTTPException(status_code=403, detail="Admin only")
    results = await pipeline.run_all_due(rag_service)
    return {"results": results}
