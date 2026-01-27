"""RAG Service for OpenSearch Serverless"""
import boto3
import json
import hashlib
import logging
import re
from typing import List, Optional
from langchain.text_splitter import RecursiveCharacterTextSplitter

from ..config import settings
from ..db.opensearch_client import OpenSearchClient

logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self):
        self.bedrock = boto3.client('bedrock-runtime', region_name=settings.aws_region)
        self.opensearch = OpenSearchClient(
            endpoint=settings.opensearch_endpoint,
            region=settings.aws_region,
            index_name=settings.opensearch_index
        )
        self.splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        
        # Create index on startup
        if settings.opensearch_endpoint:
            self.opensearch.create_index(dimension=1024)
    
    async def process_document(self, file, allowed_groups: List[str] = None) -> dict:
        """Process uploaded file"""
        content = (await file.read()).decode('utf-8')
        return await self.ingest_text(content, file.filename, allowed_groups=allowed_groups)
    
    def embed_query(self, text: str) -> List[float]:
        """Generate embedding using Bedrock Titan"""
        response = self.bedrock.invoke_model(
            modelId=settings.embedding_model_id,
            body=json.dumps({"inputText": text})
        )
        result = json.loads(response['body'].read())
        return result['embedding']
    
    async def ingest_text(self, content: str, source: str, metadata: dict = None,
                          allowed_groups: List[str] = None):
        """Chunk, embed, and index document"""
        chunks = self.splitter.split_text(content)
        
        for i, chunk in enumerate(chunks):
            embedding = self.embed_query(chunk)
            doc_id = hashlib.md5(f"{source}_{i}".encode()).hexdigest()
            
            self.opensearch.index_document(
                doc_id=doc_id,
                content=chunk,
                source=source,
                chunk_id=str(i),
                embedding=embedding,
                format=metadata.get("format", "text") if metadata else "text",
                allowed_groups=allowed_groups
            )
        
        logger.info(f"Indexed {len(chunks)} chunks from {source}")
        return {"source": source, "chunks": len(chunks)}
    
    async def query(
        self,
        question: str,
        top_k: int = 5,
        search_type: str = "hybrid",
        use_rerank: bool = True,
        alpha: float = 0.5,
        user_groups: List[str] = None,
        model_id: str = None,
        conversation_history: str = None,
        source_filter: str = None
    ) -> dict:
        """Query with hybrid search and LLM generation"""
        
        # Auto-detect source reference
        if not source_filter:
            match = re.search(r'(?:blog|post|document|doc|article)\s*(?:#|id\s*)?(\d+)', question, re.I)
            if match:
                source_filter = f"/post/{match.group(1)}/"
        
        # Generate query embedding
        query_vector = self.embed_query(question)
        
        # Search (pass source_filter to search for better results)
        if search_type == "vector":
            docs = self.opensearch.vector_search(query_vector, top_k * 2, user_groups)
        elif search_type == "keyword":
            docs = self.opensearch.keyword_search(question, top_k * 2, user_groups)
        else:
            docs = self.opensearch.hybrid_search(question, query_vector, top_k * 2, alpha, user_groups, source_filter)
        
        # Rerank with LLM
        if use_rerank and len(docs) > top_k:
            docs = self._rerank(question, docs, top_k)
        else:
            docs = docs[:top_k]
        
        # Generate answer
        context = "\n\n".join([f"[{d['source']}]: {d['content']}" for d in docs])
        
        prompt = f"""Answer based on the context below. If the question asks "what about" or "tell me about" a specific document/blog/post, provide a summary of its main topic and key points.

Context:
{context}

{f"Conversation history:{chr(10)}{conversation_history}{chr(10)}" if conversation_history else ""}
Question: {question}

Answer:"""
        
        response = self.bedrock.invoke_model(
            modelId=model_id or settings.bedrock_model_id,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": prompt}]
            })
        )
        
        result = json.loads(response['body'].read())
        answer = result['content'][0]['text']
        
        return {
            "answer": answer,
            "sources": docs
        }
    
    def _rerank(self, question: str, docs: List[dict], top_k: int) -> List[dict]:
        """Rerank documents using LLM"""
        docs_text = "\n".join([f"{i+1}. {d['content'][:200]}" for i, d in enumerate(docs[:10])])
        
        prompt = f"""Rank these documents by relevance to: "{question}"
Return only the numbers of the top {top_k} most relevant, comma-separated.

Documents:
{docs_text}

Most relevant (numbers only):"""
        
        response = self.bedrock.invoke_model(
            modelId=settings.bedrock_model_id,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 50,
                "messages": [{"role": "user", "content": prompt}]
            })
        )
        
        result = json.loads(response['body'].read())
        ranking_text = result['content'][0]['text']
        
        try:
            indices = [int(x.strip()) - 1 for x in ranking_text.split(',') if x.strip().isdigit()]
            return [docs[i] for i in indices if 0 <= i < len(docs)][:top_k]
        except:
            return docs[:top_k]
    
    def delete_document(self, source: str):
        """Delete document by source"""
        self.opensearch.delete_by_source(source)
        logger.info(f"Deleted {source}")
    
    def list_documents(self) -> List[dict]:
        """List all indexed documents"""
        return self.opensearch.get_sources()
