"""Hybrid Retriever - Vector + BM25 + Reranking"""
import logging
import json
import httpx
from typing import List, Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class RetrievedChunk:
    content: str
    source: str
    chunk_id: int
    score: float
    source_type: Optional[str] = None
    rerank_score: Optional[float] = None
    
    def to_dict(self) -> Dict:
        return {
            "content": self.content,
            "source": self.source,
            "chunk_id": self.chunk_id,
            "score": self.score,
            "source_type": self.source_type,
            "rerank_score": self.rerank_score
        }


class HybridRetriever:
    """
    Combines vector search + BM25 keyword search.
    Weaviate 1.24+ supports native hybrid search.
    """
    
    def __init__(self, weaviate_client, embed_fn, class_name: str = "Document"):
        self.client = weaviate_client
        self.embed_fn = embed_fn  # Function to embed query
        self.class_name = class_name
    
    def search(
        self,
        query: str,
        top_k: int = 10,
        search_type: str = "hybrid",  # vector, keyword, hybrid
        alpha: float = 0.5,  # 0=keyword, 1=vector
        source_filter: Optional[str] = None,
        content_type_filter: Optional[str] = None
    ) -> List[RetrievedChunk]:
        """
        Search with configurable strategy.
        """
        # Build filter
        where_filter = self._build_filter(source_filter, content_type_filter)
        
        if search_type == "vector":
            return self._vector_search(query, top_k, where_filter)
        elif search_type == "keyword":
            return self._keyword_search(query, top_k, where_filter)
        else:
            return self._hybrid_search(query, top_k, alpha, where_filter)
    
    def _vector_search(self, query: str, top_k: int, where_filter: Optional[Dict]) -> List[RetrievedChunk]:
        """Pure vector similarity search"""
        vector = self.embed_fn(query)
        
        search = (
            self.client.query
            .get(self.class_name, ["content", "source", "chunk_id", "source_type"])
            .with_near_vector({"vector": vector})
            .with_limit(top_k)
            .with_additional(["distance"])
        )
        
        if where_filter:
            search = search.with_where(where_filter)
        
        result = search.do()
        return self._parse_results(result, score_key="distance", invert_score=True)
    
    def _keyword_search(self, query: str, top_k: int, where_filter: Optional[Dict]) -> List[RetrievedChunk]:
        """BM25 keyword search"""
        search = (
            self.client.query
            .get(self.class_name, ["content", "source", "chunk_id", "source_type"])
            .with_bm25(query=query)
            .with_limit(top_k)
            .with_additional(["score"])
        )
        
        if where_filter:
            search = search.with_where(where_filter)
        
        result = search.do()
        return self._parse_results(result, score_key="score")
    
    def _hybrid_search(self, query: str, top_k: int, alpha: float, where_filter: Optional[Dict]) -> List[RetrievedChunk]:
        """Hybrid search combining vector + BM25"""
        vector = self.embed_fn(query)
        
        search = (
            self.client.query
            .get(self.class_name, ["content", "source", "chunk_id", "source_type"])
            .with_hybrid(query=query, vector=vector, alpha=alpha)
            .with_limit(top_k)
            .with_additional(["score"])
        )
        
        if where_filter:
            search = search.with_where(where_filter)
        
        result = search.do()
        return self._parse_results(result, score_key="score")
    
    def _build_filter(self, source_filter: Optional[str], content_type_filter: Optional[str]) -> Optional[Dict]:
        """Build Weaviate where filter"""
        filters = []
        
        if source_filter:
            filters.append({
                "path": ["source"],
                "operator": "Like",
                "valueText": f"*{source_filter}*"
            })
        
        if content_type_filter:
            filters.append({
                "path": ["source_type"],
                "operator": "Equal",
                "valueText": content_type_filter
            })
        
        if not filters:
            return None
        if len(filters) == 1:
            return filters[0]
        return {"operator": "And", "operands": filters}
    
    def _parse_results(self, result: Dict, score_key: str, invert_score: bool = False) -> List[RetrievedChunk]:
        """Parse Weaviate results into RetrievedChunk objects"""
        docs = result.get("data", {}).get("Get", {}).get(self.class_name, [])
        
        chunks = []
        for d in docs:
            score = d.get("_additional", {}).get(score_key, 0)
            if invert_score:
                score = 1 - float(score)  # Convert distance to similarity
            
            chunks.append(RetrievedChunk(
                content=d.get("content", ""),
                source=d.get("source", "unknown"),
                chunk_id=d.get("chunk_id", 0),
                score=float(score),
                source_type=d.get("source_type")
            ))
        
        return chunks


class LLMReranker:
    """Rerank retrieved chunks using LLM scoring"""
    
    def __init__(self, vllm_url: str = None, backend: str = "vllm"):
        self.vllm_url = vllm_url or "http://llm-server:8000"
        self.backend = backend
    
    def rerank(
        self,
        query: str,
        chunks: List[RetrievedChunk],
        top_k: int = 5
    ) -> List[RetrievedChunk]:
        """Rerank chunks by relevance to query"""
        if not chunks:
            return []
        
        # Build scoring prompt
        doc_list = "\n".join([
            f"[{i}] {c.content[:300]}..." 
            for i, c in enumerate(chunks[:10])  # Limit to 10 for reranking
        ])
        
        prompt = f"""Rate each document's relevance to the query (0-10).
Return ONLY a JSON array of scores in order.

QUERY: {query}

DOCUMENTS:
{doc_list}

Return JSON array like [8, 5, 9, 3, 7]:"""

        try:
            resp = httpx.post(
                f"{self.vllm_url}/v1/chat/completions",
                json={
                    "model": "Qwen/Qwen2.5-3B-Instruct",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 100,
                    "temperature": 0
                },
                timeout=30.0
            )
            resp.raise_for_status()
            response = resp.json()["choices"][0]["message"]["content"]
            
            scores = json.loads(response.strip())
            
            for i, chunk in enumerate(chunks[:len(scores)]):
                chunk.rerank_score = scores[i] if i < len(scores) else 0
            
            reranked = sorted(chunks, key=lambda x: x.rerank_score or 0, reverse=True)
            return reranked[:top_k]
            
        except Exception as e:
            logger.warning(f"Reranking failed: {e}, returning original order")
            return chunks[:top_k]
