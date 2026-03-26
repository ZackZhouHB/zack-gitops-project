"""EFS-based chat history manager.

Stores conversation sessions as JSON files on an EFS mount.
Each session has metadata.json and messages.json.

Structure:
    /mnt/efs/sessions/
    └── {session_id}/
        ├── metadata.json    # {session_id, title, created_at, last_active, message_count}
        └── messages.json    # [{role, content, timestamp, metadata}]
"""
import json
import os
import logging
from datetime import datetime, timezone
from pathlib import Path

from config import SESSIONS_DIR

logger = logging.getLogger("history")


def ensure_sessions_dir():
    """Create sessions directory if it doesn't exist."""
    try:
        os.makedirs(SESSIONS_DIR, exist_ok=True)
        return True
    except OSError as e:
        logger.warning(f"Cannot create sessions directory {SESSIONS_DIR}: {e}")
        return False


def create_session(session_id: str, first_message: str = "") -> dict:
    """Create a new session directory with empty files."""
    session_dir = os.path.join(SESSIONS_DIR, session_id)
    try:
        os.makedirs(session_dir, exist_ok=True)
        
        now = datetime.now(timezone.utc).isoformat()
        title = first_message[:50].strip() + ("..." if len(first_message) > 50 else "") if first_message else "New conversation"
        
        metadata = {
            "session_id": session_id,
            "title": title,
            "created_at": now,
            "last_active": now,
            "message_count": 0,
        }
        
        _write_json(os.path.join(session_dir, "metadata.json"), metadata)
        _write_json(os.path.join(session_dir, "messages.json"), [])
        
        logger.info(f"Created session: {session_id}")
        return metadata
        
    except OSError as e:
        logger.error(f"Failed to create session {session_id}: {e}")
        return {}


def list_sessions() -> list[dict]:
    """List all sessions sorted by last_active (newest first)."""
    if not os.path.isdir(SESSIONS_DIR):
        return []
    
    sessions = []
    try:
        for entry in os.scandir(SESSIONS_DIR):
            if entry.is_dir():
                meta_path = os.path.join(entry.path, "metadata.json")
                if os.path.exists(meta_path):
                    meta = _read_json(meta_path)
                    if meta:
                        sessions.append(meta)
    except OSError as e:
        logger.error(f"Failed to list sessions: {e}")
    
    sessions.sort(key=lambda s: s.get("last_active", ""), reverse=True)
    return sessions


def get_session_history(session_id: str) -> list[dict]:
    """Get all messages for a session."""
    messages_path = os.path.join(SESSIONS_DIR, session_id, "messages.json")
    if not os.path.exists(messages_path):
        return []
    return _read_json(messages_path) or []


def save_message(session_id: str, role: str, content: str, metadata: dict | None = None):
    """Append a message to the session history and update metadata."""
    session_dir = os.path.join(SESSIONS_DIR, session_id)
    
    # Auto-create session if it doesn't exist
    if not os.path.isdir(session_dir):
        first_msg = content if role == "user" else ""
        create_session(session_id, first_msg)
    
    messages_path = os.path.join(session_dir, "messages.json")
    meta_path = os.path.join(session_dir, "metadata.json")
    
    try:
        # Append message
        messages = _read_json(messages_path) or []
        messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {},
        })
        _write_json(messages_path, messages)
        
        # Update metadata
        meta = _read_json(meta_path) or {}
        meta["last_active"] = datetime.now(timezone.utc).isoformat()
        meta["message_count"] = len(messages)
        
        # Update title from first user message if still default
        if meta.get("title", "").startswith("New conversation") and role == "user":
            meta["title"] = content[:50].strip() + ("..." if len(content) > 50 else "")
        
        _write_json(meta_path, meta)
        
    except Exception as e:
        logger.error(f"Failed to save message to session {session_id}: {e}")


def _read_json(path: str):
    """Read a JSON file, return None on error."""
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"Failed to read {path}: {e}")
        return None


def _write_json(path: str, data):
    """Write JSON file atomically (write to temp then rename)."""
    tmp_path = path + ".tmp"
    try:
        with open(tmp_path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        os.replace(tmp_path, path)  # atomic on POSIX
    except OSError as e:
        logger.error(f"Failed to write {path}: {e}")
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
