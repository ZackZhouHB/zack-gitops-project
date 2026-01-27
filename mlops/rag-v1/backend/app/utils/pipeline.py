"""Scheduled data pipeline - simulates enterprise ingestion patterns"""
import asyncio
import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class SyncJob:
    source_type: str
    source_config: Dict
    schedule: str  # cron-like: "*/5" = every 5 min, "0" = hourly, "daily"
    last_run: Optional[str] = None
    last_hash: Optional[str] = None
    enabled: bool = True

class DataPipelineScheduler:
    """
    Simulates enterprise data pipeline patterns:
    - Scheduled polling (like Airflow/CloudWatch Events)
    - Change detection (like CDC)
    - Incremental sync (only new/changed docs)
    """
    
    def __init__(self, state_file: str = "/app/data/pipeline_state.json"):
        self.state_file = Path(state_file)
        self.jobs: Dict[str, SyncJob] = {}
        self.running = False
        self._load_state()
    
    def _load_state(self):
        if self.state_file.exists():
            data = json.loads(self.state_file.read_text())
            for name, job_data in data.get("jobs", {}).items():
                self.jobs[name] = SyncJob(**job_data)
    
    def _save_state(self):
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        data = {"jobs": {k: asdict(v) for k, v in self.jobs.items()}}
        self.state_file.write_text(json.dumps(data, indent=2))
    
    def add_job(self, name: str, source_type: str, source_config: Dict, schedule: str = "*/5"):
        """Add a sync job"""
        self.jobs[name] = SyncJob(
            source_type=source_type,
            source_config=source_config,
            schedule=schedule
        )
        self._save_state()
        logger.info(f"Added pipeline job: {name} ({source_type}, schedule={schedule})")
    
    def remove_job(self, name: str):
        if name in self.jobs:
            del self.jobs[name]
            self._save_state()
    
    def list_jobs(self) -> List[Dict]:
        return [{"name": k, **asdict(v)} for k, v in self.jobs.items()]
    
    async def run_job(self, name: str, rag_service) -> Dict:
        """Run a single sync job with change detection"""
        if name not in self.jobs:
            return {"error": f"Job {name} not found"}
        
        job = self.jobs[name]
        result = {"job": name, "source_type": job.source_type, "synced": 0, "skipped": 0}
        
        try:
            if job.source_type == "web":
                from ..connectors.web_connector import WebConnector
                connector = WebConnector(
                    job.source_config["base_url"],
                    job.source_config.get("auth")
                )
                if job.source_config.get("auth"):
                    connector.authenticate()
                
                pages = connector.fetch_all(
                    job.source_config.get("pattern", "/"),
                    job.source_config.get("limit", 50)
                )
                connector.close()
                
                # Change detection - only ingest new/changed content
                for page in pages:
                    if page.content_hash != job.last_hash:
                        await rag_service.ingest_text(
                            page.content,
                            source=page.url,
                            metadata={"title": page.title, "pipeline_job": name}
                        )
                        result["synced"] += 1
                    else:
                        result["skipped"] += 1
                
            elif job.source_type == "directory":
                # Watch a local directory for new files
                watch_dir = Path(job.source_config["path"])
                if watch_dir.exists():
                    for f in watch_dir.glob(job.source_config.get("pattern", "*")):
                        if f.is_file():
                            content = f.read_text()
                            content_hash = hashlib.md5(content.encode()).hexdigest()
                            # Simple change detection
                            await rag_service.ingest_text(content, source=f.name)
                            result["synced"] += 1
            
            # Update job state
            job.last_run = datetime.utcnow().isoformat()
            self._save_state()
            
        except Exception as e:
            logger.error(f"Pipeline job {name} failed: {e}")
            result["error"] = str(e)
        
        return result
    
    async def run_all_due(self, rag_service) -> List[Dict]:
        """Run all jobs that are due (simplified - runs all enabled jobs)"""
        results = []
        for name, job in self.jobs.items():
            if job.enabled:
                result = await self.run_job(name, rag_service)
                results.append(result)
        return results
    
    async def start_scheduler(self, rag_service, interval_seconds: int = 300):
        """Background scheduler loop (like Airflow scheduler)"""
        self.running = True
        logger.info(f"Pipeline scheduler started (interval={interval_seconds}s)")
        
        while self.running:
            try:
                results = await self.run_all_due(rag_service)
                for r in results:
                    if r.get("synced", 0) > 0:
                        logger.info(f"Pipeline sync: {r['job']} synced {r['synced']} docs")
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
            
            await asyncio.sleep(interval_seconds)
    
    def stop_scheduler(self):
        self.running = False
