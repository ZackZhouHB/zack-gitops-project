import weaviate
import json
import time
import logging
from typing import List, Dict, Any
import boto3
from botocore.exceptions import ClientError
import asyncio

logger = logging.getLogger(__name__)

class WeaviateService:
    def __init__(self, config):
        self.config = config
        self.client = None
        self.bedrock_client = None
        self.settings = {
            "embedding_model": "all-MiniLM-L6-v2",
            "chunk_size": 512,
            "chunk_overlap": 100,
            "chunking_method": "recursive"
        }
        self._connect_services()
        self._ensure_schema()
    
    def _connect_services(self):
        try:
            self.client = weaviate.Client(
                url=f"http://{self.config.WEAVIATE_HOST}:{self.config.WEAVIATE_PORT}",
                timeout_config=(5, 15)
            )
            logger.info("✅ Weaviate client created successfully")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Weaviate: {e}")
            self.client = None

        try:
            self.bedrock_client = boto3.client('bedrock-runtime', region_name=self.config.AWS_REGION)
            logger.info("✅ Connected to Bedrock successfully")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Bedrock: {e}")
            self.bedrock_client = None
    
    def _ensure_schema(self):
        try:
            if not self.client:
                logger.warning("⚠️  Weaviate client not available, skipping schema check")
                return
            schema = self.client.schema.get()
            document_class_exists = any(cls['class'] == 'Document' for cls in schema.get('classes', []))
            if not document_class_exists:
                document_class = {
                    "class": "Document",
                    "properties": [
                        {"name": "filename", "dataType": ["text"]},
                        {"name": "content", "dataType": ["text"]},
                        {"name": "metadata", "dataType": ["text"]}
                    ]
                }
                self.client.schema.create_class(document_class)
                logger.info("✅ Created Document class in Weaviate")
            else:
                logger.info("✅ Document class already exists in Weaviate")
        except Exception as e:
            logger.error(f"❌ Error ensuring schema: {e}")
    
    def check_connection(self) -> bool:
        try:
            if self.client is None: return False
            self.client.schema.get()
            return True
        except Exception as e:
            logger.error(f"Weaviate connection check failed: {e}")
            return False
    
    def check_bedrock_connection(self) -> bool:
        return self.bedrock_client is not None

    def index_document(self, filename: str, content: str, metadata: Dict[str, Any] = None) -> bool:
        try:
            if not self.client: return False
            existing = self.client.query.get("Document", ["filename"]).with_where({"path": ["filename"], "operator": "Equal", "valueText": filename}).with_additional(["id"]).do()
            if "data" in existing and "Get" in existing["data"] and "Document" in existing["data"]["Get"]:
                for doc in existing["data"]["Get"]["Document"]:
                    self.client.data_object.delete(doc["_additional"]["id"], class_name="Document")
            doc_object = {"filename": filename, "content": content, "metadata": json.dumps(metadata or {})}
            self.client.data_object.create(data_object=doc_object, class_name="Document")
            logger.info(f"✅ Indexed document: {filename}")
            return True
        except Exception as e:
            logger.error(f"❌ Error indexing document {filename}: {e}")
            return False
    
    def search_documents(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        try:
            if not self.client: return []
            result = self.client.query.get("Document", ["filename", "content", "metadata"]).with_near_text({"concepts": [query]}).with_limit(top_k).with_additional(["certainty"]).do()
            documents = []
            if "data" in result and "Get" in result["data"] and "Document" in result["data"]["Get"]:
                for item in result["data"]["Get"]["Document"]:
                    documents.append({
                        'content': item.get('content', ''),
                        'title': item.get('filename', ''),
                        'uri': f"s3://{self.config.S3_BUCKET_NAME}/documents/{item.get('filename', '')}",
                        'score': item.get('_additional', {}).get('certainty', 0),
                        'type': 'DOCUMENT',
                        'metadata': json.loads(item.get('metadata', '{}'))
                    })
            return documents
        except Exception as e:
            logger.error(f"❌ Error searching with Weaviate: {e}")
            return []

    def _blocking_invoke_model(self, body: str) -> Dict[str, Any]:
        response = self.bedrock_client.invoke_model(
            body=body,
            modelId=self.config.BEDROCK_MODEL_ID,
            accept="application/json",
            contentType="application/json"
        )
        return json.loads(response.get('body').read())

    async def generate_answer(self, question: str, context_docs: List[Dict[str, Any]]) -> str:
        try:
            if not self.bedrock_client: return "Sorry, I couldn't connect to the language model."
            context = "\n---\n".join([f"Document: {doc.get('title', 'Untitled')}\nContent: {doc.get('content', '')}" for doc in context_docs])
            if not context.strip(): return "I don't have any relevant documents to answer your question."

            prompt = f'''Based on the following context documents, please provide a comprehensive answer to the question.\n\nContext Documents:\n{context}\n\nQuestion: {question}\n\nPlease provide a detailed answer based on the context above:'''
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1000, "temperature": 0.1, "top_p": 0.9
            })
            
            response_body = await asyncio.to_thread(self._blocking_invoke_model, body)
            
            if 'content' in response_body and len(response_body['content']) > 0:
                return response_body['content'][0]['text'].strip()
            else:
                return "Sorry, I couldn't generate an answer."
        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            return "Sorry, I couldn't generate an answer."
    
    async def query_with_user_context(self, question: str, top_k: int = 5, user_prefix: str = "") -> Dict[str, Any]:
        start_time = time.time()
        try:
            if not self.check_connection() or not self.check_bedrock_connection():
                return {"question": question, "answer": "A required backend service is unavailable. Please try again later.", "sources": [], "processing_time": 0}

            relevant_docs = self.search_documents(question, top_k)
            answer = await self.generate_answer(question, relevant_docs)

            sources = [{'title': doc.get('title', ''), 'uri': doc.get('uri', ''), 'score': doc.get('score', 0), 'excerpt': doc.get('content', '')[:200] + '...'} for doc in relevant_docs]
            processing_time = time.time() - start_time

            return {"question": question, "answer": answer, "sources": sources, "processing_time": processing_time, "user_prefix": user_prefix}
        except Exception as e:
            logger.error(f"❌ Error in RAG query: {e}")
            return {"question": question, "answer": "Sorry, there was an error processing your question.", "sources": [], "processing_time": time.time() - start_time}
    
    def update_settings(self, new_settings: Dict[str, Any]) -> bool:
        try:
            self.settings.update(new_settings)
            return True
        except Exception as e:
            logger.error(f"Error updating settings: {e}")
            return False
    
    def get_vector_stats(self) -> Dict[str, Any]:
        try:
            if not self.client: return {"indexed_documents": 0, "vector_dimensions": 0, "total_chunks": 0}
            result = self.client.query.aggregate("Document").with_meta_count().do()
            doc_count = result["data"]["Aggregate"]["Document"][0]["meta"]["count"] if "data" in result and "Aggregate" in result["data"] else 0
            dimensions_map = {"all-MiniLM-L6-v2": 384, "all-mpnet-base-v2": 768, "multi-qa-MiniLM-L6-cos-v1": 384}
            return {"indexed_documents": doc_count, "vector_dimensions": dimensions_map.get(self.settings["embedding_model"], 384), "total_chunks": doc_count}
        except Exception as e:
            logger.error(f"Error getting vector stats: {e}")
            return {"indexed_documents": 0, "vector_dimensions": 0, "total_chunks": 0}