"""Input validation and prompt injection prevention"""
import re
from typing import Tuple

class InputValidator:
    """Validate and sanitize user inputs"""
    
    # Patterns that might indicate prompt injection
    INJECTION_PATTERNS = [
        r"ignore\s+(previous|above|all)\s+instructions",
        r"disregard\s+(previous|above|all)",
        r"forget\s+(everything|all|previous)",
        r"you\s+are\s+now\s+a",
        r"act\s+as\s+(if|a)",
        r"pretend\s+(to\s+be|you)",
        r"system\s*:\s*",
        r"<\s*system\s*>",
        r"\[\s*INST\s*\]",
    ]
    
    # PII patterns to detect (not block, just flag)
    PII_PATTERNS = {
        "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        "phone": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        "credit_card": r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
    }
    
    MAX_QUERY_LENGTH = 2000
    
    @classmethod
    def validate_query(cls, query: str) -> Tuple[bool, str, list]:
        """
        Validate query input.
        Returns: (is_valid, sanitized_query, warnings)
        """
        warnings = []
        
        # Length check
        if len(query) > cls.MAX_QUERY_LENGTH:
            return False, "", [f"Query too long (max {cls.MAX_QUERY_LENGTH} chars)"]
        
        if not query.strip():
            return False, "", ["Query cannot be empty"]
        
        # Check for injection attempts
        query_lower = query.lower()
        for pattern in cls.INJECTION_PATTERNS:
            if re.search(pattern, query_lower):
                warnings.append("Potential prompt injection detected")
                break
        
        # Check for PII (warn but don't block)
        for pii_type, pattern in cls.PII_PATTERNS.items():
            if re.search(pattern, query):
                warnings.append(f"Query may contain {pii_type}")
        
        # Basic sanitization - remove control characters
        sanitized = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', query)
        
        return True, sanitized, warnings
    
    @classmethod
    def sanitize_output(cls, text: str) -> str:
        """Remove potential PII from output"""
        result = text
        for pii_type, pattern in cls.PII_PATTERNS.items():
            result = re.sub(pattern, f"[{pii_type.upper()}_REDACTED]", result)
        return result
