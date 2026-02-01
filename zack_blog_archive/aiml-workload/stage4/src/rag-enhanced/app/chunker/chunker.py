"""Smart Chunker - Selects strategy based on document type"""
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    MarkdownTextSplitter,
    Language,
)

from .strategies import ChunkStrategy, STRATEGY_MAP

logger = logging.getLogger(__name__)

@dataclass
class Chunk:
    content: str
    chunk_id: int
    total_chunks: int
    source: str
    source_type: str
    content_type: str = "text"  # text, code, table
    page_number: Optional[int] = None
    section_header: Optional[str] = None
    language: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "content": self.content,
            "chunk_id": self.chunk_id,
            "total_chunks": self.total_chunks,
            "source": self.source,
            "source_type": self.source_type,
            "content_type": self.content_type,
            "page_number": self.page_number,
            "section_header": self.section_header,
            "language": self.language,
        }


class SmartChunker:
    """
    Intelligent chunking with strategy selection per document type.
    Uses LangChain splitters under the hood.
    """
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Initialize splitters
        self.recursive_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        self.markdown_splitter = MarkdownTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        self.fixed_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=[""]  # Fixed size only
        )
    
    def chunk(
        self,
        content: str,
        source: str,
        source_type: str,
        strategy: Optional[ChunkStrategy] = None,
        metadata: Optional[Dict] = None
    ) -> List[Chunk]:
        """
        Chunk content using appropriate strategy.
        Auto-selects strategy based on source_type if not specified.
        """
        if strategy is None:
            strategy = STRATEGY_MAP.get(source_type, ChunkStrategy.RECURSIVE)
        
        logger.info(f"Chunking {source} with strategy: {strategy.value}")
        
        if strategy == ChunkStrategy.RECURSIVE:
            texts = self.recursive_splitter.split_text(content)
        elif strategy == ChunkStrategy.MARKDOWN:
            texts = self.markdown_splitter.split_text(content)
        elif strategy == ChunkStrategy.CODE:
            texts = self._chunk_code(content, source_type)
        elif strategy == ChunkStrategy.PAGE:
            texts = self._chunk_by_pages(content, metadata)
        elif strategy == ChunkStrategy.SLIDE:
            texts = self._chunk_by_slides(content, metadata)
        else:
            texts = self.fixed_splitter.split_text(content)
        
        chunks = []
        for i, text in enumerate(texts):
            chunk = Chunk(
                content=text,
                chunk_id=i,
                total_chunks=len(texts),
                source=source,
                source_type=source_type,
                content_type=self._detect_content_type(text),
                page_number=metadata.get("page_numbers", {}).get(i) if metadata else None,
                section_header=self._extract_header(text),
                language=source_type if strategy == ChunkStrategy.CODE else None
            )
            chunks.append(chunk)
        
        logger.info(f"Created {len(chunks)} chunks from {source}")
        return chunks
    
    def _chunk_code(self, content: str, language: str) -> List[str]:
        """Chunk code preserving function boundaries"""
        lang_map = {
            "py": Language.PYTHON,
            "js": Language.JS,
            "java": Language.JAVA,
            "go": Language.GO,
        }
        lang = lang_map.get(language, Language.PYTHON)
        
        splitter = RecursiveCharacterTextSplitter.from_language(
            language=lang,
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )
        return splitter.split_text(content)
    
    def _chunk_by_pages(self, content: str, metadata: Optional[Dict]) -> List[str]:
        """Chunk PDF by pages (expects page markers in content)"""
        if metadata and "pages" in metadata:
            return metadata["pages"]
        # Fallback to recursive if no page info
        return self.recursive_splitter.split_text(content)
    
    def _chunk_by_slides(self, content: str, metadata: Optional[Dict]) -> List[str]:
        """Chunk PPT by slides (expects slide markers in content)"""
        if metadata and "slides" in metadata:
            return metadata["slides"]
        # Fallback to recursive if no slide info
        return self.recursive_splitter.split_text(content)
    
    def _detect_content_type(self, text: str) -> str:
        """Detect if chunk is code, table, or text"""
        if text.strip().startswith("```") or "def " in text or "function " in text:
            return "code"
        if "|" in text and text.count("|") > 3:
            return "table"
        return "text"
    
    def _extract_header(self, text: str) -> Optional[str]:
        """Extract section header if present"""
        lines = text.strip().split("\n")
        if lines and lines[0].startswith("#"):
            return lines[0].lstrip("#").strip()
        return None
