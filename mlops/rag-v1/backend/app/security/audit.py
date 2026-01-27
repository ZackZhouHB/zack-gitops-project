"""Audit logging for compliance"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List

logger = logging.getLogger(__name__)

class AuditLogger:
    """Log all RAG operations for compliance and debugging"""
    
    def __init__(self, log_path: str = "/app/data/audit"):
        self.log_path = Path(log_path)
        self.log_path.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_path / "audit.jsonl"
    
    def log(
        self,
        action: str,
        user_id: Optional[str],
        details: dict,
        sources_accessed: Optional[List[str]] = None
    ):
        """Log an audit event"""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "user_id": user_id or "anonymous",
            "details": details,
            "sources_accessed": sources_accessed or [],
        }
        
        # Append to JSONL file
        with open(self.log_file, "a") as f:
            f.write(json.dumps(event) + "\n")
        
        logger.info(f"AUDIT: {action} by {user_id}")
    
    def log_query(self, user_id: str, question: str, sources: List[str], response_time: float):
        self.log("QUERY", user_id, {
            "question": question,
            "response_time_ms": round(response_time * 1000, 2)
        }, sources)
    
    def log_upload(self, user_id: str, filename: str, chunks: int, allowed_groups: List[str]):
        self.log("UPLOAD", user_id, {
            "filename": filename,
            "chunks": chunks,
            "allowed_groups": allowed_groups
        })
    
    def log_auth(self, user_id: str, action: str, success: bool):
        self.log("AUTH", user_id, {"auth_action": action, "success": success})
    
    def log_action(self, user_id: str, action: str, details: dict):
        self.log(action.upper(), user_id, details)
    
    def get_recent(self, limit: int = 100) -> List[dict]:
        """Get recent audit events"""
        if not self.log_file.exists():
            return []
        
        events = []
        with open(self.log_file, "r") as f:
            for line in f:
                if line.strip():
                    events.append(json.loads(line))
        
        return events[-limit:]
