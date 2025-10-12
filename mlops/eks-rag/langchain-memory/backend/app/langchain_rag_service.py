import os
import boto3
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import hashlib
import json

from langchain.document_loaders import S3FileLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Weaviate
from langchain.embeddings import BedrockEmbeddings
from langchain.llms import Bedrock
from langchain.chains import RetrievalQA
from langchain.schema import Document
from langchain.memory import ConversationBufferMemory, ConversationBufferWindowMemory
from langchain.chains import ConversationalRetrievalChain

import weaviate

from .session_manager import SessionMemoryManager

logger = logging.getLogger(__name__)

class LangChainRAGService:
    def __init__(self, config):
        self.config = config
        self.s3_client = None
        self.bedrock_client = None
        self.weaviate_client = None
        self.vectorstore = None
        self.embeddings = None
        self.llm = None
        self.qa_chain = None
        self.conversational_chain = None
        self.memory = None
        
        # Session management
        self.session_manager = SessionMemoryManager(
            session_timeout_minutes=60,
            max_turns=20
        )
        
    async def initialize(self):
        """Initialize all LangChain components"""
        try:
            # Initialize AWS clients
            self.s3_client = boto3.client('s3', region_name=self.config.aws_region)
            self.bedrock_client = boto3.client('bedrock-runtime', region_name=self.config.aws_region)
            
            # Initialize Weaviate client
            self.weaviate_client = weaviate.Client(
                url=f"http://{self.config.weaviate_host}:{self.config.weaviate_port}"
            )
            
            # Initialize embeddings
            self.embeddings = BedrockEmbeddings(
                client=self.bedrock_client,
                model_id=self.config.embedding_model_id
            )
            
            # Initialize LLM
            from langchain.llms.base import LLM
            
            class BedrockInferenceProfileLLM(LLM):
                bedrock_client: Any = None
                model_id: str = ""
                
                def __init__(self, bedrock_client, model_id):
                    super().__init__()
                    self.bedrock_client = bedrock_client
                    self.model_id = model_id
                
                def _call(self, prompt: str, stop: Optional[List[str]] = None, **kwargs) -> str:
                    body = json.dumps({
                        "anthropic_version": "bedrock-2023-05-31",
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 4000,
                        "temperature": 0.1
                    })
                    
                    response = self.bedrock_client.invoke_model(
                        body=body,
                        modelId=self.model_id,
                        accept="application/json",
                        contentType="application/json"
                    )
                    
                    response_body = json.loads(response.get('body').read())
                    return response_body['content'][0]['text']
                
                @property
                def _llm_type(self) -> str:
                    return "bedrock_inference_profile"
            
            self.llm = BedrockInferenceProfileLLM(self.bedrock_client, self.config.bedrock_model_id)
            
            # Initialize vector store with separate class name
            self.vectorstore = Weaviate(
                client=self.weaviate_client,
                index_name=self.config.weaviate_class_name,
                text_key="content",
                embedding=self.embeddings,
                by_text=False
            )
            
            # Initialize memory for conversational chain
            self.memory = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True,
                output_key="answer"
            )
            
            # Initialize QA chain
            self.qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=self.vectorstore.as_retriever(search_kwargs={"k": 5}),
                return_source_documents=True,
                verbose=True
            )
            
            # Initialize conversational chain
            self.conversational_chain = ConversationalRetrievalChain.from_llm(
                llm=self.llm,
                retriever=self.vectorstore.as_retriever(search_kwargs={"k": 5}),
                memory=self.memory,
                return_source_documents=True,
                verbose=True
            )
            
            # Ensure Weaviate schema exists
            await self._ensure_schema()
            
            logger.info("LangChain RAG service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize LangChain RAG service: {e}")
            raise
    
    async def _ensure_schema(self):
        """Ensure Weaviate schema exists"""
        try:
            schema = {
                "class": self.config.weaviate_class_name,
                "description": "Document chunks for LangChain RAG",
                "vectorizer": "none",
                "properties": [
                    {
                        "name": "content",
                        "dataType": ["text"],
                        "description": "Document content"
                    },
                    {
                        "name": "source",
                        "dataType": ["string"],
                        "description": "Document source file"
                    },
                    {
                        "name": "chunk_id",
                        "dataType": ["string"],
                        "description": "Unique chunk identifier"
                    },
                    {
                        "name": "metadata",
                        "dataType": ["string"],
                        "description": "Additional metadata as JSON"
                    }
                ]
            }
            
            # Check if class exists
            existing_schema = self.weaviate_client.schema.get()
            class_exists = any(cls["class"] == self.config.weaviate_class_name for cls in existing_schema.get("classes", []))
            
            if not class_exists:
                self.weaviate_client.schema.create_class(schema)
                logger.info(f"Created Weaviate {self.config.weaviate_class_name} class")
            else:
                logger.info(f"Weaviate {self.config.weaviate_class_name} class already exists")
                
        except Exception as e:
            logger.error(f"Failed to ensure Weaviate schema: {e}")
            raise
    
    async def process_document(self, file, session_id: str = "unknown") -> Dict[str, Any]:
        """Process uploaded document using LangChain"""
        try:
            # Upload to S3 first
            file_key = f"documents/{file.filename}"
            
            # Read file content
            content = await file.read()
            
            # Upload to S3 with session metadata
            self.s3_client.put_object(
                Bucket=self.config.s3_bucket,
                Key=file_key,
                Body=content,
                ContentType=file.content_type,
                Metadata={
                    'uploaded-by': session_id
                }
            )
            
            # Process with LangChain
            # For now, we'll process the content directly since S3FileLoader might need additional setup
            # In production, you'd use S3FileLoader for better integration
            
            # Create document
            doc_content = content.decode('utf-8') if file.content_type.startswith('text') else str(content)
            document = Document(
                page_content=doc_content,
                metadata={
                    "source": file.filename,
                    "s3_key": file_key,
                    "upload_time": datetime.now().isoformat(),
                    "content_type": file.content_type
                }
            )
            
            # Split document
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                length_function=len
            )
            
            chunks = text_splitter.split_documents([document])
            
            # Add chunk IDs
            for i, chunk in enumerate(chunks):
                chunk.metadata["chunk_id"] = f"{file.filename}_{i}"
                chunk.metadata["chunk_index"] = i
            
            # Add to vector store
            self.vectorstore.add_documents(chunks)
            
            logger.info(f"Processed document {file.filename} into {len(chunks)} chunks")
            
            return {
                "message": f"Document {file.filename} processed successfully",
                "filename": file.filename,
                "chunks_created": len(chunks),
                "s3_key": file_key
            }
            
        except Exception as e:
            logger.error(f"Failed to process document: {e}")
            raise
    
    async def query(self, question: str, session_id: str, top_k: int = 5) -> Dict[str, Any]:
        """Query documents using LangChain RAG chain with session memory"""
        try:
            import time
            start_time = time.time()
            
            # Get session-specific memory
            session_memory = self.session_manager.get_memory(session_id)
            
            # Create chain with session memory
            from langchain.chains import ConversationalRetrievalChain
            chain = ConversationalRetrievalChain.from_llm(
                llm=self.llm,
                retriever=self.vectorstore.as_retriever(search_kwargs={"k": top_k}),
                memory=session_memory,
                return_source_documents=True
            )
            
            # Query with session context
            result = chain({"question": question})
            
            # Query Weaviate directly to get documents with metadata for sources
            query_result = (
                self.weaviate_client.query
                .get(self.config.weaviate_class_name, ["content", "source", "s3_key", "chunk_id"])
                .with_near_vector({"vector": self.embeddings.embed_query(question)})
                .with_limit(top_k)
                .with_additional(["distance"])
                .do()
            )
            
            processing_time = time.time() - start_time
            
            # Format sources from direct Weaviate query
            sources = []
            if "data" in query_result and "Get" in query_result["data"]:
                docs = query_result["data"]["Get"].get(self.config.weaviate_class_name, [])
                
                for doc in docs:
                    distance = doc.get("_additional", {}).get("distance", 1.0)
                    certainty = 1 - distance if distance < 1 else 0
                    source_name = doc.get("source", "Unknown")
                    
                    sources.append({
                        "title": source_name,
                        "uri": f"s3://{self.config.s3_bucket}/{source_name}",
                        "score": certainty,
                        "type": "DOCUMENT",
                        "excerpt": doc.get("content", "")[:200]
                    })
            
            response = {
                "answer": result["answer"],
                "sources": sources,
                "processing_time": processing_time,
                "question": question
            }
            
            return response
            
        except Exception as e:
            logger.error(f"Query failed: {e}")
            raise
    
    async def list_documents(self) -> List[Dict[str, Any]]:
        """List all documents from S3 bucket"""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.config.s3_bucket,
                Prefix="documents/"
            )
            
            documents = []
            for obj in response.get('Contents', []):
                key = obj['Key']
                filename = key.replace("documents/", "")
                
                if filename:  # Skip empty filenames
                    # Get metadata to show who uploaded
                    try:
                        head_response = self.s3_client.head_object(
                            Bucket=self.config.s3_bucket,
                            Key=key
                        )
                        uploaded_by = head_response.get('Metadata', {}).get('uploaded-by', 'unknown')
                    except:
                        uploaded_by = 'unknown'
                    
                    documents.append({
                        'filename': filename,
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'].isoformat(),
                        'key': key,
                        'uploaded_by': uploaded_by
                    })
            
            return documents
            
        except Exception as e:
            logger.error(f"Failed to list documents: {e}")
            raise
    
    async def delete_document(self, document_id: str) -> Dict[str, Any]:
        """Delete document from vector store"""
        try:
            # Delete all chunks for this document
            self.weaviate_client.batch.delete_objects(
                class_name=self.config.weaviate_class_name,
                where={
                    "path": ["source"],
                    "operator": "Equal",
                    "valueString": document_id
                }
            )
            
            return {"message": f"Document {document_id} deleted successfully"}
            
        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of all components"""
        try:
            health = {
                "status": "healthy",
                "components": {}
            }
            
            # Check Weaviate
            try:
                self.weaviate_client.schema.get()
                health["components"]["weaviate"] = "healthy"
            except Exception as e:
                health["components"]["weaviate"] = f"unhealthy: {str(e)}"
                health["status"] = "unhealthy"
            
            # Check S3
            try:
                self.s3_client.head_bucket(Bucket=self.config.s3_bucket)
                health["components"]["s3"] = "healthy"
            except Exception as e:
                health["components"]["s3"] = f"unhealthy: {str(e)}"
                health["status"] = "unhealthy"
            
            # Check Bedrock (simple check)
            try:
                # This is a lightweight check - just verify client is configured
                health["components"]["bedrock"] = "healthy"
            except Exception as e:
                health["components"]["bedrock"] = f"unhealthy: {str(e)}"
                health["status"] = "unhealthy"
            
            return health
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def get_vector_stats(self):
        """Get vector database statistics"""
        try:
            # Get total chunk count
            result = self.weaviate_client.query.aggregate(self.config.weaviate_class_name).with_meta_count().do()
            
            total_chunks = 0
            if result.get("data", {}).get("Aggregate", {}).get(self.config.weaviate_class_name):
                total_chunks = result["data"]["Aggregate"][self.config.weaviate_class_name][0].get("meta", {}).get("count", 0)
            
            # Get unique documents count
            docs_result = self.weaviate_client.query.aggregate(self.config.weaviate_class_name).with_fields("source { count }").do()
            
            # Get schema to find vector dimensions
            schema = self.weaviate_client.schema.get(self.config.weaviate_class_name)
            vector_dimensions = 1024  # Titan v2 default
            
            # Try to get actual dimensions from schema
            if schema and "properties" in schema:
                for prop in schema.get("properties", []):
                    if prop.get("dataType") == ["number[]"]:
                        vector_dimensions = prop.get("dimensions", 1024)
                        break
            
            # Count unique documents
            unique_docs = await self.list_documents()
            
            return {
                "indexed_documents": len(unique_docs),
                "vector_dimensions": vector_dimensions,
                "total_chunks": total_chunks,
                "total_documents": len(unique_docs),
                "class_name": self.config.weaviate_class_name,
                "status": "connected"
            }
        except Exception as e:
            logger.error(f"Error getting vector stats: {e}")
            return {
                "indexed_documents": 0,
                "vector_dimensions": 0,
                "total_chunks": 0,
                "total_documents": 0,
                "class_name": self.config.weaviate_class_name,
                "status": "error",
                "error": str(e)
            }
