"""Weaviate store — manage the vector database schema and store embedded chunks.

Weaviate organises data into "collections" (like tables in SQL).
We create one collection called "DocumentChunk" that stores:
- The text content
- The embedding vector (1024 dimensions)
- Metadata (title, source, URL, source_type, chunk_index)
"""

import os
import weaviate
from weaviate.classes.config import Configure, Property, DataType, VectorDistances
from dotenv import load_dotenv

load_dotenv()

WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://localhost:8080")
COLLECTION_NAME = "DocumentChunk"


def get_client() -> weaviate.WeaviateClient:
    """Connect to the local Weaviate instance."""
    url = WEAVIATE_URL
    # If running outside Docker, "vectordb" won't resolve — use localhost
    host = url.replace("http://", "").replace("https://", "").split(":")[0]
    port = int(url.split(":")[-1]) if ":" in url.split("//")[-1] else 8080

    if host in ("vectordb", "localhost", "127.0.0.1"):
        host = "localhost"

    client = weaviate.connect_to_local(host=host, port=port)
    return client


def init_weaviate_schema():
    """Create the DocumentChunk collection if it doesn't exist.
    
    This defines the schema — what fields each document chunk has
    and how the vector index is configured.
    """
    client = get_client()

    try:
        if client.collections.exists(COLLECTION_NAME):
            print(f"   Collection '{COLLECTION_NAME}' already exists")
            return

        client.collections.create(
            name=COLLECTION_NAME,
            # We provide our own vectors (from Bedrock Titan), so no vectorizer module
            vectorizer_config=Configure.Vectorizer.none(),
            # Cosine distance is standard for text embeddings
            vector_index_config=Configure.VectorIndex.hnsw(
                distance_metric=VectorDistances.COSINE,
            ),
            properties=[
                Property(name="content", data_type=DataType.TEXT,
                         description="The text content of this chunk"),
                Property(name="title", data_type=DataType.TEXT,
                         description="Title of the source document"),
                Property(name="source", data_type=DataType.TEXT,
                         description="Source identifier (e.g., blog/post/156)"),
                Property(name="url", data_type=DataType.TEXT,
                         description="URL or path to the source document"),
                Property(name="source_type", data_type=DataType.TEXT,
                         description="Type: blog, confluence, or file"),
                Property(name="chunk_index", data_type=DataType.INT,
                         description="Position of this chunk within the document"),
            ],
        )
        print(f"   ✅ Created collection '{COLLECTION_NAME}'")

    finally:
        client.close()


def store_chunks(chunks: list[dict]):
    """Store embedded chunks in Weaviate.
    
    Each chunk must have:
    - content, title, source, url, source_type, chunk_index (properties)
    - embedding (the vector, list of 1024 floats)
    """
    client = get_client()

    try:
        collection = client.collections.get(COLLECTION_NAME)

        # Use batch insert for efficiency
        with collection.batch.dynamic() as batch:
            for chunk in chunks:
                batch.add_object(
                    properties={
                        "content": chunk["content"],
                        "title": chunk["title"],
                        "source": chunk["source"],
                        "url": chunk["url"],
                        "source_type": chunk["source_type"],
                        "chunk_index": chunk["chunk_index"],
                    },
                    vector=chunk["embedding"],
                )

        print(f"   ✅ Stored {len(chunks)} chunks in Weaviate")

    finally:
        client.close()


def get_chunk_count() -> int:
    """Return the total number of chunks stored in Weaviate."""
    client = get_client()
    try:
        if not client.collections.exists(COLLECTION_NAME):
            return 0
        collection = client.collections.get(COLLECTION_NAME)
        result = collection.aggregate.over_all(total_count=True)
        return result.total_count
    finally:
        client.close()
