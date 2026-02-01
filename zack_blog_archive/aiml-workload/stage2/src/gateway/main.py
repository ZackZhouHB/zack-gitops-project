"""
AI Gateway - Routes between vLLM (K8s), Ollama (WSL), and Bedrock (AWS)
With Prometheus metrics for observability
Now includes RAG proxy routes
"""
import os
import json
import logging
import httpx
import boto3
from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from pydantic import BaseModel
from typing import Optional, List
import time
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

# Structured logging
logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","msg":"%(message)s"}'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Gateway", version="1.2.0")

# Configuration
VLLM_URL = os.getenv("VLLM_URL", "http://llm-server:8000")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://192.168.50.61:11434")
BEDROCK_REGION = os.getenv("BEDROCK_REGION", "ap-southeast-2")
DEFAULT_BACKEND = os.getenv("DEFAULT_BACKEND", "vllm")
RAG_BACKEND_URL = os.getenv("RAG_BACKEND_URL", "http://rag-backend:8001")

# Prometheus Metrics
REQUEST_COUNT = Counter(
    'ai_gateway_requests_total', 
    'Total requests to AI Gateway',
    ['backend', 'status']
)
REQUEST_LATENCY = Histogram(
    'ai_gateway_request_latency_seconds',
    'Request latency in seconds',
    ['backend'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0]
)
BACKEND_HEALTH = Gauge(
    'ai_gateway_backend_healthy',
    'Backend health status (1=healthy, 0=unhealthy)',
    ['backend']
)
TOKENS_GENERATED = Counter(
    'ai_gateway_tokens_generated_total',
    'Approximate tokens generated',
    ['backend']
)

# Initialize health gauges
backend_health = {"vllm": True, "ollama": True, "bedrock": True, "rag": True}
for backend, healthy in backend_health.items():
    BACKEND_HEALTH.labels(backend=backend).set(1 if healthy else 0)

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    model: Optional[str] = None
    backend: Optional[str] = None
    max_tokens: Optional[int] = 512
    temperature: Optional[float] = 0.7
    stream: Optional[bool] = False

class ChatResponse(BaseModel):
    content: str
    backend: str
    model: str
    latency_ms: float

class RAGQueryRequest(BaseModel):
    question: str
    top_k: Optional[int] = 3

# Metrics endpoint for Prometheus scraping
@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/health")
async def health():
    return {"status": "ok", "backends": backend_health}

@app.get("/backends")
async def list_backends():
    return {
        "vllm": {"url": VLLM_URL, "healthy": backend_health["vllm"]},
        "ollama": {"url": OLLAMA_URL, "healthy": backend_health["ollama"]},
        "bedrock": {"region": BEDROCK_REGION, "healthy": backend_health["bedrock"]},
        "rag": {"url": RAG_BACKEND_URL, "healthy": backend_health["rag"]},
    }

def update_health(backend: str, healthy: bool):
    backend_health[backend] = healthy
    BACKEND_HEALTH.labels(backend=backend).set(1 if healthy else 0)

def estimate_tokens(text: str) -> int:
    return len(text) // 4

async def call_vllm(messages: List[Message], model: str, max_tokens: int, temperature: float) -> tuple[str, str]:
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{VLLM_URL}/v1/chat/completions",
            json={
                "model": model or "Qwen/Qwen2.5-3B-Instruct",
                "messages": [m.dict() for m in messages],
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"], data["model"]

async def call_ollama(messages: List[Message], model: str, max_tokens: int, temperature: float) -> tuple[str, str]:
    model = model or "gpt-oss-gpu:latest"
    prompt = messages[-1].content if messages else ""
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False}
        )
        response.raise_for_status()
        data = response.json()
        return data.get("response", ""), model

def call_bedrock(messages: List[Message], model: str, max_tokens: int, temperature: float) -> tuple[str, str]:
    model = model or "anthropic.claude-3-haiku-20240307-v1:0"
    client = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "messages": [{"role": m.role, "content": m.content} for m in messages],
        "temperature": temperature,
    }
    response = client.invoke_model(modelId=model, body=json.dumps(body))
    result = json.loads(response["body"].read())
    return result["content"][0]["text"], model

@app.post("/v1/chat/completions", response_model=ChatResponse)
async def chat(request: ChatRequest):
    backend = request.backend or DEFAULT_BACKEND
    start = time.time()
    
    logger.info(f"Request received: backend={backend}, messages={len(request.messages)}")
    
    try:
        if backend == "vllm":
            content, model = await call_vllm(request.messages, request.model, request.max_tokens, request.temperature)
        elif backend == "ollama":
            content, model = await call_ollama(request.messages, request.model, request.max_tokens, request.temperature)
        elif backend == "bedrock":
            content, model = call_bedrock(request.messages, request.model, request.max_tokens, request.temperature)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown backend: {backend}")
        
        latency = time.time() - start
        REQUEST_COUNT.labels(backend=backend, status="success").inc()
        REQUEST_LATENCY.labels(backend=backend).observe(latency)
        TOKENS_GENERATED.labels(backend=backend).inc(estimate_tokens(content))
        update_health(backend, True)
        
        logger.info(f"Request completed: backend={backend}, latency={latency:.2f}s")
        return ChatResponse(content=content, backend=backend, model=model, latency_ms=latency * 1000)
    
    except Exception as e:
        latency = time.time() - start
        REQUEST_COUNT.labels(backend=backend, status="error").inc()
        REQUEST_LATENCY.labels(backend=backend).observe(latency)
        update_health(backend, False)
        logger.error(f"Request failed: backend={backend}, error={str(e)}")
        
        if backend == "vllm" and backend_health["bedrock"]:
            try:
                content, model = call_bedrock(request.messages, None, request.max_tokens, request.temperature)
                latency = time.time() - start
                REQUEST_COUNT.labels(backend="bedrock", status="success").inc()
                return ChatResponse(content=content, backend="bedrock (fallback)", model=model, latency_ms=latency * 1000)
            except:
                pass
        raise HTTPException(status_code=503, detail=f"Backend {backend} failed: {str(e)}")

@app.post("/v1/chat/smart")
async def smart_chat(request: ChatRequest):
    if backend_health["vllm"]:
        request.backend = "vllm"
        try:
            return await chat(request)
        except:
            pass
    if backend_health["ollama"]:
        request.backend = "ollama"
        try:
            return await chat(request)
        except:
            pass
    request.backend = "bedrock"
    return await chat(request)

# ============ RAG Routes ============

@app.post("/v1/rag/query")
async def rag_query(request: RAGQueryRequest):
    """Query the RAG system"""
    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{RAG_BACKEND_URL}/query",
                json={"question": request.question, "top_k": request.top_k}
            )
            response.raise_for_status()
            data = response.json()
        
        latency = time.time() - start
        REQUEST_COUNT.labels(backend="rag", status="success").inc()
        REQUEST_LATENCY.labels(backend="rag").observe(latency)
        update_health("rag", True)
        logger.info(f"RAG query completed: latency={latency:.2f}s")
        return data
    except Exception as e:
        REQUEST_COUNT.labels(backend="rag", status="error").inc()
        update_health("rag", False)
        logger.error(f"RAG query failed: {e}")
        raise HTTPException(status_code=503, detail=str(e))

@app.post("/v1/rag/upload")
async def rag_upload(file: UploadFile = File(...)):
    """Upload document to RAG"""
    start = time.time()
    try:
        content = await file.read()
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{RAG_BACKEND_URL}/upload",
                files={"file": (file.filename, content, file.content_type)}
            )
            response.raise_for_status()
            data = response.json()
        
        latency = time.time() - start
        REQUEST_COUNT.labels(backend="rag", status="success").inc()
        update_health("rag", True)
        logger.info(f"RAG upload completed: {file.filename}, latency={latency:.2f}s")
        return data
    except Exception as e:
        REQUEST_COUNT.labels(backend="rag", status="error").inc()
        update_health("rag", False)
        logger.error(f"RAG upload failed: {e}")
        raise HTTPException(status_code=503, detail=str(e))

@app.get("/v1/rag/documents")
async def rag_documents():
    """List RAG documents"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{RAG_BACKEND_URL}/documents")
            response.raise_for_status()
            return response.json()
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
