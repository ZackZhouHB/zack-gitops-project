"""Rate limiting and token tracking"""
import time
from collections import defaultdict
from typing import Dict, Tuple

class RateLimiter:
    """Simple in-memory rate limiter (use Redis in production)"""
    
    def __init__(self, requests_per_minute: int = 20):
        self.rpm = requests_per_minute
        self.requests: Dict[str, list] = defaultdict(list)
    
    def check(self, user_id: str) -> Tuple[bool, int]:
        """Check if request is allowed. Returns (allowed, retry_after_seconds)"""
        now = time.time()
        window_start = now - 60
        
        # Clean old requests
        self.requests[user_id] = [t for t in self.requests[user_id] if t > window_start]
        
        if len(self.requests[user_id]) >= self.rpm:
            oldest = min(self.requests[user_id])
            retry_after = int(oldest + 60 - now) + 1
            return False, retry_after
        
        self.requests[user_id].append(now)
        return True, 0


class TokenTracker:
    """Track token usage for cost monitoring"""
    
    # Approximate costs per 1K tokens
    COSTS = {
        "amazon.titan-embed-text-v1": {"input": 0.0001},
        "anthropic.claude-3-haiku-20240307-v1:0": {"input": 0.00025, "output": 0.00125},
        "anthropic.claude-3-sonnet-20240229-v1:0": {"input": 0.003, "output": 0.015},
    }
    
    def __init__(self):
        self.usage: Dict[str, dict] = defaultdict(lambda: {
            "input_tokens": 0,
            "output_tokens": 0,
            "embedding_tokens": 0,
            "requests": 0,
            "estimated_cost": 0.0
        })
    
    def track(self, user_id: str, model: str, input_tokens: int, output_tokens: int = 0):
        """Track token usage"""
        self.usage[user_id]["requests"] += 1
        
        if "embed" in model:
            self.usage[user_id]["embedding_tokens"] += input_tokens
            cost = (input_tokens / 1000) * self.COSTS.get(model, {}).get("input", 0.0001)
        else:
            self.usage[user_id]["input_tokens"] += input_tokens
            self.usage[user_id]["output_tokens"] += output_tokens
            costs = self.COSTS.get(model, {"input": 0.001, "output": 0.002})
            cost = (input_tokens / 1000) * costs["input"] + (output_tokens / 1000) * costs["output"]
        
        self.usage[user_id]["estimated_cost"] += cost
    
    def get_usage(self, user_id: str = None) -> dict:
        """Get usage stats"""
        if user_id:
            return dict(self.usage[user_id])
        
        # Aggregate all users
        total = {"input_tokens": 0, "output_tokens": 0, "embedding_tokens": 0, "requests": 0, "estimated_cost": 0.0}
        for u in self.usage.values():
            for k in total:
                total[k] += u[k]
        total["estimated_cost"] = round(total["estimated_cost"], 4)
        return total
