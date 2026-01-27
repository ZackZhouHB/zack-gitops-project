"""Session memory for multi-turn conversations"""
from typing import Dict, List
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class ConversationMemory:
    """Manages conversation history per session"""
    
    def __init__(self, max_turns: int = 10, timeout_minutes: int = 60):
        self.sessions: Dict[str, dict] = {}
        self.max_turns = max_turns
        self.timeout = timedelta(minutes=timeout_minutes)
    
    def get_history(self, session_id: str) -> List[dict]:
        """Get conversation history for session"""
        self._cleanup()
        if session_id not in self.sessions:
            self.sessions[session_id] = {"history": [], "last_access": datetime.now()}
        self.sessions[session_id]["last_access"] = datetime.now()
        return self.sessions[session_id]["history"]
    
    def add_turn(self, session_id: str, question: str, answer: str):
        """Add Q&A turn to session history"""
        history = self.get_history(session_id)
        history.append({"role": "user", "content": question})
        history.append({"role": "assistant", "content": answer})
        
        # Keep only last N turns (2 messages per turn)
        if len(history) > self.max_turns * 2:
            self.sessions[session_id]["history"] = history[-(self.max_turns * 2):]
    
    def format_for_prompt(self, session_id: str) -> str:
        """Format history for LLM prompt"""
        history = self.get_history(session_id)
        if not history:
            return ""
        
        formatted = []
        for msg in history[-6:]:  # Last 3 turns
            role = "Human" if msg["role"] == "user" else "Assistant"
            formatted.append(f"{role}: {msg['content']}")
        
        return "\n".join(formatted)
    
    def clear(self, session_id: str):
        """Clear session history"""
        if session_id in self.sessions:
            del self.sessions[session_id]
    
    def _cleanup(self):
        """Remove expired sessions"""
        now = datetime.now()
        expired = [sid for sid, data in self.sessions.items() 
                   if now - data["last_access"] > self.timeout]
        for sid in expired:
            del self.sessions[sid]
