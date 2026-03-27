"""RAG tool — search Weaviate knowledge base (reused from platform-health-agent).

Connects to the same Weaviate instance running via platform-health-agent's Docker Compose.
Uses AWS Bedrock Titan Embed V2 for query embedding.
"""

import json
import time
import logging

import boto3
import weaviate
import weaviate.classes.query
from pydantic import BaseModel

from config import (
    WEAVIATE_URL, BEDROCK_EMBED_MODEL_ID, EMBED_DIMENSIONS,
    AWS_REGION, AWS_PROFILE,
)

logger = logging.getLogger("tools.rag")


class SearchResult(BaseModel):
    """Structured output from RAG search."""
    query: str
    results: list[dict]
    sources: list[str]
    success: bool
    latency_ms: int
    message: str = ""


def _get_weaviate_client() -> weaviate.WeaviateClient:
    """Connect to Weaviate, handling Docker vs local hostname."""
    url = WEAVIATE_URL
    host = url.replace("http://", "").replace("https://", "").split(":")[0]
    port = int(url.split(":")[-1]) if ":" in url.split("//")[-1] else 8080

    if host in ("localhost", "127.0.0.1"):
        return weaviate.connect_to_local(host=host, port=port)
    else:
        # Docker DNS name (e.g., "vectordb") — use URL-based connection
        return weaviate.connect_to_custom(
            http_host=host, http_port=port, http_secure=False,
            grpc_host=host, grpc_port=50051, grpc_secure=False,
        )


def _embed_query(text: str) -> list[float]:
    """Embed a query string using Bedrock Titan Embed V2."""
    session = boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
    bedrock = session.client("bedrock-runtime")
    body = json.dumps({
        "inputText": text,
        "dimensions": EMBED_DIMENSIONS,
        "normalize": True,
    })
    response = bedrock.invoke_model(modelId=BEDROCK_EMBED_MODEL_ID, body=body)
    return json.loads(response["body"].read())["embedding"]


async def rag_search(query: str, top_k: int = 5) -> SearchResult:
    """Search the knowledge base for relevant documents.

    ALWAYS use this tool first before taking any action. It provides context
    from past incidents, runbooks, architecture docs, and technical blog posts.

    Args:
        query: Natural language search query about platform health topics
        top_k: Number of results to return (default 5)

    Returns:
        SearchResult with relevant chunks, source attribution, and relevance scores
    """
    start = time.time()
    logger.info(f"rag_search: query='{query}', top_k={top_k}")

    try:
        query_vector = _embed_query(query)

        client = _get_weaviate_client()
        try:
            collection = client.collections.get("DocumentChunk")
            wv_results = collection.query.near_vector(
                near_vector=query_vector,
                limit=top_k,
                return_properties=["content", "title", "source_type", "source", "url", "chunk_index"],
                return_metadata=weaviate.classes.query.MetadataQuery(distance=True),
            )
        finally:
            client.close()

        results = []
        sources = set()
        for obj in wv_results.objects:
            props = obj.properties
            score = round(1.0 - (obj.metadata.distance or 0.0), 4)
            results.append({
                "content": props.get("content", ""),
                "title": props.get("title", ""),
                "source_type": props.get("source_type", ""),
                "source": props.get("source", ""),
                "url": props.get("url", ""),
                "chunk_index": props.get("chunk_index", 0),
                "score": score,
            })
            sources.add(props.get("title", "unknown"))

        latency_ms = int((time.time() - start) * 1000)
        logger.info(f"rag_search: found {len(results)} results in {latency_ms}ms")
        return SearchResult(
            query=query,
            results=results,
            sources=sorted(sources),
            success=True,
            latency_ms=latency_ms,
            message=f"Found {len(results)} relevant chunks",
        )

    except Exception as e:
        latency_ms = int((time.time() - start) * 1000)
        logger.error(f"rag_search failed: {e}")
        return SearchResult(
            query=query,
            results=[],
            sources=[],
            success=False,
            latency_ms=latency_ms,
            message=f"RAG search failed: {str(e)}",
        )


def format_context_for_llm(search_result: SearchResult) -> str:
    """Format RAG results into a context string for the LLM."""
    if not search_result.results:
        return "No relevant documents found in the knowledge base."

    parts = []
    for i, r in enumerate(search_result.results, 1):
        parts.append(
            f"[Source {i}: {r['title']} ({r['source_type']}) — relevance: {r['score']}]\n"
            f"{r['content']}\n"
        )
    return "\n---\n".join(parts)
