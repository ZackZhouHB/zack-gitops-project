"""Advanced chunking strategies"""
from typing import List, Dict
from langchain.text_splitter import RecursiveCharacterTextSplitter

class Chunker:
    """Smart chunking with metadata preservation"""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    
    def chunk(self, content: str, metadata: Dict) -> List[Dict]:
        """Chunk content and attach metadata to each chunk"""
        chunks = self.splitter.split_text(content)
        
        return [
            {
                "content": chunk,
                "chunk_id": i,
                "source": metadata.get("filename", "unknown"),
                "format": metadata.get("format", "unknown"),
                "total_chunks": len(chunks),
            }
            for i, chunk in enumerate(chunks)
        ]
