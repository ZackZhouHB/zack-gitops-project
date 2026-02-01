"""
RAG Enhanced - Production-grade RAG with evaluation
"""
import os
import json
import time
import logging
import httpx
import weaviate
from fastapi import FastAPI, UploadFile, HTTPException, File
from pydantic import BaseModel
from typing import Optional, List
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

from .config import settings
from .chunker import SmartChunker, ChunkStrategy
from .retriever import HybridRetriever, LLMReranker
from .evaluation import RAGEvaluator, TestSuiteBuilder, BASELINE_TEST_CASES
from .loaders import PDFLoader, WordLoader, ExcelLoader, LoadedDocument

logging.basicConfig(level=logging.INFO, format='{"time":"%(asctime)s","level":"%(levelname)s","msg":"%(message)s"}')
logger = logging.getLogger(__name__)

app = FastAPI(title="RAG Enhanced", version="2.0.0")

# Prometheus metrics
RAG_QUERIES = Counter('rag_queries_total', 'Total RAG queries', ['search_type', 'status'])
RAG_LATENCY = Histogram('rag_query_latency_seconds', 'RAG query latency', ['stage'], 
                        buckets=[0.1, 0.5, 1, 2, 5, 10, 30])
DOCS_INDEXED = Counter('rag_documents_indexed_total', 'Documents indexed', ['source_type'])
CHUNKS_CREATED = Counter('rag_chunks_created_total', 'Chunks created', ['strategy'])
EVAL_SCORES = Gauge('rag_evaluation_score', 'Evaluation scores', ['metric'])

# Components
weaviate_client = None
chunker = None
retriever = None
reranker = None
evaluator = None

# Document loaders
pdf_loader = PDFLoader()
word_loader = WordLoader()
excel_loader = ExcelLoader()

# Request/Response models
class QueryRequest(BaseModel):
    question: str
    top_k: Optional[int] = 5
    search_type: Optional[str] = "hybrid"  # vector, keyword, hybrid
    alpha: Optional[float] = 0.5
    use_rerank: Optional[bool] = True
    source_filter: Optional[str] = None

class QueryResponse(BaseModel):
    answer: str
    sources: List[dict]
    search_type: str
    reranked: bool
    latency_ms: float

class EvalRequest(BaseModel):
    test_cases: Optional[List[dict]] = None  # If None, use baseline

class EvalResponse(BaseModel):
    num_cases: int
    avg_faithfulness: float
    avg_relevance: float
    avg_context_precision: float
    avg_overall: float


@app.on_event("startup")
async def startup():
    global weaviate_client, chunker, retriever, reranker, evaluator
    
    weaviate_client = weaviate.Client(settings.weaviate_url)
    _ensure_schema()
    
    chunker = SmartChunker(settings.chunk_size, settings.chunk_overlap)
    retriever = HybridRetriever(weaviate_client, embed_text, settings.weaviate_class)
    reranker = LLMReranker(settings.vllm_url)
    evaluator = RAGEvaluator(settings.vllm_url)
    
    logger.info(f"RAG Enhanced started - LLM: {settings.llm_backend}, Embed: {settings.embed_backend}")


def _ensure_schema():
    """Create Weaviate schema with enhanced fields"""
    schema = weaviate_client.schema.get()
    exists = any(c["class"] == settings.weaviate_class for c in schema.get("classes", []))
    
    if not exists:
        weaviate_client.schema.create_class({
            "class": settings.weaviate_class,
            "vectorizer": "none",
            "properties": [
                {"name": "content", "dataType": ["text"]},
                {"name": "source", "dataType": ["string"]},
                {"name": "source_type", "dataType": ["string"]},
                {"name": "chunk_id", "dataType": ["int"]},
                {"name": "total_chunks", "dataType": ["int"]},
                {"name": "content_type", "dataType": ["string"]},
                {"name": "page_number", "dataType": ["int"]},
                {"name": "section_header", "dataType": ["string"]},
            ],
            "invertedIndexConfig": {"bm25": {"b": 0.75, "k1": 1.2}}
        })
        logger.info(f"Created Weaviate class: {settings.weaviate_class}")


def embed_text(text: str) -> List[float]:
    """Generate embeddings using Ollama"""
    resp = httpx.post(
        f"{settings.ollama_url}/api/embeddings",
        json={"model": settings.embed_model, "prompt": text},
        timeout=30.0
    )
    resp.raise_for_status()
    return resp.json()["embedding"]


def generate_response(question: str, context: str) -> str:
    """Generate answer using vLLM"""
    messages = [
        {"role": "system", "content": "Answer based on the context. Cite sources when possible. If context doesn't contain the answer, say so."},
        {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}
    ]
    resp = httpx.post(
        f"{settings.vllm_url}/v1/chat/completions",
        json={"model": "Qwen/Qwen2.5-3B-Instruct", "messages": messages, "max_tokens": 512},
        timeout=120.0
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


# === API Endpoints ===

@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0", "features": ["hybrid_search", "reranking", "evaluation"]}

@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    strategy: Optional[str] = None
):
    """Upload and index a document with smart chunking"""
    content = await file.read()
    
    # Detect source type from extension
    ext = file.filename.split(".")[-1].lower() if "." in file.filename else "txt"
    
    # Load document based on type
    if ext == "pdf":
        doc = pdf_loader.load(content, file.filename)
        text = doc.content
    elif ext in ("docx", "doc"):
        doc = word_loader.load(content, file.filename)
        text = doc.content
    elif ext in ("xlsx", "xls"):
        doc = excel_loader.load(content, file.filename)
        text = doc.content
    elif ext in ("md", "txt"):
        text = content.decode("utf-8", errors="ignore")
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")
    
    # Chunk with appropriate strategy
    chunk_strategy = ChunkStrategy(strategy) if strategy else None
    chunks = chunker.chunk(text, file.filename, ext, strategy=chunk_strategy)
    
    # Index chunks
    for chunk in chunks:
        vector = embed_text(chunk.content)
        weaviate_client.data_object.create(
            class_name=settings.weaviate_class,
            data_object=chunk.to_dict(),
            vector=vector
        )
    
    DOCS_INDEXED.labels(source_type=ext).inc()
    CHUNKS_CREATED.labels(strategy=chunk_strategy.value if chunk_strategy else "auto").inc(len(chunks))
    
    logger.info(f"Indexed {file.filename}: {len(chunks)} chunks, type={ext}")
    return {"status": "ok", "filename": file.filename, "chunks": len(chunks), "source_type": ext}


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """Query with hybrid search and optional reranking"""
    start = time.time()
    
    try:
        # Search
        search_start = time.time()
        chunks = retriever.search(
            request.question,
            top_k=request.top_k * 2 if request.use_rerank else request.top_k,
            search_type=request.search_type,
            alpha=request.alpha,
            source_filter=request.source_filter
        )
        RAG_LATENCY.labels(stage="search").observe(time.time() - search_start)
        
        if not chunks:
            return QueryResponse(
                answer="No relevant documents found.",
                sources=[],
                search_type=request.search_type,
                reranked=False,
                latency_ms=(time.time() - start) * 1000
            )
        
        # Rerank
        if request.use_rerank:
            rerank_start = time.time()
            chunks = reranker.rerank(request.question, chunks, request.top_k)
            RAG_LATENCY.labels(stage="rerank").observe(time.time() - rerank_start)
        
        # Generate
        gen_start = time.time()
        context = "\n\n".join([f"[{c.source}]: {c.content}" for c in chunks])
        answer = generate_response(request.question, context)
        RAG_LATENCY.labels(stage="generate").observe(time.time() - gen_start)
        
        latency = time.time() - start
        RAG_QUERIES.labels(search_type=request.search_type, status="success").inc()
        RAG_LATENCY.labels(stage="total").observe(latency)
        
        return QueryResponse(
            answer=answer,
            sources=[c.to_dict() for c in chunks],
            search_type=request.search_type,
            reranked=request.use_rerank,
            latency_ms=latency * 1000
        )
    
    except Exception as e:
        RAG_QUERIES.labels(search_type=request.search_type, status="error").inc()
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/evaluate", response_model=EvalResponse)
async def evaluate(request: EvalRequest):
    """Run evaluation on test cases"""
    
    # Use provided test cases or baseline
    if request.test_cases:
        test_cases = request.test_cases
    else:
        # Run baseline test cases through RAG first
        test_cases = []
        for tc in BASELINE_TEST_CASES:
            # Query RAG
            chunks = retriever.search(tc.question, top_k=3, search_type="hybrid")
            context = "\n".join([c.content for c in chunks])
            answer = generate_response(tc.question, context)
            
            test_cases.append({
                "question": tc.question,
                "answer": answer,
                "contexts": [c.content for c in chunks]
            })
    
    # Evaluate
    result = evaluator.evaluate_batch(test_cases)
    
    # Update Prometheus gauges
    EVAL_SCORES.labels(metric="faithfulness").set(result.avg_faithfulness)
    EVAL_SCORES.labels(metric="relevance").set(result.avg_relevance)
    EVAL_SCORES.labels(metric="context_precision").set(result.avg_context_precision)
    EVAL_SCORES.labels(metric="overall").set(result.avg_overall)
    
    logger.info(f"Evaluation complete: overall={result.avg_overall:.2f}")
    
    return EvalResponse(
        num_cases=result.num_cases,
        avg_faithfulness=result.avg_faithfulness,
        avg_relevance=result.avg_relevance,
        avg_context_precision=result.avg_context_precision,
        avg_overall=result.avg_overall
    )


@app.get("/documents")
async def list_documents():
    """List indexed documents"""
    result = (
        weaviate_client.query
        .aggregate(settings.weaviate_class)
        .with_group_by_filter(["source"])
        .with_meta_count()
        .do()
    )
    
    sources = []
    for group in result.get("data", {}).get("Aggregate", {}).get(settings.weaviate_class, []):
        sources.append({
            "source": group.get("groupedBy", {}).get("value"),
            "chunks": group.get("meta", {}).get("count", 0)
        })
    return {"documents": sources}


@app.delete("/documents/{source}")
async def delete_document(source: str):
    """Delete document by source"""
    weaviate_client.batch.delete_objects(
        class_name=settings.weaviate_class,
        where={"path": ["source"], "operator": "Equal", "valueString": source}
    )
    return {"status": "deleted", "source": source}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
