"""
Main ingestion script - loads, chunks, embeds, and stores documents.

USAGE:
    python -m src.ingest.main --data-dir ./data

STEPS:
1. Load documents from data directory
2. Chunk documents using appropriate strategy
3. Generate embeddings
4. Store in pgvector
"""

import argparse
from pathlib import Path

from .loaders import load_all_documents, Document
from .chunker import chunk_documents, Chunk
from ..embed.embedder import BedrockEmbedder, HybridEmbedder
from ..store.pgvector_store import PgVectorStore


def ingest_documents(
    data_dir: str,
    use_bedrock: bool = True,
    clear_existing: bool = False
):
    """
    Main ingestion pipeline.
    
    FLOW:
    1. Load all documents from data directory
    2. For each document:
       a. Store document metadata
       b. Chunk the document
       c. Embed all chunks
       d. Store chunks with embeddings
    """
    print(f"Starting ingestion from: {data_dir}")
    
    # Initialize components
    store = PgVectorStore()
    
    if use_bedrock:
        embedder = BedrockEmbedder()
        print("Using Bedrock Titan embeddings")
    else:
        embedder = HybridEmbedder(prefer_bedrock=False)
        print("Using Ollama embeddings")
    
    if clear_existing:
        print("Clearing existing data...")
        store.clear()
    
    # Track stats
    total_docs = 0
    total_chunks = 0
    
    # Load and process documents
    print("\nLoading documents...")
    documents = list(load_all_documents(data_dir))
    print(f"Found {len(documents)} documents")
    
    for doc in documents:
        print(f"\nProcessing: {doc.source_type} - {doc.metadata.get('filename', doc.source_path)}")
        
        # Store document
        doc_id = store.add_document(
            source_type=doc.source_type,
            source_path=doc.source_path,
            title=doc.metadata.get('title', doc.metadata.get('filename', 'Untitled')),
            content=doc.content,
            metadata=doc.metadata
        )
        
        # Chunk document
        chunks = list(chunk_documents(iter([doc])))
        print(f"  Created {len(chunks)} chunks")
        
        if not chunks:
            continue
        
        # Embed chunks
        print(f"  Embedding chunks...")
        chunk_texts = [c.content for c in chunks]
        embeddings = embedder.embed_batch(chunk_texts)
        
        # Prepare chunks for storage
        chunk_data = [
            {
                "content": chunk.content,
                "embedding": embedding,
                "metadata": {
                    **chunk.metadata,
                    "chunk_index": chunk.chunk_index,
                    "document_id": chunk.document_id
                }
            }
            for chunk, embedding in zip(chunks, embeddings)
        ]
        
        # Store chunks
        store.add_chunks(doc_id, chunk_data)
        
        total_docs += 1
        total_chunks += len(chunks)
    
    # Print summary
    print("\n" + "="*60)
    print("INGESTION COMPLETE")
    print("="*60)
    print(f"Documents processed: {total_docs}")
    print(f"Chunks created: {total_chunks}")
    
    stats = store.get_stats()
    print(f"\nDatabase stats:")
    print(f"  Total documents: {stats['documents']}")
    print(f"  Total chunks: {stats['chunks']}")
    print(f"  By source: {stats['by_source']}")
    
    store.close()


def main():
    parser = argparse.ArgumentParser(description="Ingest documents into RAG system")
    parser.add_argument(
        "--data-dir",
        type=str,
        default="./data",
        help="Directory containing documents to ingest"
    )
    parser.add_argument(
        "--use-ollama",
        action="store_true",
        help="Use Ollama instead of Bedrock for embeddings"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing data before ingesting"
    )
    
    args = parser.parse_args()
    
    ingest_documents(
        data_dir=args.data_dir,
        use_bedrock=not args.use_ollama,
        clear_existing=args.clear
    )


if __name__ == "__main__":
    main()
