import json
import logging
from typing import List
import boto3
from datetime import datetime
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import BedrockEmbeddings

from .loader import DocumentLoader
from .chunker import Chunker
from .retriever import HybridRetriever, LLMReranker

logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self, weaviate_client, settings):
        self.client = weaviate_client
        self.settings = settings
        self.embeddings = None
        self.bedrock = None
        self.loader = None
        self.chunker = None
        self.retriever = None
        self.reranker = None
        
    async def initialize(self):
        self.bedrock = boto3.client("bedrock-runtime", region_name=self.settings.aws_region)
        
        # Use direct Bedrock embeddings (not langchain wrapper)
        self.embedding_model = self.settings.embedding_model_id
        
        self.loader = DocumentLoader(bedrock_client=self.bedrock)
        self.chunker = Chunker(self.settings.chunk_size, self.settings.chunk_overlap)
        self._ensure_schema()
        
        # Advanced retrieval
        self.retriever = HybridRetriever(self.client, self, self.settings.weaviate_class)
        self.reranker = LLMReranker(self.bedrock, self.settings.bedrock_model_id)
        
        logger.info("RAG service ready (hybrid search + reranking enabled)")
    
    def embed_query(self, text: str) -> list:
        """Embed text using Bedrock Titan"""
        import json
        body = json.dumps({"inputText": text})
        response = self.bedrock.invoke_model(
            modelId=self.embedding_model,
            body=body,
            contentType="application/json",
            accept="application/json"
        )
        result = json.loads(response["body"].read())
        return result["embedding"]
    
    def _ensure_schema(self):
        schema = self.client.schema.get()
        exists = any(c["class"] == self.settings.weaviate_class for c in schema.get("classes", []))
        
        if not exists:
            self.client.schema.create_class({
                "class": self.settings.weaviate_class,
                "vectorizer": "none",
                "properties": [
                    {"name": "content", "dataType": ["text"]},
                    {"name": "source", "dataType": ["string"]},
                    {"name": "chunk_id", "dataType": ["int"]},
                    {"name": "format", "dataType": ["string"]},
                    {"name": "total_chunks", "dataType": ["int"]},
                    {"name": "allowed_groups", "dataType": ["text[]"]},
                    {"name": "uploaded_at", "dataType": ["string"]},
                ]
            })
            logger.info(f"Created Weaviate class: {self.settings.weaviate_class}")
    
    async def process_document(self, file, allowed_groups: List[str] = None) -> dict:
        doc = await self.loader.load(file)
        logger.info(f"Loaded {doc['filename']} ({doc['format']}, {doc['size_bytes']} bytes)")
        
        chunks = self.chunker.chunk(doc["content"], doc)
        logger.info(f"Created {len(chunks)} chunks")
        
        groups = allowed_groups or []
        
        for chunk in chunks:
            vector = self.embed_query(chunk["content"])
            self.client.data_object.create(
                class_name=self.settings.weaviate_class,
                data_object={
                    "content": chunk["content"],
                    "source": chunk["source"],
                    "chunk_id": chunk["chunk_id"],
                    "format": chunk["format"],
                    "total_chunks": chunk["total_chunks"],
                    "allowed_groups": groups,
                    "uploaded_at": datetime.now().isoformat(),
                },
                vector=vector
            )
        
        return {
            "filename": doc["filename"],
            "format": doc["format"],
            "size_bytes": doc["size_bytes"],
            "chunks": len(chunks),
            "allowed_groups": groups,
        }
    
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
        """Query with access control filtering"""
        import re
        
        # Auto-detect source reference in question (e.g., "blog 148", "post 148", "document 148")
        if not source_filter:
            match = re.search(r'(?:blog|post|document|doc|article)\s*(?:#|id\s*)?(\d+)', question, re.I)
            if match:
                source_filter = f"post/{match.group(1)}"
        
        # Build access filter
        groups = user_groups or []
        filters = []
        
        if groups and "admin" not in groups:
            # Filter to docs user can access
            filters.append({
                "operator": "Or",
                "operands": [
                    {"path": ["allowed_groups"], "operator": "IsNull", "valueBoolean": True},
                    {"path": ["allowed_groups"], "operator": "ContainsAny", "valueTextArray": groups}
                ]
            })
        
        # Source filter (e.g., "post/148" to filter to specific doc)
        if source_filter:
            filters.append({
                "path": ["source"],
                "operator": "Like",
                "valueText": f"*{source_filter}*"
            })
        
        # Combine filters
        where_filter = None
        if len(filters) == 1:
            where_filter = filters[0]
        elif len(filters) > 1:
            where_filter = {"operator": "And", "operands": filters}
        
        # Retrieve with filter
        docs = self.retriever.search(
            question, 
            top_k=top_k * 2, 
            alpha=alpha,
            where_filter=where_filter
        )
        
        # Rerank
        if use_rerank and docs:
            docs = self.reranker.rerank(question, docs, top_k=top_k)
        else:
            docs = docs[:top_k]
        
        # Generate with specified model
        context = "\n\n".join([f"[{d['source']}]\n{d['content']}" for d in docs])
        llm_model = model_id or self.settings.bedrock_model_id
        answer = self._generate(question, context, llm_model, conversation_history)
        
        sources = [
            {
                "source": d["source"],
                "format": d["format"],
                "relevance": d.get("rerank_score", d.get("relevance", 0)),
            }
            for d in docs
        ]
        
        return {
            "answer": answer,
            "sources": sources,
            "question": question,
            "search_type": search_type,
            "reranked": use_rerank,
        }
    
    def _generate(self, question: str, context: str, model_id: str = None, history: str = None) -> str:
        history_section = f"\nPrevious conversation:\n{history}\n" if history else ""
        
        prompt = f"""Answer based on the context below. Cite sources when possible.
{history_section}
Context:
{context}

Question: {question}

Answer:"""
        
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1000,
            "temperature": 0.1
        })
        
        response = self.bedrock.invoke_model(modelId=model_id or self.settings.bedrock_model_id, body=body)
        return json.loads(response["body"].read())["content"][0]["text"]
    
    async def ingest_text(self, content: str, source: str, metadata: dict = None):
        """Ingest raw text (for connectors)"""
        chunks = self.chunker.chunk(content, {"filename": source, "format": "text"})
        
        for chunk in chunks:
            vector = self.embed_query(chunk["content"])
            self.client.data_object.create(
                class_name=self.settings.weaviate_class,
                data_object={
                    "content": chunk["content"],
                    "source": source,
                    "chunk_id": chunk["chunk_id"],
                    "format": "text",
                    "total_chunks": chunk["total_chunks"],
                    "allowed_groups": [],
                },
                vector=vector
            )
    
    async def list_documents(self) -> dict:
        # Get documents with upload time
        result = (
            self.client.query
            .get(self.settings.weaviate_class, ["source", "uploaded_at"])
            .with_limit(1000)
            .do()
        )
        
        docs_data = result.get("data", {}).get("Get", {}).get(self.settings.weaviate_class, [])
        
        # Aggregate by source
        doc_map = {}
        for d in docs_data:
            src = d.get("source", "unknown")
            if src not in doc_map:
                doc_map[src] = {"source": src, "chunks": 0, "uploaded_at": d.get("uploaded_at")}
            doc_map[src]["chunks"] += 1
        
        return {"documents": list(doc_map.values())}
    
    async def delete_document(self, source: str) -> dict:
        """Delete all chunks for a document"""
        result = self.client.batch.delete_objects(
            class_name=self.settings.weaviate_class,
            where={"path": ["source"], "operator": "Equal", "valueText": source}
        )
        
        deleted = result.get("results", {}).get("successful", 0)
        return {"deleted": deleted, "source": source}
