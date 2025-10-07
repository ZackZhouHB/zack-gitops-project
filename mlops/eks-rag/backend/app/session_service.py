import hashlib
import time
from typing import Optional

class SessionService:
    """Simple session management using client IP + timestamp"""
    
    def __init__(self):
        self.sessions = {}
    
    def get_session_id(self, request) -> str:
        """Generate session ID from client IP"""
        client_ip = request.client.host
        # Use IP hash for session ID (simple approach)
        session_id = hashlib.md5(f"{client_ip}".encode()).hexdigest()[:8]
        
        # Track session
        self.sessions[session_id] = {
            'ip': client_ip,
            'last_seen': time.time()
        }
        
        return session_id
    
    def get_user_prefix(self, session_id: str) -> str:
        """Get S3/EFS prefix for user isolation"""
        return f"user-{session_id}"
    
    def get_chat_history_path(self, session_id: str) -> str:
        """Get user-specific chat history path"""
        return f"/efs/chat_history/user-{session_id}-history.json"
