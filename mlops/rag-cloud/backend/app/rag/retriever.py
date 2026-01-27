"""Advanced retrieval: hybrid search + reranking"""
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

class HybridRetriever:
    """Combines vector search + BM25 keyword search"""
    
    def __init__(self, weaviate_client, rag_service, class_name: str):
        self.client = weaviate_client
        self.rag_service = rag_service  # For embed_query
        self.class_name = class_name
    
    def search(self, query: str, top_k: int = 5, alpha: float = 0.5, where_filter: dict = None) -> List[Dict]:
        """
        Hybrid search combining vector and keyword (BM25).
        alpha: 0 = pure keyword, 1 = pure vector, 0.5 = balanced
        """
        q_vector = self.rag_service.embed_query(query)
        
        search = (
            self.client.query
            .get(self.class_name, ["content", "source", "chunk_id", "format"])
            .with_hybrid(query=query, vector=q_vector, alpha=alpha)
            .with_limit(top_k)
            .with_additional(["score"])
        )
        
        if where_filter:
            search = search.with_where(where_filter)
        
        result = search.do()
        
        docs = result.get("data", {}).get("Get", {}).get(self.class_name, [])
        
        return [
            {
                "content": d["content"],
                "source": d["source"],
                "chunk_id": d["chunk_id"],
                "format": d.get("format", "unknown"),
                "relevance": round(float(d["_additional"]["score"]) * 100, 1),
            }
            for d in docs
        ]
    
    def vector_search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Pure vector similarity search"""
        q_vector = self.rag_service.embed_query(query)
        
        result = (
            self.client.query
            .get(self.class_name, ["content", "source", "chunk_id", "format"])
            .with_near_vector({"vector": q_vector})
            .with_limit(top_k)
            .with_additional(["distance"])
            .do()
        )
        
        docs = result.get("data", {}).get("Get", {}).get(self.class_name, [])
        
        return [
            {
                "content": d["content"],
                "source": d["source"],
                "chunk_id": d["chunk_id"],
                "format": d.get("format", "unknown"),
                "score": 1 - d["_additional"]["distance"],
            }
            for d in docs
        ]
    
    def keyword_search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Pure BM25 keyword search"""
        result = (
            self.client.query
            .get(self.class_name, ["content", "source", "chunk_id", "format"])
            .with_bm25(query=query)
            .with_limit(top_k)
            .with_additional(["score"])
            .do()
        )
        
        docs = result.get("data", {}).get("Get", {}).get(self.class_name, [])
        
        return [
            {
                "content": d["content"],
                "source": d["source"],
                "chunk_id": d["chunk_id"],
                "format": d.get("format", "unknown"),
                "score": d["_additional"]["score"],
            }
            for d in docs
        ]


class LLMReranker:
    """Rerank results using LLM scoring"""
    
    def __init__(self, bedrock_client, model_id: str):
        self.bedrock = bedrock_client
        self.model_id = model_id
    
    def rerank(self, query: str, docs: List[Dict], top_k: int = 5) -> List[Dict]:
        """Rerank documents by relevance to query using LLM"""
        import json
        
        if not docs:
            return []
        
        # Build prompt for scoring
        doc_list = "\n".join([f"[{i}] {d['content'][:500]}" for i, d in enumerate(docs)])
        
        prompt = f"""Rate each document's relevance to the query (0-10).
Return JSON array of scores in order.

Query: {query}

Documents:
{doc_list}

Return only JSON array like [8, 5, 9, 3, 7]:"""
        
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 100,
            "temperature": 0
        })
        
        response = self.bedrock.invoke_model(modelId=self.model_id, body=body)
        result = json.loads(response["body"].read())["content"][0]["text"]
        
        try:
            scores = json.loads(result.strip())
            for i, doc in enumerate(docs):
                doc["rerank_score"] = scores[i] if i < len(scores) else 0
            
            reranked = sorted(docs, key=lambda x: x.get("rerank_score", 0), reverse=True)
            return reranked[:top_k]
        except:
            logger.warning("Reranking failed, returning original order")
            return docs[:top_k]
