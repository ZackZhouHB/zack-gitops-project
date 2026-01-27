"""OpenSearch Serverless client for vector search"""
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class OpenSearchClient:
    """OpenSearch Serverless client with vector search support"""
    
    def __init__(self, endpoint: str, region: str = "us-east-1", index_name: str = "documents"):
        self.endpoint = endpoint.replace("https://", "")
        self.region = region
        self.index_name = index_name
        
        # AWS SigV4 auth
        credentials = boto3.Session().get_credentials()
        self.auth = AWS4Auth(
            credentials.access_key,
            credentials.secret_key,
            region,
            'aoss',
            session_token=credentials.token
        )
        
        self.client = OpenSearch(
            hosts=[{'host': self.endpoint, 'port': 443}],
            http_auth=self.auth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            timeout=30
        )
    
    def create_index(self, dimension: int = 1024):
        """Create index with vector field mapping"""
        if self.client.indices.exists(index=self.index_name):
            logger.info(f"Index {self.index_name} already exists")
            return
        
        mapping = {
            "settings": {
                "index": {
                    "knn": True
                }
            },
            "mappings": {
                "properties": {
                    "content": {"type": "text"},
                    "source": {"type": "keyword"},
                    "chunk_id": {"type": "keyword"},
                    "format": {"type": "keyword"},
                    "allowed_groups": {"type": "keyword"},
                    "embedding": {
                        "type": "knn_vector",
                        "dimension": dimension,
                        "method": {
                            "name": "hnsw",
                            "space_type": "cosinesimil",
                            "engine": "faiss"
                        }
                    }
                }
            }
        }
        
        self.client.indices.create(index=self.index_name, body=mapping)
        logger.info(f"Created index {self.index_name}")
    
    def index_document(self, doc_id: str, content: str, source: str, chunk_id: str,
                       embedding: List[float], format: str = "text",
                       allowed_groups: List[str] = None):
        """Index a document with vector embedding"""
        body = {
            "content": content,
            "source": source,
            "chunk_id": chunk_id,
            "format": format,
            "embedding": embedding,
            "allowed_groups": allowed_groups or []
        }
        
        self.client.index(index=self.index_name, body=body)  # No custom ID for Serverless
    
    def hybrid_search(self, query_text: str, query_vector: List[float], 
                      top_k: int = 5, alpha: float = 0.5,
                      filter_groups: List[str] = None,
                      source_filter: str = None) -> List[Dict]:
        """Hybrid search combining vector (kNN) and keyword (BM25)"""
        
        # Build filter
        filters = []
        if filter_groups:
            filters.append({
                "bool": {
                    "should": [
                        {"terms": {"allowed_groups": filter_groups}},
                        {"bool": {"must_not": {"exists": {"field": "allowed_groups"}}}}
                    ]
                }
            })
        if source_filter:
            filters.append({"wildcard": {"source": f"*{source_filter}*"}})
        
        # Vector search (kNN)
        knn_query = {
            "knn": {
                "embedding": {
                    "vector": query_vector,
                    "k": top_k * 2
                }
            }
        }
        
        # Keyword search (BM25)
        text_query = {
            "match": {
                "content": {
                    "query": query_text,
                    "boost": 1.0
                }
            }
        }
        
        # Combine with alpha weighting
        # OpenSearch Serverless doesn't support script_score, use knn with filter
        if alpha >= 1.0:
            # Pure vector
            query = knn_query
        elif alpha <= 0.0:
            # Pure keyword
            query = {"bool": {"must": [text_query]}}
        else:
            # Hybrid: use knn with text filter boost
            query = {
                "bool": {
                    "must": [knn_query],
                    "should": [text_query]
                }
            }
        
        body = {
            "size": top_k,
            "query": query,
            "_source": ["content", "source", "chunk_id", "format"]
        }
        
        if filters:
            body["query"] = {"bool": {"must": [query], "filter": filters}}
        
        response = self.client.search(index=self.index_name, body=body)
        
        results = []
        for hit in response["hits"]["hits"]:
            results.append({
                "content": hit["_source"]["content"],
                "source": hit["_source"]["source"],
                "chunk_id": hit["_source"]["chunk_id"],
                "format": hit["_source"].get("format", "text"),
                "relevance": round(hit["_score"] * 10, 1)  # Normalize score
            })
        
        return results
    
    def vector_search(self, query_vector: List[float], top_k: int = 5,
                      filter_groups: List[str] = None) -> List[Dict]:
        """Pure vector search"""
        return self.hybrid_search("", query_vector, top_k, alpha=1.0, filter_groups=filter_groups)
    
    def keyword_search(self, query_text: str, top_k: int = 5,
                       filter_groups: List[str] = None) -> List[Dict]:
        """Pure keyword search"""
        return self.hybrid_search(query_text, [0]*1024, top_k, alpha=0.0, filter_groups=filter_groups)
    
    def delete_by_source(self, source: str):
        """Delete all documents from a source"""
        self.client.delete_by_query(
            index=self.index_name,
            body={"query": {"term": {"source": source}}}
        )
    
    def get_sources(self) -> List[Dict]:
        """Get unique sources with document counts"""
        body = {
            "size": 0,
            "aggs": {
                "sources": {
                    "terms": {"field": "source", "size": 1000}
                }
            }
        }
        
        response = self.client.search(index=self.index_name, body=body)
        
        return [
            {"source": bucket["key"], "chunks": bucket["doc_count"]}
            for bucket in response["aggregations"]["sources"]["buckets"]
        ]
