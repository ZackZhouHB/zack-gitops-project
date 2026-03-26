"""Document ingestion pipeline — load documents into Weaviate for RAG search.

This script loads documents from 3 sources:
1. Blog posts (web crawl from zackblog.work)
2. Confluence pages (API call to Atlassian)
3. Local files (PDFs and Markdown from ./documents/)

Each document is:
1. Loaded and converted to plain text
2. Split into overlapping chunks (~500 tokens each)
3. Embedded using AWS Bedrock Titan Embed V2 (1024 dimensions)
4. Stored in Weaviate with metadata (source, title, URL)

Usage:
    python -m ingestion.ingest          # Ingest all sources
    python -m ingestion.ingest blog     # Ingest blog only
    python -m ingestion.ingest confluence
    python -m ingestion.ingest files
"""

import sys
import os

# Add parent dir to path so we can import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingestion.loaders import load_blog_posts, load_confluence_pages, load_local_files
from ingestion.chunker import chunk_documents
from ingestion.embedder import embed_chunks
from ingestion.weaviate_store import init_weaviate_schema, store_chunks, get_chunk_count


def main():
    """Run the full ingestion pipeline."""
    source_filter = sys.argv[1] if len(sys.argv) > 1 else "all"

    print("=" * 60)
    print("  Teacher Accreditation Agent — Document Ingestion")
    print("=" * 60)

    # Step 0: Ensure Weaviate schema exists
    print("\n📦 Step 0: Initialising Weaviate schema...")
    init_weaviate_schema()
    print(f"   Current chunk count: {get_chunk_count()}")

    # Step 1: Load documents from sources
    documents = []

    if source_filter in ("all", "blog"):
        print("\n🌐 Step 1a: Loading blog posts...")
        blog_docs = load_blog_posts()
        documents.extend(blog_docs)
        print(f"   Loaded {len(blog_docs)} blog posts")

    if source_filter in ("all", "confluence"):
        print("\n📄 Step 1b: Loading Confluence pages...")
        confluence_docs = load_confluence_pages()
        documents.extend(confluence_docs)
        print(f"   Loaded {len(confluence_docs)} Confluence pages")

    if source_filter in ("all", "files"):
        print("\n📁 Step 1c: Loading local files...")
        file_docs = load_local_files()
        documents.extend(file_docs)
        print(f"   Loaded {len(file_docs)} local files")

    if not documents:
        print("\n⚠️  No documents loaded. Nothing to ingest.")
        return

    print(f"\n📊 Total documents loaded: {len(documents)}")

    # Step 2: Chunk documents
    print("\n✂️  Step 2: Chunking documents...")
    chunks = chunk_documents(documents)
    print(f"   Created {len(chunks)} chunks from {len(documents)} documents")

    # Step 3: Embed chunks using Bedrock Titan
    print("\n🧠 Step 3: Embedding chunks via AWS Bedrock Titan...")
    embedded_chunks = embed_chunks(chunks)
    print(f"   Embedded {len(embedded_chunks)} chunks (1024 dimensions each)")

    # Step 4: Store in Weaviate
    print("\n💾 Step 4: Storing in Weaviate...")
    store_chunks(embedded_chunks)
    total = get_chunk_count()
    print(f"   Total chunks in Weaviate: {total}")

    print("\n" + "=" * 60)
    print("  ✅ Ingestion complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
