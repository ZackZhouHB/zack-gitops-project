"""Async job queue for document processing - simulates SQS locally"""
import asyncio
import uuid
import logging
from datetime import datetime
from typing import Dict, Optional
from enum import Enum

logger = logging.getLogger(__name__)

class JobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class JobQueue:
    """In-memory job queue (replace with SQS in production)"""
    
    def __init__(self):
        self.jobs: Dict[str, dict] = {}
        self.queue: asyncio.Queue = asyncio.Queue()
        self.worker_running = False
    
    def create_job(self, filename: str, file_content: bytes, allowed_groups: list) -> str:
        """Create a new processing job"""
        job_id = str(uuid.uuid4())[:8]
        self.jobs[job_id] = {
            "job_id": job_id,
            "filename": filename,
            "status": JobStatus.QUEUED,
            "created_at": datetime.now().isoformat(),
            "completed_at": None,
            "chunks": 0,
            "error": None,
            "file_content": file_content,
            "allowed_groups": allowed_groups,
        }
        return job_id
    
    async def enqueue(self, job_id: str):
        """Add job to processing queue"""
        await self.queue.put(job_id)
        logger.info(f"Job {job_id} queued")
    
    def get_job(self, job_id: str) -> Optional[dict]:
        """Get job status"""
        job = self.jobs.get(job_id)
        if job:
            # Don't return file content in status
            return {k: v for k, v in job.items() if k != "file_content"}
        return None
    
    def update_job(self, job_id: str, **kwargs):
        """Update job status"""
        if job_id in self.jobs:
            self.jobs[job_id].update(kwargs)
    
    def list_jobs(self, limit: int = 20) -> list:
        """List recent jobs"""
        jobs = sorted(self.jobs.values(), key=lambda x: x["created_at"], reverse=True)
        return [{k: v for k, v in j.items() if k != "file_content"} for j in jobs[:limit]]


class DocumentWorker:
    """Background worker for processing documents"""
    
    def __init__(self, job_queue: JobQueue, rag_service):
        self.queue = job_queue
        self.rag_service = rag_service
        self.running = False
    
    async def start(self):
        """Start the background worker"""
        if self.running:
            return
        self.running = True
        asyncio.create_task(self._process_loop())
        logger.info("Document worker started")
    
    async def _process_loop(self):
        """Main processing loop"""
        while self.running:
            try:
                # Wait for job with timeout
                try:
                    job_id = await asyncio.wait_for(self.queue.queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                
                await self._process_job(job_id)
                
            except Exception as e:
                logger.error(f"Worker error: {e}")
    
    async def _process_job(self, job_id: str):
        """Process a single job"""
        job = self.queue.jobs.get(job_id)
        if not job:
            return
        
        logger.info(f"Processing job {job_id}: {job['filename']}")
        self.queue.update_job(job_id, status=JobStatus.PROCESSING)
        
        try:
            # Simulate file upload object
            class FakeFile:
                def __init__(self, filename, content):
                    self.filename = filename
                    self._content = content
                async def read(self):
                    return self._content
            
            fake_file = FakeFile(job["filename"], job["file_content"])
            
            # Process document
            result = await self.rag_service.process_document(fake_file, job["allowed_groups"])
            
            self.queue.update_job(
                job_id,
                status=JobStatus.COMPLETED,
                completed_at=datetime.now().isoformat(),
                chunks=result["chunks"]
            )
            logger.info(f"Job {job_id} completed: {result['chunks']} chunks")
            
        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")
            self.queue.update_job(
                job_id,
                status=JobStatus.FAILED,
                completed_at=datetime.now().isoformat(),
                error=str(e)
            )
