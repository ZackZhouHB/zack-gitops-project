"""
Text chunking strategies for RAG.

WHY CHUNKING MATTERS:
- LLMs have context limits (can't send entire documents)
- Retrieval works better with focused chunks
- Wrong chunk size = poor retrieval quality

STRATEGIES:
1. Fixed size: Simple, works for most cases
2. Semantic: Split by meaning (paragraphs, sections)
3. Recursive: Try multiple separators, fall back
4. Document-specific: Custom for contracts, code, etc.
"""

import re
from dataclasses import dataclass
from typing import Iterator
from abc import ABC, abstractmethod

from .loaders import Document


@dataclass
class Chunk:
    """A chunk of text ready for embedding."""
    content: str
    metadata: dict
    chunk_index: int
    document_id: str  # Reference to source document


class BaseChunker(ABC):
    """Base class for chunking strategies."""
    
    @abstractmethod
    def chunk(self, document: Document) -> Iterator[Chunk]:
        pass


class FixedSizeChunker(BaseChunker):
    """
    Split text into fixed-size chunks with overlap.
    
    PARAMETERS:
    - chunk_size: Target size in characters (not tokens)
    - overlap: Characters to overlap between chunks
    
    WHY OVERLAP?
    - Prevents cutting sentences/ideas in half
    - Ensures context isn't lost at boundaries
    - Typical: 10-20% of chunk_size
    
    TYPICAL SIZES:
    - 500 chars: Good for precise retrieval
    - 1000 chars: Balance of context and precision
    - 2000 chars: More context, less precise
    """
    
    def __init__(self, chunk_size: int = 1000, overlap: int = 200):
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def chunk(self, document: Document) -> Iterator[Chunk]:
        text = document.content
        doc_id = document.metadata.get('filename', document.source_path)
        
        start = 0
        chunk_index = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence end within last 20% of chunk
                search_start = end - int(self.chunk_size * 0.2)
                sentence_end = self._find_sentence_boundary(text[search_start:end])
                if sentence_end:
                    end = search_start + sentence_end
            
            chunk_text = text[start:end].strip()
            
            if chunk_text:  # Don't yield empty chunks
                yield Chunk(
                    content=chunk_text,
                    metadata={
                        **document.metadata,
                        "chunk_start": start,
                        "chunk_end": end,
                    },
                    chunk_index=chunk_index,
                    document_id=doc_id
                )
                chunk_index += 1
            
            start = end - self.overlap
    
    def _find_sentence_boundary(self, text: str) -> int | None:
        """Find the last sentence boundary in text."""
        # Look for . ! ? followed by space or end
        matches = list(re.finditer(r'[.!?]\s', text))
        if matches:
            return matches[-1].end()
        return None


class SemanticChunker(BaseChunker):
    """
    Split by semantic boundaries (headers, paragraphs).
    
    BEST FOR:
    - Markdown documents with clear structure
    - Runbooks with sections
    - Documentation with headers
    
    HOW IT WORKS:
    1. Split by headers (##, ###)
    2. If section too large, split by paragraphs
    3. If still too large, fall back to fixed size
    """
    
    def __init__(self, max_chunk_size: int = 2000, min_chunk_size: int = 100):
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        self.fallback_chunker = FixedSizeChunker(chunk_size=1000, overlap=200)
    
    def chunk(self, document: Document) -> Iterator[Chunk]:
        text = document.content
        doc_id = document.metadata.get('filename', document.source_path)
        
        # Split by headers
        sections = self._split_by_headers(text)
        
        chunk_index = 0
        for section_title, section_content in sections:
            # If section is small enough, yield as-is
            if len(section_content) <= self.max_chunk_size:
                if len(section_content) >= self.min_chunk_size:
                    yield Chunk(
                        content=section_content,
                        metadata={
                            **document.metadata,
                            "section": section_title,
                        },
                        chunk_index=chunk_index,
                        document_id=doc_id
                    )
                    chunk_index += 1
            else:
                # Section too large, split by paragraphs
                paragraphs = section_content.split('\n\n')
                current_chunk = []
                current_size = 0
                
                for para in paragraphs:
                    if current_size + len(para) > self.max_chunk_size and current_chunk:
                        yield Chunk(
                            content='\n\n'.join(current_chunk),
                            metadata={
                                **document.metadata,
                                "section": section_title,
                            },
                            chunk_index=chunk_index,
                            document_id=doc_id
                        )
                        chunk_index += 1
                        current_chunk = []
                        current_size = 0
                    
                    current_chunk.append(para)
                    current_size += len(para)
                
                # Yield remaining
                if current_chunk:
                    yield Chunk(
                        content='\n\n'.join(current_chunk),
                        metadata={
                            **document.metadata,
                            "section": section_title,
                        },
                        chunk_index=chunk_index,
                        document_id=doc_id
                    )
                    chunk_index += 1
    
    def _split_by_headers(self, text: str) -> list[tuple[str, str]]:
        """Split text by markdown headers."""
        # Pattern for headers (## or ###)
        pattern = r'^(#{1,3})\s+(.+)$'
        
        sections = []
        current_title = "Introduction"
        current_content = []
        
        for line in text.split('\n'):
            match = re.match(pattern, line)
            if match:
                # Save previous section
                if current_content:
                    sections.append((current_title, '\n'.join(current_content).strip()))
                current_title = match.group(2)
                current_content = []
            else:
                current_content.append(line)
        
        # Save last section
        if current_content:
            sections.append((current_title, '\n'.join(current_content).strip()))
        
        return sections


class ServiceNowChunker(BaseChunker):
    """
    Special chunker for ServiceNow incidents.
    
    WHY SPECIAL?
    - Each incident is already a logical unit
    - Don't want to split incident across chunks
    - Want to preserve incident ID for exact matching
    
    STRATEGY:
    - Small incidents: Keep as single chunk
    - Large incidents: Split but keep ID in each chunk
    """
    
    def __init__(self, max_chunk_size: int = 1500):
        self.max_chunk_size = max_chunk_size
    
    def chunk(self, document: Document) -> Iterator[Chunk]:
        text = document.content
        doc_id = document.metadata.get('incident_number', document.source_path)
        
        if len(text) <= self.max_chunk_size:
            # Small enough, keep as single chunk
            yield Chunk(
                content=text,
                metadata=document.metadata,
                chunk_index=0,
                document_id=doc_id
            )
        else:
            # Split but preserve incident header in each chunk
            # Extract header (incident number, category, summary)
            lines = text.split('\n')
            header_lines = []
            content_lines = []
            in_header = True
            
            for line in lines:
                if in_header and (line.startswith('Incident:') or 
                                  line.startswith('Category:') or 
                                  line.startswith('Summary:')):
                    header_lines.append(line)
                else:
                    in_header = False
                    content_lines.append(line)
            
            header = '\n'.join(header_lines)
            content = '\n'.join(content_lines)
            
            # Chunk the content, prepend header to each
            fallback = FixedSizeChunker(
                chunk_size=self.max_chunk_size - len(header) - 50,
                overlap=100
            )
            
            # Create a temporary document for chunking
            temp_doc = Document(
                content=content,
                metadata=document.metadata,
                source_type=document.source_type,
                source_path=document.source_path
            )
            
            for i, chunk in enumerate(fallback.chunk(temp_doc)):
                yield Chunk(
                    content=f"{header}\n\n{chunk.content}",
                    metadata=document.metadata,
                    chunk_index=i,
                    document_id=doc_id
                )


def get_chunker(source_type: str) -> BaseChunker:
    """
    Get appropriate chunker based on source type.
    
    ROUTING:
    - servicenow: ServiceNowChunker (preserve incident structure)
    - confluence/lld: SemanticChunker (use document structure)
    - default: FixedSizeChunker (safe fallback)
    """
    chunkers = {
        "servicenow": ServiceNowChunker(),
        "confluence": SemanticChunker(),
        "lld": SemanticChunker(),
    }
    return chunkers.get(source_type, FixedSizeChunker())


def chunk_documents(documents: Iterator[Document]) -> Iterator[Chunk]:
    """Chunk all documents using appropriate strategy."""
    for doc in documents:
        chunker = get_chunker(doc.source_type)
        yield from chunker.chunk(doc)


# Test
if __name__ == "__main__":
    from .loaders import Document
    
    # Test with sample document
    sample_doc = Document(
        content="""# EKS Troubleshooting Guide

## Pods Stuck in Pending

When pods are stuck in Pending state, check the following:

1. Node resources - are nodes at capacity?
2. Node selectors - do pods match available nodes?
3. PVC status - is persistent storage bound?

### Resolution Steps

First, check node capacity:
```
kubectl describe nodes | grep -A 5 "Allocated resources"
```

Then check pod events:
```
kubectl describe pod <pod-name>
```

## Pods in CrashLoopBackOff

This usually indicates application errors.

### Check Logs

```
kubectl logs <pod-name> --previous
```

Look for exit codes - 137 means OOMKilled.
""",
        metadata={"filename": "eks-guide.md", "source_type": "confluence"},
        source_type="confluence",
        source_path="/docs/eks-guide.md"
    )
    
    print("=== Semantic Chunking ===")
    chunker = SemanticChunker()
    for chunk in chunker.chunk(sample_doc):
        print(f"\n--- Chunk {chunk.chunk_index} ({len(chunk.content)} chars) ---")
        print(f"Section: {chunk.metadata.get('section', 'N/A')}")
        print(chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content)
