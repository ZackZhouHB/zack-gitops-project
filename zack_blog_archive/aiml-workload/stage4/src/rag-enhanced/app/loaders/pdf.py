"""PDF Loader - Extract text from PDF files with page awareness"""
import io
import logging
from typing import List, Optional
import pdfplumber

from .base import LoadedDocument

logger = logging.getLogger(__name__)

class PDFLoader:
    """
    Load PDF documents with page-aware extraction.
    Uses pdfplumber for reliable text extraction.
    """
    
    def load(self, file_content: bytes, filename: str) -> LoadedDocument:
        """
        Extract text from PDF, preserving page structure.
        
        Returns:
            LoadedDocument with content and metadata
        """
        pages_text = []
        page_count = 0
        
        with pdfplumber.open(io.BytesIO(file_content)) as pdf:
            page_count = len(pdf.pages)
            
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                if text.strip():
                    # Add page marker for chunking
                    pages_text.append(f"[Page {i+1}]\n{text}")
        
        content = "\n\n".join(pages_text)
        
        logger.info(f"Loaded PDF: {filename}, {page_count} pages, {len(content)} chars")
        
        return LoadedDocument(
            content=content,
            filename=filename,
            source_type="pdf",
            size_bytes=len(file_content),
            checksum=LoadedDocument.calculate_checksum(file_content),
            page_count=page_count,
            metadata={"pages": page_count}
        )
    
    def load_with_tables(self, file_content: bytes, filename: str) -> LoadedDocument:
        """
        Extract text AND tables from PDF.
        Tables are converted to markdown format.
        """
        pages_text = []
        
        with pdfplumber.open(io.BytesIO(file_content)) as pdf:
            for i, page in enumerate(pdf.pages):
                page_content = []
                
                # Extract text
                text = page.extract_text() or ""
                if text.strip():
                    page_content.append(text)
                
                # Extract tables
                tables = page.extract_tables()
                for table in tables:
                    if table:
                        md_table = self._table_to_markdown(table)
                        page_content.append(f"\n{md_table}\n")
                
                if page_content:
                    pages_text.append(f"[Page {i+1}]\n" + "\n".join(page_content))
        
        content = "\n\n".join(pages_text)
        
        return LoadedDocument(
            content=content,
            filename=filename,
            source_type="pdf",
            size_bytes=len(file_content),
            checksum=LoadedDocument.calculate_checksum(file_content),
            page_count=len(pages_text),
            metadata={"pages": len(pages_text), "has_tables": True}
        )
    
    def _table_to_markdown(self, table: List[List]) -> str:
        """Convert table to markdown format"""
        if not table or not table[0]:
            return ""
        
        lines = []
        # Header
        header = [str(cell or "") for cell in table[0]]
        lines.append("| " + " | ".join(header) + " |")
        lines.append("| " + " | ".join(["---"] * len(header)) + " |")
        
        # Rows
        for row in table[1:]:
            cells = [str(cell or "") for cell in row]
            lines.append("| " + " | ".join(cells) + " |")
        
        return "\n".join(lines)
