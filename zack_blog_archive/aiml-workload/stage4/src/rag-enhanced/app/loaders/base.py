"""Document Loaders - Base class and common utilities"""
import hashlib
from typing import Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class LoadedDocument:
    """Standardized document output from all loaders"""
    content: str
    filename: str
    source_type: str  # pdf, docx, xlsx, md, confluence
    size_bytes: int
    checksum: str     # For change detection
    page_count: Optional[int] = None
    metadata: Optional[dict] = None
    
    @staticmethod
    def calculate_checksum(content: bytes) -> str:
        """MD5 checksum for change detection"""
        return hashlib.md5(content).hexdigest()
