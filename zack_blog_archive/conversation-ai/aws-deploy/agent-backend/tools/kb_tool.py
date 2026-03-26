"""Bedrock Knowledge Base search tool.

Replaces the local Weaviate-based rag_tool.py.
Uses the Bedrock Agent Runtime Retrieve API to search the Knowledge Base.
The KB handles chunking, embedding, and indexing automatically.
"""
import logging
from dataclasses import dataclass, field

import boto3

from config import AWS_REGION, KNOWLEDGE_BASE_ID

logger = logging.getLogger("kb_tool")


@dataclass
class KBSearchResult:
    """Single result from Knowledge Base search."""
    content: str
    title: str
    source_uri: str
    source_type: str  # s3, web, confluence
    score: float


@dataclass 
class KBSearchResponse:
    """Response from KB search."""
    success: bool
    results: list[KBSearchResult] = field(default_factory=list)
    message: str = ""


def _classify_source_type(uri: str) -> str:
    """Determine source type from URI."""
    if not uri:
        return "unknown"
    if uri.startswith("s3://"):
        return "s3"
    if "atlassian.net" in uri or "confluence" in uri.lower():
        return "confluence"
    if uri.startswith("http"):
        return "web"
    return "file"


def _extract_title(uri: str, content: str) -> str:
    """Extract a readable title from the source URI or content."""
    if not uri:
        return content[:60] + "..." if len(content) > 60 else content
    
    # S3: use filename
    if uri.startswith("s3://"):
        parts = uri.split("/")
        return parts[-1] if parts else uri
    
    # Web/Confluence: use last path segment or domain
    if uri.startswith("http"):
        from urllib.parse import urlparse
        parsed = urlparse(uri)
        path = parsed.path.rstrip("/")
        if path:
            segment = path.split("/")[-1]
            # Clean up URL-encoded characters and extensions
            segment = segment.replace("-", " ").replace("_", " ")
            if "." in segment:
                segment = segment.rsplit(".", 1)[0]
            return segment.title() if segment else parsed.netloc
        return parsed.netloc
    
    return uri[:60]


async def kb_search(query: str, top_k: int = 5) -> KBSearchResponse:
    """Search the Bedrock Knowledge Base.
    
    Args:
        query: Natural language search query
        top_k: Number of results to return (default 5)
    
    Returns:
        KBSearchResponse with results including content, title, source, and score
    """
    if not KNOWLEDGE_BASE_ID:
        return KBSearchResponse(
            success=False,
            message="KNOWLEDGE_BASE_ID not configured. Set it in environment variables."
        )
    
    try:
        client = boto3.client("bedrock-agent-runtime", region_name=AWS_REGION)
        
        response = client.retrieve(
            knowledgeBaseId=KNOWLEDGE_BASE_ID,
            retrievalQuery={"text": query},
            retrievalConfiguration={
                "vectorSearchConfiguration": {
                    "numberOfResults": top_k
                }
            }
        )
        
        results = []
        for item in response.get("retrievalResults", []):
            content = item.get("content", {}).get("text", "")
            location = item.get("location", {})
            score = item.get("score", 0.0)
            
            # Extract URI based on location type
            loc_type = location.get("type", "")
            uri = ""
            if loc_type == "S3":
                uri = location.get("s3Location", {}).get("uri", "")
            elif loc_type == "WEB":
                uri = location.get("webLocation", {}).get("url", "")
            elif loc_type == "CONFLUENCE":
                uri = location.get("confluenceLocation", {}).get("url", "")
            
            source_type = _classify_source_type(uri)
            title = _extract_title(uri, content)
            
            results.append(KBSearchResult(
                content=content,
                title=title,
                source_uri=uri,
                source_type=source_type,
                score=score,
            ))
        
        if not results:
            return KBSearchResponse(
                success=True,
                results=[],
                message="No relevant documents found in the knowledge base."
            )
        
        return KBSearchResponse(success=True, results=results)
        
    except Exception as e:
        logger.error(f"KB search failed: {e}")
        return KBSearchResponse(success=False, message=f"Knowledge base search error: {str(e)}")


def format_context_for_llm(response: KBSearchResponse) -> str:
    """Format KB search results for the LLM prompt.
    
    Produces the same format as the local rag_tool for consistency:
    [Source N: Title (type) — relevance: X.XX]
    Content...
    """
    if not response.success or not response.results:
        return response.message
    
    parts = []
    for i, r in enumerate(response.results, 1):
        header = f"[Source {i}: {r.title} ({r.source_type}) — relevance: {r.score:.2f}]"
        parts.append(f"{header}\n{r.content}")
    
    return "\n\n---\n\n".join(parts)
