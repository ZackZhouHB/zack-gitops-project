"""
RAG Backend - Adapted for local K8s with vLLM
Simplified version focusing on core RAG functionality
"""
import os
import json
import logging
import httpx
import weaviate
from fastapi import FastAPI, UploadFile, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

from .config import settings

logging.basicConfig(level=logging.INFO, format='{"time":"%(asctime)s","level":"%(levelname)s","msg":"%(message)s"}')
logger = logging.getLogger(__name__)

app = FastAPI(title="RAG Backend", version="1.0.0")

# Prometheus metrics
RAG_QUERIES = Counter('rag_queries_total', 'Total RAG queries', ['status'])
RAG_LATENCY = Histogram('rag_query_latency_seconds', 'RAG query latency', buckets=[0.5, 1, 2, 5, 10, 30])
DOCS_INDEXED = Counter('rag_documents_indexed_total', 'Documents indexed')

# Weaviate client
weaviate_client = None

class QueryRequest(BaseModel):
    question: str
    top_k: Optional[int] = 3

class QueryResponse(BaseModel):
    answer: str
    sources: List[dict]
    latency_ms: float

@app.on_event("startup")
async def startup():
    global weaviate_client
    weaviate_client = weaviate.Client(settings.weaviate_url)
    _ensure_schema()
    logger.info(f"Connected to Weaviate at {settings.weaviate_url}")
    logger.info(f"LLM backend: {settings.llm_backend}, Embed backend: {settings.embed_backend}")

def _ensure_schema():
    schema = weaviate_client.schema.get()
    exists = any(c["class"] == settings.weaviate_class for c in schema.get("classes", []))
    if not exists:
        weaviate_client.schema.create_class({
            "class": settings.weaviate_class,
            "vectorizer": "none",
            "properties": [
                {"name": "content", "dataType": ["text"]},
                {"name": "source", "dataType": ["string"]},
                {"name": "chunk_id", "dataType": ["int"]},
            ]
        })
        logger.info(f"Created Weaviate class: {settings.weaviate_class}")

# Embedding functions
def embed_text(text: str) -> List[float]:
    """Generate embeddings using configured backend"""
    if settings.embed_backend == "ollama":
        return _embed_ollama(text)
    else:
        return _embed_bedrock(text)

def _embed_ollama(text: str) -> List[float]:
    """Embed using Ollama"""
    resp = httpx.post(
        f"{settings.ollama_url}/api/embeddings",
        json={"model": settings.embed_model, "prompt": text},
        timeout=30.0
    )
    resp.raise_for_status()
    return resp.json()["embedding"]

def _embed_bedrock(text: str) -> List[float]:
    """Embed using Bedrock Titan"""
    import boto3
    client = boto3.client("bedrock-runtime", region_name=settings.aws_region)
    resp = client.invoke_model(
        modelId=settings.bedrock_embed_model,
        body=json.dumps({"inputText": text}),
        contentType="application/json"
    )
    return json.loads(resp["body"].read())["embedding"]

# LLM functions
def generate_response(prompt: str, context: str) -> str:
    """Generate response using configured LLM backend"""
    if settings.llm_backend == "vllm":
        return _generate_vllm(prompt, context)
    elif settings.llm_backend == "ollama":
        return _generate_ollama(prompt, context)
    else:
        return _generate_bedrock(prompt, context)

def _generate_vllm(prompt: str, context: str) -> str:
    """Generate using vLLM"""
    messages = [
        {"role": "system", "content": "You are a helpful assistant. Answer based on the provided context. If the context doesn't contain the answer, say so."},
        {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {prompt}"}
    ]
    resp = httpx.post(
        f"{settings.vllm_url}/v1/chat/completions",
        json={"model": "Qwen/Qwen2.5-3B-Instruct", "messages": messages, "max_tokens": 512},
        timeout=120.0
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]

def _generate_ollama(prompt: str, context: str) -> str:
    """Generate using Ollama"""
    full_prompt = f"Context:\n{context}\n\nQuestion: {prompt}\n\nAnswer based on the context above:"
    resp = httpx.post(
        f"{settings.ollama_url}/api/generate",
        json={"model": "qwen3-coder:latest", "prompt": full_prompt, "stream": False},
        timeout=120.0
    )
    resp.raise_for_status()
    return resp.json()["response"]

def _generate_bedrock(prompt: str, context: str) -> str:
    """Generate using Bedrock Claude"""
    import boto3
    client = boto3.client("bedrock-runtime", region_name=settings.aws_region)
    messages = [{"role": "user", "content": f"Context:\n{context}\n\nQuestion: {prompt}"}]
    resp = client.invoke_model(
        modelId=settings.bedrock_model_id,
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 512,
            "messages": messages
        })
    )
    return json.loads(resp["body"].read())["content"][0]["text"]

# Simple chunking
def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """Split text into overlapping chunks"""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks

# API Endpoints
@app.get("/health")
async def health():
    return {"status": "ok", "llm": settings.llm_backend, "embed": settings.embed_backend}

@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/upload")
async def upload_document(file: UploadFile):
    """Upload and index a document"""
    content = await file.read()
    text = content.decode("utf-8", errors="ignore")
    
    chunks = chunk_text(text, settings.chunk_size, settings.chunk_overlap)
    logger.info(f"Processing {file.filename}: {len(chunks)} chunks")
    
    for i, chunk in enumerate(chunks):
        vector = embed_text(chunk)
        weaviate_client.data_object.create(
            class_name=settings.weaviate_class,
            data_object={"content": chunk, "source": file.filename, "chunk_id": i},
            vector=vector
        )
    
    DOCS_INDEXED.inc()
    logger.info(f"Indexed {file.filename} with {len(chunks)} chunks")
    return {"status": "ok", "filename": file.filename, "chunks": len(chunks)}

@app.get("/documents")
async def list_documents():
    """List indexed documents"""
    result = weaviate_client.query.aggregate(settings.weaviate_class).with_group_by_filter(["source"]).with_meta_count().do()
    sources = []
    for group in result.get("data", {}).get("Aggregate", {}).get(settings.weaviate_class, []):
        sources.append({
            "source": group.get("groupedBy", {}).get("value"),
            "chunks": group.get("meta", {}).get("count", 0)
        })
    return {"documents": sources}

@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """Query the RAG system"""
    import time
    start = time.time()
    
    try:
        # Embed query
        query_vector = embed_text(request.question)
        
        # Search Weaviate
        result = weaviate_client.query.get(
            settings.weaviate_class, ["content", "source", "chunk_id"]
        ).with_near_vector({"vector": query_vector}).with_limit(request.top_k).do()
        
        docs = result.get("data", {}).get("Get", {}).get(settings.weaviate_class, [])
        
        if not docs:
            RAG_QUERIES.labels(status="no_results").inc()
            return QueryResponse(answer="No relevant documents found.", sources=[], latency_ms=(time.time()-start)*1000)
        
        # Build context
        context = "\n\n".join([f"[{d['source']}]: {d['content']}" for d in docs])
        
        # Generate response
        answer = generate_response(request.question, context)
        
        latency = time.time() - start
        RAG_QUERIES.labels(status="success").inc()
        RAG_LATENCY.observe(latency)
        
        sources = [{"source": d["source"], "chunk_id": d["chunk_id"]} for d in docs]
        
        logger.info(f"Query completed: {latency:.2f}s, {len(docs)} sources")
        return QueryResponse(answer=answer, sources=sources, latency_ms=latency*1000)
    
    except Exception as e:
        RAG_QUERIES.labels(status="error").inc()
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/documents/{source}")
async def delete_document(source: str):
    """Delete a document by source name"""
    weaviate_client.batch.delete_objects(
        class_name=settings.weaviate_class,
        where={"path": ["source"], "operator": "Equal", "valueString": source}
    )
    return {"status": "deleted", "source": source}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
