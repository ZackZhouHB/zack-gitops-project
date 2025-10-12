from datetime import datetime, timedelta
from typing import Dict, Tuple
from langchain.memory import ConversationBufferWindowMemory
import logging

logger = logging.getLogger(__name__)

class SessionMemoryManager:
    """Manages conversation memory per session with automatic cleanup"""
    
    def __init__(self, session_timeout_minutes: int = 60, max_turns: int = 20):
        self.sessions: Dict[str, Tuple[ConversationBufferWindowMemory, datetime]] = {}
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
        self.max_turns = max_turns
    
    def get_memory(self, session_id: str) -> ConversationBufferWindowMemory:
        """Get or create memory for a session"""
        self._cleanup_old_sessions()
        
        if session_id not in self.sessions:
            logger.info(f"Creating new session: {session_id}")
            memory = ConversationBufferWindowMemory(
                k=self.max_turns,
                memory_key="chat_history",
                return_messages=True,
                output_key="answer"
            )
            self.sessions[session_id] = (memory, datetime.now())
        else:
            memory, _ = self.sessions[session_id]
            # Update last access time
            self.sessions[session_id] = (memory, datetime.now())
        
        return memory
    
    def clear_session(self, session_id: str):
        """Clear a specific session"""
        if session_id in self.sessions:
            logger.info(f"Clearing session: {session_id}")
            del self.sessions[session_id]
    
    def _cleanup_old_sessions(self):
        """Remove sessions older than timeout"""
        cutoff = datetime.now() - self.session_timeout
        old_sessions = [
            sid for sid, (_, last_access) in self.sessions.items() 
            if last_access < cutoff
        ]
        
        for sid in old_sessions:
            logger.info(f"Cleaning up expired session: {sid}")
            del self.sessions[sid]
    
    def get_stats(self) -> dict:
        """Get session statistics"""
        return {
            "active_sessions": len(self.sessions),
            "oldest_session_age_minutes": self._get_oldest_session_age(),
            "total_memory_mb": self._estimate_memory_usage()
        }
    
    def _get_oldest_session_age(self) -> float:
        """Get age of oldest session in minutes"""
        if not self.sessions:
            return 0
        oldest = min(last_access for _, last_access in self.sessions.values())
        return (datetime.now() - oldest).total_seconds() / 60
    
    def _estimate_memory_usage(self) -> float:
        """Estimate total memory usage in MB"""
        # Rough estimate: 50KB per session
        return len(self.sessions) * 0.05
