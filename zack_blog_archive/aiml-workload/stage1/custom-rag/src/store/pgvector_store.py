"""
Vector store implementation using PostgreSQL + pgvector.

WHY PGVECTOR?
- Free and open source
- Runs anywhere (local Docker, RDS, Aurora)
- SQL interface (familiar, powerful filtering)
- Good performance for <1M vectors
- Supports HNSW index (fast approximate search)

ALTERNATIVES:
- Qdrant: Better performance, more features, separate service
- Pinecone: Managed, easy, but external dependency
- OpenSearch: AWS native, expensive minimum
"""

import json
from dataclasses import dataclass
from typing import Sequence
import psycopg2
from psycopg2.extras import execute_values, Json


@dataclass
class SearchResult:
    """A search result with similarity score."""
    chunk_id: int
    document_id: int
    content: str
    metadata: dict
    similarity: float


class PgVectorStore:
    """
    Vector store using PostgreSQL with pgvector extension.
    
    SCHEMA (from init.sql):
    - documents: Source document metadata
    - chunks: Text chunks with embeddings
    
    INDEX:
    - HNSW for fast approximate nearest neighbor search
    - Cosine similarity (normalized vectors)
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "ragdb",
        user: str = "raguser",
        password: str = "ragpass"
    ):
        self.conn_params = {
            "host": host,
            "port": port,
            "database": database,
            "user": user,
            "password": password
        }
        self._conn = None
    
    @property
    def conn(self):
        """Lazy connection with auto-reconnect."""
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(**self.conn_params)
        return self._conn
    
    def close(self):
        """Close the connection."""
        if self._conn and not self._conn.closed:
            self._conn.close()
    
    # -------------------------------------------------------------------------
    # Document Operations
    # -------------------------------------------------------------------------
    
    def add_document(
        self,
        source_type: str,
        source_path: str,
        title: str,
        content: str,
        metadata: dict = None
    ) -> int:
        """
        Add a source document and return its ID.
        
        Documents are the original files (PDFs, CSVs, etc.)
        Chunks reference documents for citation tracking.
        """
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO documents (source_type, source_path, title, content, metadata)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (source_type, source_path, title, content, Json(metadata or {})))
            
            doc_id = cur.fetchone()[0]
            self.conn.commit()
            return doc_id
    
    def get_document(self, doc_id: int) -> dict | None:
        """Get a document by ID."""
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT id, source_type, source_path, title, content, metadata
                FROM documents WHERE id = %s
            """, (doc_id,))
            
            row = cur.fetchone()
            if row:
                return {
                    "id": row[0],
                    "source_type": row[1],
                    "source_path": row[2],
                    "title": row[3],
                    "content": row[4],
                    "metadata": row[5]
                }
            return None
    
    # -------------------------------------------------------------------------
    # Chunk Operations
    # -------------------------------------------------------------------------
    
    def add_chunks(
        self,
        document_id: int,
        chunks: list[dict]  # [{"content": str, "embedding": list, "metadata": dict}, ...]
    ) -> list[int]:
        """
        Add multiple chunks for a document.
        
        BATCH INSERT for performance - much faster than individual inserts.
        """
        with self.conn.cursor() as cur:
            values = [
                (
                    document_id,
                    i,
                    chunk["content"],
                    chunk["embedding"],
                    Json(chunk.get("metadata", {}))
                )
                for i, chunk in enumerate(chunks)
            ]
            
            execute_values(
                cur,
                """
                INSERT INTO chunks (document_id, chunk_index, content, embedding, metadata)
                VALUES %s
                RETURNING id
                """,
                values,
                template="(%s, %s, %s, %s::vector, %s)"
            )
            
            chunk_ids = [row[0] for row in cur.fetchall()]
            self.conn.commit()
            return chunk_ids
    
    def add_chunk(
        self,
        document_id: int,
        chunk_index: int,
        content: str,
        embedding: list[float],
        metadata: dict = None
    ) -> int:
        """Add a single chunk."""
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO chunks (document_id, chunk_index, content, embedding, metadata)
                VALUES (%s, %s, %s, %s::vector, %s)
                RETURNING id
            """, (document_id, chunk_index, content, embedding, Json(metadata or {})))
            
            chunk_id = cur.fetchone()[0]
            self.conn.commit()
            return chunk_id
    
    # -------------------------------------------------------------------------
    # Search Operations
    # -------------------------------------------------------------------------
    
    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        source_type: str = None,
        similarity_threshold: float = 0.0
    ) -> list[SearchResult]:
        """
        Search for similar chunks using vector similarity.
        
        USES:
        - Cosine similarity (1 - cosine distance)
        - HNSW index for fast approximate search
        - Optional filtering by source type
        
        PARAMETERS:
        - query_embedding: The embedded query
        - top_k: Number of results to return
        - source_type: Filter by source (e.g., 'servicenow')
        - similarity_threshold: Minimum similarity score
        """
        with self.conn.cursor() as cur:
            if source_type:
                cur.execute("""
                    SELECT 
                        c.id,
                        c.document_id,
                        c.content,
                        c.metadata,
                        1 - (c.embedding <=> %s::vector) AS similarity
                    FROM chunks c
                    WHERE c.metadata->>'source_type' = %s
                    ORDER BY c.embedding <=> %s::vector
                    LIMIT %s
                """, (query_embedding, source_type, query_embedding, top_k))
            else:
                cur.execute("""
                    SELECT 
                        c.id,
                        c.document_id,
                        c.content,
                        c.metadata,
                        1 - (c.embedding <=> %s::vector) AS similarity
                    FROM chunks c
                    ORDER BY c.embedding <=> %s::vector
                    LIMIT %s
                """, (query_embedding, query_embedding, top_k))
            
            results = []
            for row in cur.fetchall():
                if row[4] >= similarity_threshold:
                    results.append(SearchResult(
                        chunk_id=row[0],
                        document_id=row[1],
                        content=row[2],
                        metadata=row[3],
                        similarity=row[4]
                    ))
            
            return results
    
    def hybrid_search(
        self,
        query_embedding: list[float],
        query_text: str,
        top_k: int = 5,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3
    ) -> list[SearchResult]:
        """
        Hybrid search combining vector similarity and keyword matching.
        
        WHY HYBRID?
        - Vector search: Good for semantic similarity ("restart deployment" ≈ "rollout restart")
        - Keyword search: Good for exact matches (incident IDs, error codes)
        - Combined: Best of both worlds
        
        EXAMPLE:
        - Query: "INC0012345 database timeout"
        - Vector finds: Similar database issues
        - Keyword finds: Exact incident INC0012345
        - Hybrid: Ranks exact match higher
        """
        with self.conn.cursor() as cur:
            # This uses PostgreSQL full-text search combined with vector search
            cur.execute("""
                WITH vector_results AS (
                    SELECT 
                        c.id,
                        c.document_id,
                        c.content,
                        c.metadata,
                        1 - (c.embedding <=> %s::vector) AS vector_score
                    FROM chunks c
                    ORDER BY c.embedding <=> %s::vector
                    LIMIT %s * 2
                ),
                keyword_results AS (
                    SELECT 
                        c.id,
                        ts_rank(to_tsvector('english', c.content), plainto_tsquery('english', %s)) AS keyword_score
                    FROM chunks c
                    WHERE to_tsvector('english', c.content) @@ plainto_tsquery('english', %s)
                )
                SELECT 
                    v.id,
                    v.document_id,
                    v.content,
                    v.metadata,
                    (v.vector_score * %s + COALESCE(k.keyword_score, 0) * %s) AS combined_score
                FROM vector_results v
                LEFT JOIN keyword_results k ON v.id = k.id
                ORDER BY combined_score DESC
                LIMIT %s
            """, (
                query_embedding, query_embedding, top_k,
                query_text, query_text,
                vector_weight, keyword_weight,
                top_k
            ))
            
            results = []
            for row in cur.fetchall():
                results.append(SearchResult(
                    chunk_id=row[0],
                    document_id=row[1],
                    content=row[2],
                    metadata=row[3],
                    similarity=row[4]
                ))
            
            return results
    
    # -------------------------------------------------------------------------
    # Utility Operations
    # -------------------------------------------------------------------------
    
    def get_stats(self) -> dict:
        """Get statistics about the vector store."""
        with self.conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM documents")
            doc_count = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM chunks")
            chunk_count = cur.fetchone()[0]
            
            cur.execute("""
                SELECT metadata->>'source_type', COUNT(*) 
                FROM chunks 
                GROUP BY metadata->>'source_type'
            """)
            by_source = dict(cur.fetchall())
            
            return {
                "documents": doc_count,
                "chunks": chunk_count,
                "by_source": by_source
            }
    
    def clear(self):
        """Clear all data (for testing)."""
        with self.conn.cursor() as cur:
            cur.execute("TRUNCATE chunks, documents RESTART IDENTITY CASCADE")
            self.conn.commit()


# Test
if __name__ == "__main__":
    print("Testing PgVectorStore...")
    
    try:
        store = PgVectorStore()
        
        # Test connection
        stats = store.get_stats()
        print(f"Connected! Current stats: {stats}")
        
        # Add test document
        doc_id = store.add_document(
            source_type="test",
            source_path="/test/doc.md",
            title="Test Document",
            content="This is a test document for vector search.",
            metadata={"test": True}
        )
        print(f"Added document with ID: {doc_id}")
        
        # Add test chunk with fake embedding
        fake_embedding = [0.1] * 1024  # Titan v2 dimensions
        chunk_id = store.add_chunk(
            document_id=doc_id,
            chunk_index=0,
            content="This is a test chunk about Kubernetes deployments.",
            embedding=fake_embedding,
            metadata={"source_type": "test"}
        )
        print(f"Added chunk with ID: {chunk_id}")
        
        # Search
        results = store.search(fake_embedding, top_k=5)
        print(f"Search returned {len(results)} results")
        for r in results:
            print(f"  - {r.content[:50]}... (similarity: {r.similarity:.4f})")
        
        # Cleanup
        store.clear()
        print("Cleared test data")
        
        store.close()
        
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure PostgreSQL is running: docker-compose up -d")
