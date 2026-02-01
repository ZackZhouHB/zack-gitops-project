"""Chunking Strategies"""
from enum import Enum

class ChunkStrategy(Enum):
    FIXED = "fixed"           # Simple fixed size
    RECURSIVE = "recursive"   # LangChain recursive (respects boundaries)
    MARKDOWN = "markdown"     # Header-aware for MD
    CODE = "code"             # Code-aware (preserve functions)
    PAGE = "page"             # PDF page-based
    SLIDE = "slide"           # PPT slide-based

# Map document types to best chunking strategy
STRATEGY_MAP = {
    "txt": ChunkStrategy.RECURSIVE,
    "md": ChunkStrategy.MARKDOWN,
    "pdf": ChunkStrategy.PAGE,
    "docx": ChunkStrategy.RECURSIVE,
    "pptx": ChunkStrategy.SLIDE,
    "xlsx": ChunkStrategy.FIXED,
    "py": ChunkStrategy.CODE,
    "js": ChunkStrategy.CODE,
    "java": ChunkStrategy.CODE,
    "jira": ChunkStrategy.FIXED,
    "confluence": ChunkStrategy.MARKDOWN,
}
