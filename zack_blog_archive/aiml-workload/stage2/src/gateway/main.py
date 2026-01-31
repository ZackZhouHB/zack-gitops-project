"""
AI Gateway - Routes between vLLM (K8s), Ollama (WSL), and Bedrock (AWS)
"""
import os
import json
import httpx
import boto3
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
import time

app = FastAPI(title="AI Gateway", version="1.0.0")

# Configuration
VLLM_URL = os.getenv("VLLM_URL", "http://llm-server:8000")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://192.168.50.61:11434")
BEDROCK_REGION = os.getenv("BEDROCK_REGION", "ap-southeast-2")
DEFAULT_BACKEND = os.getenv("DEFAULT_BACKEND", "vllm")

# Backend health status
backend_health = {"vllm": True, "ollama": True, "bedrock": True}

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    model: Optional[str] = None
    backend: Optional[str] = None  # vllm, ollama, bedrock
    max_tokens: Optional[int] = 512
    temperature: Optional[float] = 0.7
    stream: Optional[bool] = False

class ChatResponse(BaseModel):
    content: str
    backend: str
    model: str
    latency_ms: float

# Health check endpoints
@app.get("/health")
async def health():
    return {"status": "ok", "backends": backend_health}

@app.get("/backends")
async def list_backends():
    return {
        "vllm": {"url": VLLM_URL, "healthy": backend_health["vllm"]},
        "ollama": {"url": OLLAMA_URL, "healthy": backend_health["ollama"]},
        "bedrock": {"region": BEDROCK_REGION, "healthy": backend_health["bedrock"]},
    }

# Backend implementations
async def call_vllm(messages: List[Message], model: str, max_tokens: int, temperature: float) -> tuple[str, str]:
    """Call vLLM in K8s cluster"""
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
    """Call Ollama on WSL"""
    model = model or "gpt-oss-gpu:latest"
    prompt = messages[-1].content if messages else ""
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
            }
        )
        response.raise_for_status()
        data = response.json()
        return data.get("response", ""), model

def call_bedrock(messages: List[Message], model: str, max_tokens: int, temperature: float) -> tuple[str, str]:
    """Call AWS Bedrock"""
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

# Main chat endpoint with routing
@app.post("/v1/chat/completions", response_model=ChatResponse)
async def chat(request: ChatRequest):
    backend = request.backend or DEFAULT_BACKEND
    start = time.time()
    
    try:
        if backend == "vllm":
            content, model = await call_vllm(request.messages, request.model, request.max_tokens, request.temperature)
        elif backend == "ollama":
            content, model = await call_ollama(request.messages, request.model, request.max_tokens, request.temperature)
        elif backend == "bedrock":
            content, model = call_bedrock(request.messages, request.model, request.max_tokens, request.temperature)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown backend: {backend}")
        
        backend_health[backend] = True
        latency = (time.time() - start) * 1000
        
        return ChatResponse(content=content, backend=backend, model=model, latency_ms=latency)
    
    except Exception as e:
        backend_health[backend] = False
        # Fallback logic
        if backend == "vllm" and backend_health["bedrock"]:
            try:
                content, model = call_bedrock(request.messages, None, request.max_tokens, request.temperature)
                latency = (time.time() - start) * 1000
                return ChatResponse(content=content, backend="bedrock (fallback)", model=model, latency_ms=latency)
            except:
                pass
        raise HTTPException(status_code=503, detail=f"Backend {backend} failed: {str(e)}")

# Smart routing endpoint
@app.post("/v1/chat/smart")
async def smart_chat(request: ChatRequest):
    """Route based on availability and cost optimization"""
    # Try vLLM first (free, local)
    if backend_health["vllm"]:
        request.backend = "vllm"
        try:
            return await chat(request)
        except:
            pass
    
    # Fallback to Ollama (free, local)
    if backend_health["ollama"]:
        request.backend = "ollama"
        try:
            return await chat(request)
        except:
            pass
    
    # Last resort: Bedrock (paid)
    request.backend = "bedrock"
    return await chat(request)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
