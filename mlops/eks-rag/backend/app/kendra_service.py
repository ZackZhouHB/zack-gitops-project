import boto3
import json
import time
import logging
from typing import List, Dict, Any
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class KendraService:
    def __init__(self, config):
        self.config = config
        self.kendra_client = None
        self.bedrock_client = None
        self._connect_services()
    
    def _connect_services(self):
        """Connect to AWS Kendra and Bedrock"""
        try:
            self.kendra_client = boto3.client(
                'kendra',
                region_name=self.config.AWS_REGION
            )
            self.bedrock_client = boto3.client(
                'bedrock-runtime',
                region_name=self.config.AWS_REGION
            )
            logger.info("Connected to Kendra and Bedrock")
        except Exception as e:
            logger.error(f"Failed to connect to AWS services: {e}")
    
    def check_connection(self) -> bool:
        """Check if Kendra is accessible"""
        try:
            if self.kendra_client is None:
                return False
            self.kendra_client.describe_index(Id=self.config.KENDRA_INDEX_ID)
            return True
        except Exception as e:
            logger.error(f"Kendra connection check failed: {e}")
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
    
    def start_data_source_sync(self) -> str:
        """Start Kendra data source synchronization"""
        try:
            response = self.kendra_client.start_data_source_sync_job(
                Id=self.config.KENDRA_DATA_SOURCE_ID,
                IndexId=self.config.KENDRA_INDEX_ID
            )
            job_id = response['ExecutionId']
            logger.info(f"Started Kendra sync job: {job_id}")
            return job_id
        except Exception as e:
            logger.error(f"Error starting sync job: {e}")
            raise
    
    def get_sync_status(self, job_id: str) -> Dict[str, Any]:
        """Get status of Kendra sync job"""
        try:
            response = self.kendra_client.describe_data_source_sync_job(
                Id=job_id,
                IndexId=self.config.KENDRA_INDEX_ID,
                DataSourceId=self.config.KENDRA_DATA_SOURCE_ID
            )
            return {
                "status": response.get('Status'),
                "start_time": response.get('StartTime'),
                "end_time": response.get('EndTime'),
                "error_message": response.get('ErrorMessage'),
                "documents_added": response.get('Metrics', {}).get('DocumentsAdded', 0),
                "documents_modified": response.get('Metrics', {}).get('DocumentsModified', 0),
                "documents_deleted": response.get('Metrics', {}).get('DocumentsDeleted', 0),
                "documents_failed": response.get('Metrics', {}).get('DocumentsFailed', 0)
            }
        except Exception as e:
            logger.error(f"Error getting sync status: {e}")
            raise
    
    def search_documents(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search documents using Kendra"""
        try:
            response = self.kendra_client.query(
                IndexId=self.config.KENDRA_INDEX_ID,
                QueryText=query,
                PageSize=top_k
            )
            
            documents = []
            
            # Process query results
            for item in response.get('ResultItems', []):
                if item['Type'] in ['DOCUMENT', 'QUESTION_ANSWER']:
                    doc_info = {
                        'content': item.get('DocumentExcerpt', {}).get('Text', ''),
                        'title': item.get('DocumentTitle', {}).get('Text', ''),
                        'uri': item.get('DocumentURI', ''),
                        'score': item.get('ScoreAttributes', {}).get('ScoreConfidence', 0),
                        'type': item.get('Type'),
                        'id': item.get('Id', '')
                    }
                    
                    # Extract additional attributes
                    if 'DocumentAttributes' in item:
                        for attr in item['DocumentAttributes']:
                            key = attr.get('Key', '')
                            value = attr.get('Value', {})
                            if key and value:
                                doc_info[f'attr_{key}'] = list(value.values())[0] if value else ''
                    
                    documents.append(doc_info)
                    logger.info(f"Retrieved doc: {doc_info['title']}, score: {doc_info['score']}")
            
            logger.info(f"Kendra search returned {len(documents)} documents")
            return documents
            
        except Exception as e:
            logger.error(f"Error searching with Kendra: {e}")
            return []
    
    def generate_answer(self, question: str, context_docs: List[Dict[str, Any]]) -> str:
        """Generate answer using Bedrock with Kendra context"""
        try:
            if not self.bedrock_client:
                logger.error("No Bedrock client available")
                return "Sorry, I couldn't connect to the language model."
            
            # Prepare context from Kendra results
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
            
            logger.info(f"Context prepared with {len(context_docs)} documents, context length: {len(context)}")
            
            if not context.strip():
                logger.warning("No context available for question")
                return "I don't have any relevant documents to answer your question."
            
            # Prepare prompt for Bedrock
            prompt = f"""Based on the following context documents, please provide a comprehensive answer to the question. Include specific details from the documents and cite the sources when possible.

Context Documents:
{context}

Question: {question}

Please provide a detailed answer based on the context above:"""

            # Call Bedrock with Claude messages format
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 1000,
                "temperature": 0.1,
                "top_p": 0.9
            })
            
            logger.info(f"Calling Bedrock with model: {self.config.BEDROCK_MODEL_ID}")
            logger.info(f"Request body length: {len(body)}")
            logger.info(f"Request body preview: {body[:200]}...")
            
            response = self.bedrock_client.invoke_model(
                body=body,
                modelId=self.config.BEDROCK_MODEL_ID,
                accept="application/json",
                contentType="application/json"
            )
            
            response_body = json.loads(response.get('body').read())
            logger.info(f"Bedrock response received")
            
            # Extract answer from Claude response format
            if 'content' in response_body and len(response_body['content']) > 0:
                answer = response_body['content'][0]['text'].strip()
                logger.info(f"Generated answer length: {len(answer)}")
            elif 'outputs' in response_body and len(response_body['outputs']) > 0:
                answer = response_body['outputs'][0]['text'].strip()
                logger.info(f"Generated answer length: {len(answer)}")
            else:
                logger.error(f"Unexpected Bedrock response format: {response_body}")
                answer = "Sorry, I couldn't generate an answer."
            
            return answer
            
        except ClientError as e:
            logger.error(f"Bedrock API error: {e}")
            return "Sorry, there was an error with the language model."
        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            return "Sorry, I couldn't generate an answer."
    
    def start_data_source_sync(self, user_prefix: str = "") -> str:
        """Start Kendra data source synchronization with user context"""
        try:
            response = self.kendra_client.start_data_source_sync_job(
                Id=self.config.KENDRA_DATA_SOURCE_ID,
                IndexId=self.config.KENDRA_INDEX_ID
            )
            job_id = response['ExecutionId']
            logger.info(f"Started Kendra sync job: {job_id} for user: {user_prefix}")
            return job_id
        except Exception as e:
            logger.error(f"Error starting sync job: {e}")
            raise
    
    def search_documents_with_user_context(self, query: str, top_k: int = 5, user_prefix: str = "") -> List[Dict[str, Any]]:
        """Search all shared documents using Kendra (no user filtering)"""
        try:
            response = self.kendra_client.query(
                IndexId=self.config.KENDRA_INDEX_ID,
                QueryText=query,
                PageSize=top_k
            )
            
            documents = []
            
            # Process query results - all documents are shared, no filtering needed
            for item in response.get('ResultItems', []):
                if item['Type'] in ['DOCUMENT', 'QUESTION_ANSWER']:
                    doc_info = {
                        'content': item.get('DocumentExcerpt', {}).get('Text', ''),
                        'title': item.get('DocumentTitle', {}).get('Text', ''),
                        'uri': item.get('DocumentURI', ''),
                        'score': item.get('ScoreAttributes', {}).get('ScoreConfidence', 0),
                        'type': item.get('Type'),
                        'id': item.get('Id', '')
                    }
                    
                    # Extract additional attributes
                    if 'DocumentAttributes' in item:
                        for attr in item['DocumentAttributes']:
                            key = attr.get('Key', '')
                            value = attr.get('Value', {})
                            if key and value:
                                doc_info[f'attr_{key}'] = list(value.values())[0] if value else ''
                    
                    documents.append(doc_info)
                    logger.info(f"Retrieved shared doc: {doc_info['title']}, score: {doc_info['score']}")
            
            logger.info(f"Kendra search returned {len(documents)} shared documents for user {user_prefix}")
            return documents
            
        except Exception as e:
            logger.error(f"Error searching with Kendra: {e}")
            return []
    
    def query_with_user_context(self, question: str, top_k: int = 5, user_prefix: str = "") -> Dict[str, Any]:
        """Main RAG query function using Kendra + Bedrock with user context"""
        start_time = time.time()
        
        try:
            # Search for relevant documents using Kendra with user context
            relevant_docs = self.search_documents_with_user_context(question, top_k, user_prefix)
            
            # Generate answer using Bedrock
            answer = self.generate_answer(question, relevant_docs)
            
            # Prepare sources with Kendra metadata
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
                "user_prefix": user_prefix
            }
            
        except Exception as e:
            logger.error(f"Error in RAG query: {e}")
            processing_time = time.time() - start_time
            
            return {
                "question": question,
                "answer": "Sorry, there was an error processing your question.",
                "sources": [],
                "processing_time": processing_time,
                "user_prefix": user_prefix
            }
