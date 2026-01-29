"""
Document loaders for different source types.
Handles: PDF, CSV (ServiceNow), Markdown, HTML (Confluence)
"""

import csv
import json
from pathlib import Path
from dataclasses import dataclass
from typing import Iterator
from abc import ABC, abstractmethod


@dataclass
class Document:
    """Represents a loaded document with metadata."""
    content: str
    metadata: dict
    source_type: str  # 'lld', 'servicenow', 'confluence'
    source_path: str


class BaseLoader(ABC):
    """Base class for document loaders."""
    
    @abstractmethod
    def load(self) -> Iterator[Document]:
        pass


class PDFLoader(BaseLoader):
    """
    Load PDF documents (LLD files from SharePoint).
    
    WHY PDF IS TRICKY:
    - Text extraction varies by PDF type (text vs scanned)
    - Tables often lose structure
    - Headers/footers get mixed in
    
    LIBRARIES:
    - PyPDF2: Simple, fast, text-only
    - pdfplumber: Better table extraction
    - unstructured: Best quality, slower
    """
    
    def __init__(self, path: str | Path):
        self.path = Path(path)
    
    def load(self) -> Iterator[Document]:
        try:
            import pdfplumber
        except ImportError:
            raise ImportError("pip install pdfplumber")
        
        if self.path.is_file():
            yield from self._load_single(self.path)
        elif self.path.is_dir():
            for pdf_file in self.path.glob("**/*.pdf"):
                yield from self._load_single(pdf_file)
    
    def _load_single(self, file_path: Path) -> Iterator[Document]:
        import pdfplumber
        
        with pdfplumber.open(file_path) as pdf:
            full_text = []
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text() or ""
                full_text.append(f"[Page {page_num}]\n{text}")
            
            yield Document(
                content="\n\n".join(full_text),
                metadata={
                    "filename": file_path.name,
                    "page_count": len(pdf.pages),
                    "source_type": "lld"
                },
                source_type="lld",
                source_path=str(file_path)
            )


class ServiceNowCSVLoader(BaseLoader):
    """
    Load ServiceNow incident exports (CSV format).
    
    EXPECTED COLUMNS:
    - number: Incident ID (INC0012345)
    - short_description: Brief summary
    - description: Full description
    - resolution_notes: How it was fixed
    - category: Incident category
    - resolved_at: Resolution date
    
    WHY EACH INCIDENT = ONE DOCUMENT:
    - Each incident is a self-contained knowledge unit
    - Resolution notes are the key value
    - Incident ID enables exact matching (hybrid search)
    """
    
    def __init__(self, path: str | Path):
        self.path = Path(path)
    
    def load(self) -> Iterator[Document]:
        with open(self.path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                # Combine fields into searchable content
                content = f"""
Incident: {row.get('number', 'N/A')}
Category: {row.get('category', 'N/A')}
Summary: {row.get('short_description', 'N/A')}

Description:
{row.get('description', 'N/A')}

Resolution:
{row.get('resolution_notes', 'N/A')}
""".strip()
                
                yield Document(
                    content=content,
                    metadata={
                        "incident_number": row.get('number'),
                        "category": row.get('category'),
                        "resolved_at": row.get('resolved_at'),
                        "source_type": "servicenow"
                    },
                    source_type="servicenow",
                    source_path=str(self.path)
                )


class MarkdownLoader(BaseLoader):
    """
    Load Markdown files (runbooks, docs).
    
    PRESERVES:
    - Headers (useful for chunking by section)
    - Code blocks (important for runbooks)
    - Lists and tables
    """
    
    def __init__(self, path: str | Path):
        self.path = Path(path)
    
    def load(self) -> Iterator[Document]:
        if self.path.is_file():
            yield from self._load_single(self.path)
        elif self.path.is_dir():
            for md_file in self.path.glob("**/*.md"):
                yield from self._load_single(md_file)
    
    def _load_single(self, file_path: Path) -> Iterator[Document]:
        content = file_path.read_text(encoding='utf-8')
        
        # Extract title from first H1 if present
        title = file_path.stem
        lines = content.split('\n')
        for line in lines:
            if line.startswith('# '):
                title = line[2:].strip()
                break
        
        yield Document(
            content=content,
            metadata={
                "filename": file_path.name,
                "title": title,
                "source_type": "confluence"  # or could be 'runbook'
            },
            source_type="confluence",
            source_path=str(file_path)
        )


class HTMLLoader(BaseLoader):
    """
    Load HTML files (Confluence exports).
    
    STRIPS:
    - HTML tags
    - Scripts and styles
    - Navigation elements
    
    PRESERVES:
    - Text content
    - Basic structure
    """
    
    def __init__(self, path: str | Path):
        self.path = Path(path)
    
    def load(self) -> Iterator[Document]:
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            raise ImportError("pip install beautifulsoup4")
        
        if self.path.is_file():
            yield from self._load_single(self.path)
        elif self.path.is_dir():
            for html_file in self.path.glob("**/*.html"):
                yield from self._load_single(html_file)
    
    def _load_single(self, file_path: Path) -> Iterator[Document]:
        from bs4 import BeautifulSoup
        
        html_content = file_path.read_text(encoding='utf-8')
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for element in soup(['script', 'style', 'nav', 'header', 'footer']):
            element.decompose()
        
        # Get text content
        text = soup.get_text(separator='\n', strip=True)
        
        # Try to get title
        title = file_path.stem
        if soup.title:
            title = soup.title.string or title
        
        yield Document(
            content=text,
            metadata={
                "filename": file_path.name,
                "title": title,
                "source_type": "confluence"
            },
            source_type="confluence",
            source_path=str(file_path)
        )


def load_all_documents(data_dir: str | Path) -> Iterator[Document]:
    """
    Load all documents from the data directory.
    
    Expected structure:
    data/
    ├── lld/           # PDF files
    ├── servicenow/    # CSV exports
    └── confluence/    # MD or HTML files
    """
    data_path = Path(data_dir)
    
    # Load LLD PDFs
    lld_path = data_path / "lld"
    if lld_path.exists():
        yield from PDFLoader(lld_path).load()
    
    # Load ServiceNow CSVs
    servicenow_path = data_path / "servicenow"
    if servicenow_path.exists():
        for csv_file in servicenow_path.glob("*.csv"):
            yield from ServiceNowCSVLoader(csv_file).load()
    
    # Load Confluence (MD and HTML)
    confluence_path = data_path / "confluence"
    if confluence_path.exists():
        yield from MarkdownLoader(confluence_path).load()
        yield from HTMLLoader(confluence_path).load()


# Test
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        data_dir = sys.argv[1]
    else:
        data_dir = "../data"
    
    print(f"Loading documents from: {data_dir}")
    
    for doc in load_all_documents(data_dir):
        print(f"\n{'='*60}")
        print(f"Source: {doc.source_type} | {doc.source_path}")
        print(f"Metadata: {doc.metadata}")
        print(f"Content preview: {doc.content[:200]}...")
