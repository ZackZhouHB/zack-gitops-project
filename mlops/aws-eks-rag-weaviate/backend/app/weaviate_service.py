import weaviate
import json
import time
import logging
from typing import List, Dict, Any
import boto3
from botocore.exceptions import ClientError

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
        """Connect to Weaviate and Bedrock with comprehensive error handling"""
        # Try to connect to Weaviate first
        self.client = None  # Default to None
        self.bedrock_client = None  # Default to None

        try:
            # Test connection before creating client
            test_url = f"http://{self.config.WEAVIATE_HOST}:{self.config.WEAVIATE_PORT}/v1/.well-known/ready"
            import urllib.request
            import urllib.error

            # Quick connection test with short timeout
            logger.info(f"🔄 Testing Weaviate connection to {test_url}")
            req = urllib.request.Request(test_url)
            response = urllib.request.urlopen(req, timeout=5)
            if response.status == 200 or response.status == 204:
                logger.info(f"✅ Weaviate connection test successful: {response.status}")

                # Create Weaviate client with minimal initialization to avoid automatic checks
                try:
                    # Create client without automatic schema validation
                    self.client = weaviate.Client(
                        url=f"http://{self.config.WEAVIATE_HOST}:{self.config.WEAVIATE_PORT}",
                        timeout_config=(5, 15)  # (connect timeout, read timeout)
                    )
                    logger.info("✅ Weaviate client created successfully")
                except Exception as client_e:
                    logger.warning(f"⚠️  Weaviate client creation failed: {client_e}")
                    self.client = None
            else:
                logger.warning(f"⚠️  Weaviate returned unexpected status: {response.status}")
                self.client = None
        except Exception as e:
            logger.error(f"❌ Failed to connect to Weaviate: {e}")
            self.client = None

        # Connect to Bedrock
        try:
            self.bedrock_client = boto3.client(
                'bedrock-runtime',
                region_name=self.config.AWS_REGION
            )
            logger.info("✅ Connected to Bedrock successfully")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Bedrock: {e}")
            self.bedrock_client = None
    
    def _ensure_schema(self):
        """Ensure Document class exists in Weaviate"""
        try:
            if not self.client:
                logger.warning("⚠️  Weaviate client not available, skipping schema check")
                return

            # Check if Document class exists
            schema = self.client.schema.get()
            document_class_exists = any(cls['class'] == 'Document' for cls in schema.get('classes', []))

            if not document_class_exists:
                document_class = {
                    "class": "Document",
                    "description": "A document for RAG",
                    "properties": [
                        {
                            "name": "filename",
                            "dataType": ["text"],
                            "description": "The filename of the document"
                        },
                        {
                            "name": "content",
                            "dataType": ["text"],
                            "description": "The content of the document"
                        },
                        {
                            "name": "metadata",
                            "dataType": ["text"],
                            "description": "Metadata about the document"
                        }
                    ]
                }
                self.client.schema.create_class(document_class)
                logger.info("✅ Created Document class in Weaviate")
            else:
                logger.info("✅ Document class already exists in Weaviate")
        except Exception as e:
            logger.error(f"❌ Error ensuring schema: {e}")
    
    def check_connection(self) -> bool:
        """Check if Weaviate is accessible"""
        try:
            if self.client is None:
                return False
            self.client.schema.get()
            return True
        except Exception as e:
            logger.error(f"Weaviate connection check failed: {e}")
            return False
    
    def check_bedrock_connection(self) -> bool:
        """Check if Bedrock is accessible"""
        try:
            if self.bedrock_client is None:
                return False
            return True
        except Exception as e:
            logger.error(f"Bedrock connection check failed: {e}")
            return False
    
    def index_document(self, filename: str, content: str, metadata: Dict[str, Any] = None) -> bool:
        """Index a document in Weaviate (replaces existing if found)"""
        try:
            # Check if Weaviate client is available
            if not self.client:
                logger.warning(f"⚠️  Weaviate client not available, cannot index document: {filename}")
                return False

            # First, check if document already exists and delete it
            existing = (
                self.client.query
                .get("Document", ["filename"])
                .with_where({
                    "path": ["filename"],
                    "operator": "Equal",
                    "valueText": filename
                })
                .with_additional(["id"])
                .do()
            )

            # Delete existing documents with same filename
            if "data" in existing and "Get" in existing["data"] and "Document" in existing["data"]["Get"]:
                for doc in existing["data"]["Get"]["Document"]:
                    doc_id = doc["_additional"]["id"]
                    self.client.data_object.delete(doc_id, class_name="Document")
                    logger.info(f"Deleted existing document: {filename} (ID: {doc_id})")

            # Create new document
            doc_object = {
                "filename": filename,
                "content": content,
                "metadata": json.dumps(metadata or {})
            }

            self.client.data_object.create(
                data_object=doc_object,
                class_name="Document"
            )
            logger.info(f"✅ Indexed document: {filename}")
            return True
        except Exception as e:
            logger.error(f"❌ Error indexing document {filename}: {e}")
            return False
    
    def search_documents(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search documents using Weaviate with fallback"""
        try:
            if not self.client:
                logger.warning("⚠️  Weaviate client not available, returning empty results")
                return []

            result = (
                self.client.query
                .get("Document", ["filename", "content", "metadata"])
                .with_near_text({"concepts": [query]})
                .with_limit(top_k)
                .with_additional(["certainty"])
                .do()
            )

            documents = []
            if "data" in result and "Get" in result["data"] and "Document" in result["data"]["Get"]:
                for item in result["data"]["Get"]["Document"]:
                    doc_info = {
                        'content': item.get('content', ''),
                        'title': item.get('filename', ''),
                        'uri': f"s3://{self.config.S3_BUCKET_NAME}/documents/{item.get('filename', '')}",
                        'score': item.get('_additional', {}).get('certainty', 0),
                        'type': 'DOCUMENT',
                        'metadata': json.loads(item.get('metadata', '{}'))
                    }
                    documents.append(doc_info)

            logger.info(f"✅ Weaviate search returned {len(documents)} documents")
            return documents

        except Exception as e:
            logger.error(f"❌ Error searching with Weaviate: {e}")
            return []
    
    def generate_answer(self, question: str, context_docs: List[Dict[str, Any]]) -> str:
        """Generate answer using Bedrock with Weaviate context"""
        try:
            if not self.bedrock_client:
                logger.error("❌ No Bedrock client available")
                return "Sorry, I couldn't connect to the language model."

            # Prepare context from Weaviate results
            context_parts = []
            for doc in context_docs:
                title = doc.get('title', 'Untitled')
                content = doc.get('content', '')
                uri = doc.get('uri', '')

                context_part = f"Document: {title}\n"
                if uri:
                    context_part += f"Source: {uri}\n"
                context_part += f"Content: {content}\n"
                context_parts.append(context_part)

            context = "\n---\n".join(context_parts)

            if not context.strip():
                # Improved error message for when Weaviate is unavailable
                if not self.client:
                    return "I'm currently unable to search the document database. Please try again later or contact support if the issue persists."
                else:
                    return "I don't have any relevant documents to answer your question."

            prompt = f"""Based on the following context documents, please provide a comprehensive answer to the question.

Context Documents:
{context}

Question: {question}

Please provide a detailed answer based on the context above:"""

            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1000,
                "temperature": 0.1,
                "top_p": 0.9
            })
            
            response = self.bedrock_client.invoke_model(
                body=body,
                modelId=self.config.BEDROCK_MODEL_ID,
                accept="application/json",
                contentType="application/json"
            )
            
            response_body = json.loads(response.get('body').read())
            
            if 'content' in response_body and len(response_body['content']) > 0:
                return response_body['content'][0]['text'].strip()
            else:
                return "Sorry, I couldn't generate an answer."
            
        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            return "Sorry, I couldn't generate an answer."
    
    def query_with_user_context(self, question: str, top_k: int = 5, user_prefix: str = "") -> Dict[str, Any]:
        """Main RAG query function using Weaviate + Bedrock with improved error handling"""
        start_time = time.time()

        try:
            # Check service availability first
            weaviate_available = self.check_connection()
            bedrock_available = self.check_bedrock_connection()

            if not weaviate_available:
                logger.warning("⚠️  Weaviate unavailable, using fallback mode")
                processing_time = time.time() - start_time
                return {
                    "question": question,
                    "answer": "I'm currently unable to search the document database. Please try again later or contact support if the issue persists.",
                    "sources": [],
                    "processing_time": processing_time,
                    "user_prefix": user_prefix,
                    "service_status": {
                        "weaviate": weaviate_available,
                        "bedrock": bedrock_available
                    }
                }

            if not bedrock_available:
                logger.warning("⚠️  Bedrock unavailable")
                processing_time = time.time() - start_time
                return {
                    "question": question,
                    "answer": "I'm currently unable to generate answers using the language model. Please try again later.",
                    "sources": [],
                    "processing_time": processing_time,
                    "user_prefix": user_prefix,
                    "service_status": {
                        "weaviate": weaviate_available,
                        "bedrock": bedrock_available
                    }
                }

            # Normal processing
            relevant_docs = self.search_documents(question, top_k)
            answer = self.generate_answer(question, relevant_docs)

            sources = []
            for doc in relevant_docs:
                source_info = {
                    'title': doc.get('title', 'Untitled'),
                    'uri': doc.get('uri', ''),
                    'score': doc.get('score', 0),
                    'type': doc.get('type', ''),
                    'excerpt': doc.get('content', '')[:200] + '...' if len(doc.get('content', '')) > 200 else doc.get('content', '')
                }
                sources.append(source_info)

            processing_time = time.time() - start_time

            return {
                "question": question,
                "answer": answer,
                "sources": sources,
                "processing_time": processing_time,
                "user_prefix": user_prefix,
                "service_status": {
                    "weaviate": weaviate_available,
                    "bedrock": bedrock_available
                }
            }

        except Exception as e:
            logger.error(f"❌ Error in RAG query: {e}")
            processing_time = time.time() - start_time

            return {
                "question": question,
                "answer": "Sorry, there was an error processing your question. Please try again.",
                "sources": [],
                "processing_time": processing_time,
                "user_prefix": user_prefix,
                "service_status": {
                    "weaviate": self.check_connection(),
                    "bedrock": self.check_bedrock_connection()
                }
            }
    
    def update_settings(self, new_settings: Dict[str, Any]) -> bool:
        """Update embedding and chunking settings"""
        try:
            self.settings.update(new_settings)
            logger.info(f"Updated settings: {self.settings}")
            return True
        except Exception as e:
            logger.error(f"Error updating settings: {e}")
            return False
    
    def get_vector_stats(self) -> Dict[str, Any]:
        """Get vector database statistics"""
        try:
            if not self.client:
                return {"indexed_documents": 0, "vector_dimensions": 0, "total_chunks": 0}
            
            # Get document count
            result = self.client.query.aggregate("Document").with_meta_count().do()
            doc_count = 0
            if "data" in result and "Aggregate" in result["data"] and "Document" in result["data"]["Aggregate"]:
                doc_count = result["data"]["Aggregate"]["Document"][0]["meta"]["count"]
            
            # Get embedding dimensions based on current model
            dimensions_map = {
                "all-MiniLM-L6-v2": 384,
                "all-mpnet-base-v2": 768,
                "multi-qa-MiniLM-L6-cos-v1": 384
            }
            
            return {
                "indexed_documents": doc_count,
                "vector_dimensions": dimensions_map.get(self.settings["embedding_model"], 384),
                "total_chunks": doc_count  # Simplified - each doc is one chunk for now
            }
        except Exception as e:
            logger.error(f"Error getting vector stats: {e}")
            return {"indexed_documents": 0, "vector_dimensions": 0, "total_chunks": 0}
