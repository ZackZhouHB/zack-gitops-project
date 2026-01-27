"""SQS-based document worker for cloud deployment"""
import boto3
import json
import logging
import asyncio
import sys
import os
from typing import Optional

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings

logger = logging.getLogger(__name__)

class SQSWorker:
    """Polls SQS for document processing jobs"""
    
    def __init__(self, rag_service):
        self.rag_service = rag_service
        self.sqs = boto3.client('sqs', region_name=settings.aws_region)
        self.s3 = boto3.client('s3', region_name=settings.aws_region)
        self.dynamodb = boto3.resource('dynamodb', region_name=settings.aws_region)
        self.jobs_table = self.dynamodb.Table(settings.dynamodb_jobs_table)
        self.running = False
    
    async def start(self):
        """Start polling SQS"""
        self.running = True
        logger.info("SQS Worker started")
        asyncio.create_task(self._poll_loop())
    
    async def stop(self):
        self.running = False
    
    async def _poll_loop(self):
        """Main polling loop"""
        while self.running:
            try:
                response = self.sqs.receive_message(
                    QueueUrl=settings.sqs_queue_url,
                    MaxNumberOfMessages=1,
                    WaitTimeSeconds=20,
                    VisibilityTimeout=300
                )
                
                for message in response.get('Messages', []):
                    await self._process_message(message)
                    
            except Exception as e:
                logger.error(f"SQS poll error: {e}")
                await asyncio.sleep(5)
    
    async def _process_message(self, message: dict):
        """Process a single SQS message"""
        try:
            body = json.loads(message['Body'])
            
            # Handle S3 event notification
            if 'Records' in body:
                for record in body['Records']:
                    if record.get('eventSource') == 'aws:s3':
                        bucket = record['s3']['bucket']['name']
                        key = record['s3']['object']['key']
                        await self._process_s3_object(bucket, key)
            else:
                # Direct job message
                job_id = body.get('job_id')
                bucket = body.get('bucket')
                key = body.get('key')
                
                if job_id:
                    self._update_job_status(job_id, 'processing')
                
                await self._process_s3_object(bucket, key)
                
                if job_id:
                    self._update_job_status(job_id, 'completed')
            
            # Delete message after successful processing
            self.sqs.delete_message(
                QueueUrl=settings.sqs_queue_url,
                ReceiptHandle=message['ReceiptHandle']
            )
            
        except Exception as e:
            logger.error(f"Message processing error: {e}")
            # Message will return to queue after visibility timeout
    
    async def _process_s3_object(self, bucket: str, key: str):
        """Download and process S3 object"""
        logger.info(f"Processing s3://{bucket}/{key}")
        
        # Download file
        response = self.s3.get_object(Bucket=bucket, Key=key)
        content = response['Body'].read()
        
        # Determine format and extract text
        if key.endswith('.txt'):
            text = content.decode('utf-8')
        elif key.endswith('.pdf'):
            from pypdf import PdfReader
            import io
            reader = PdfReader(io.BytesIO(content))
            text = "\n".join([page.extract_text() for page in reader.pages])
        elif key.endswith('.docx'):
            from docx import Document
            import io
            doc = Document(io.BytesIO(content))
            text = "\n".join([p.text for p in doc.paragraphs])
        else:
            text = content.decode('utf-8', errors='ignore')
        
        # Ingest into RAG
        await self.rag_service.ingest_text(
            content=text,
            source=f"s3://{bucket}/{key}",
            metadata={"format": key.split('.')[-1]}
        )
        
        logger.info(f"Processed {key}")
    
    def _update_job_status(self, job_id: str, status: str, chunks: int = 0):
        """Update job status in DynamoDB"""
        update_expr = "SET #status = :status"
        expr_values = {':status': status}
        
        if chunks:
            update_expr += ", chunks = :chunks"
            expr_values[':chunks'] = chunks
        
        self.jobs_table.update_item(
            Key={'job_id': job_id},
            UpdateExpression=update_expr,
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues=expr_values
        )


# Entry point for running as standalone worker
if __name__ == "__main__":
    import asyncio
    from app.rag.service import RAGService
    
    logging.basicConfig(level=logging.INFO)
    
    async def main():
        logger.info("Starting SQS Worker...")
        rag_service = RAGService()
        worker = SQSWorker(rag_service)
        await worker.start()
        
        # Keep running
        while True:
            await asyncio.sleep(60)
    
    asyncio.run(main())
