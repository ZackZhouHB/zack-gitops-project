"""Response caching for RAG queries"""
import hashlib
import json
import time
from typing import Optional, Dict, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class ResponseCache:
    """Simple file-based cache for RAG responses"""
    
    def __init__(self, cache_dir: str = "/app/data/cache", ttl_seconds: int = 3600):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = ttl_seconds
        self.hits = 0
        self.misses = 0
    
    def _hash_key(self, query: str, params: dict) -> str:
        """Generate cache key from query and params"""
        key_data = json.dumps({"q": query.lower().strip(), **params}, sort_keys=True)
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, query: str, params: dict = None) -> Optional[Dict[str, Any]]:
        """Get cached response if exists and not expired"""
        key = self._hash_key(query, params or {})
        cache_file = self.cache_dir / f"{key}.json"
        
        if not cache_file.exists():
            self.misses += 1
            return None
        
        try:
            with open(cache_file, "r") as f:
                cached = json.load(f)
            
            if time.time() - cached["timestamp"] > self.ttl:
                cache_file.unlink()  # Expired
                self.misses += 1
                return None
            
            self.hits += 1
            logger.info(f"Cache hit for query: {query[:50]}...")
            return cached["response"]
        except Exception as e:
            logger.warning(f"Cache read error: {e}")
            self.misses += 1
            return None
    
    def set(self, query: str, response: Dict[str, Any], params: dict = None):
        """Cache a response"""
        key = self._hash_key(query, params or {})
        cache_file = self.cache_dir / f"{key}.json"
        
        try:
            with open(cache_file, "w") as f:
                json.dump({"timestamp": time.time(), "response": response}, f)
        except Exception as e:
            logger.warning(f"Cache write error: {e}")
    
    def stats(self) -> dict:
        """Get cache statistics"""
        total = self.hits + self.misses
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(self.hits / total, 2) if total > 0 else 0,
            "ttl_seconds": self.ttl
        }
