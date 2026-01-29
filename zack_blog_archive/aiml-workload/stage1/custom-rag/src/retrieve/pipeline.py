"""
RAG Query Pipeline - ties everything together.

FLOW:
1. User asks question
2. Embed the question
3. Search vector store (hybrid: vector + keyword)
4. Format context from retrieved chunks
5. Generate answer with Bedrock LLM
6. Return answer with citations
"""

import json
from dataclasses import dataclass
from typing import Sequence
import boto3

from ..store.pgvector_store import PgVectorStore, SearchResult
from ..embed.embedder import BedrockEmbedder


@dataclass
class Citation:
    """A citation to a source document."""
    source_type: str
    source_path: str
    content_preview: str
    similarity: float
    metadata: dict


@dataclass
class RAGResponse:
    """Response from the RAG pipeline."""
    answer: str
    citations: list[Citation]
    query: str
    model: str


class RAGPipeline:
    """
    Complete RAG pipeline for question answering.
    
    COMPONENTS:
    - Embedder: Converts text to vectors (Bedrock Titan)
    - Store: Vector database (pgvector)
    - LLM: Generates answers (Bedrock Claude)
    
    RETRIEVAL STRATEGY:
    - Hybrid search by default (vector + keyword)
    - Falls back to vector-only if hybrid fails
    """
    
    def __init__(
        self,
        store: PgVectorStore = None,
        embedder: BedrockEmbedder = None,
        llm_model: str = "anthropic.claude-3-haiku-20240307-v1:0",
        profile: str = "default",
        region: str = "ap-southeast-2"
    ):
        self.store = store or PgVectorStore()
        self.embedder = embedder or BedrockEmbedder(profile=profile, region=region)
        self.llm_model = llm_model
        
        session = boto3.Session(profile_name=profile, region_name=region)
        self.bedrock = session.client("bedrock-runtime")
    
    def query(
        self,
        question: str,
        top_k: int = 5,
        use_hybrid: bool = True,
        source_type: str = None
    ) -> RAGResponse:
        """
        Answer a question using RAG.
        
        STEPS:
        1. Embed the question
        2. Retrieve relevant chunks
        3. Build context from chunks
        4. Generate answer with LLM
        5. Return answer with citations
        """
        # 1. Embed the question
        query_embedding = self.embedder.embed(question)
        
        # 2. Retrieve relevant chunks
        if use_hybrid:
            try:
                results = self.store.hybrid_search(
                    query_embedding=query_embedding,
                    query_text=question,
                    top_k=top_k
                )
            except Exception:
                # Fall back to vector-only
                results = self.store.search(
                    query_embedding=query_embedding,
                    top_k=top_k,
                    source_type=source_type
                )
        else:
            results = self.store.search(
                query_embedding=query_embedding,
                top_k=top_k,
                source_type=source_type
            )
        
        # 3. Build context from chunks
        context = self._build_context(results)
        
        # 4. Generate answer
        answer = self._generate_answer(question, context)
        
        # 5. Build citations
        citations = self._build_citations(results)
        
        return RAGResponse(
            answer=answer,
            citations=citations,
            query=question,
            model=self.llm_model
        )
    
    def _build_context(self, results: list[SearchResult]) -> str:
        """
        Build context string from search results.
        
        FORMAT:
        Each chunk is labeled with source for the LLM to cite.
        """
        if not results:
            return "No relevant information found."
        
        context_parts = []
        for i, result in enumerate(results, 1):
            source = result.metadata.get('source_type', 'unknown')
            source_path = result.metadata.get('filename', result.metadata.get('incident_number', 'unknown'))
            
            context_parts.append(f"""
[Source {i}: {source} - {source_path}]
{result.content}
""")
        
        return "\n---\n".join(context_parts)
    
    def _generate_answer(self, question: str, context: str) -> str:
        """
        Generate answer using Bedrock LLM.
        
        PROMPT DESIGN:
        - Clear instruction to use only provided context
        - Request for citations
        - Instruction to say "I don't know" if not in context
        """
        prompt = f"""You are a helpful cloud engineering assistant. Answer the question based ONLY on the provided context. If the answer is not in the context, say "I don't have information about that in my knowledge base."

When you use information from the context, cite the source number (e.g., [Source 1]).

Context:
{context}

Question: {question}

Answer:"""
        
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        response = self.bedrock.invoke_model(
            modelId=self.llm_model,
            body=json.dumps(body)
        )
        
        result = json.loads(response["body"].read())
        return result["content"][0]["text"]
    
    def _build_citations(self, results: list[SearchResult]) -> list[Citation]:
        """Build citation objects from search results."""
        citations = []
        for result in results:
            citations.append(Citation(
                source_type=result.metadata.get('source_type', 'unknown'),
                source_path=result.metadata.get('filename', 
                            result.metadata.get('incident_number', 'unknown')),
                content_preview=result.content[:200] + "..." if len(result.content) > 200 else result.content,
                similarity=result.similarity,
                metadata=result.metadata
            ))
        return citations


class StreamingRAGPipeline(RAGPipeline):
    """
    RAG pipeline with streaming response.
    
    For chat UIs where you want to show the answer as it's generated.
    """
    
    def query_stream(
        self,
        question: str,
        top_k: int = 5,
        use_hybrid: bool = True
    ):
        """
        Stream the answer as it's generated.
        
        YIELDS:
        - Text chunks as they arrive
        - Final yield includes citations
        """
        # 1-2. Embed and retrieve (same as non-streaming)
        query_embedding = self.embedder.embed(question)
        
        if use_hybrid:
            results = self.store.hybrid_search(
                query_embedding=query_embedding,
                query_text=question,
                top_k=top_k
            )
        else:
            results = self.store.search(
                query_embedding=query_embedding,
                top_k=top_k
            )
        
        # 3. Build context
        context = self._build_context(results)
        
        # 4. Generate with streaming
        prompt = f"""You are a helpful cloud engineering assistant. Answer the question based ONLY on the provided context. If the answer is not in the context, say "I don't have information about that in my knowledge base."

When you use information from the context, cite the source number (e.g., [Source 1]).

Context:
{context}

Question: {question}

Answer:"""
        
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        response = self.bedrock.invoke_model_with_response_stream(
            modelId=self.llm_model,
            body=json.dumps(body)
        )
        
        for event in response["body"]:
            chunk = json.loads(event["chunk"]["bytes"])
            if chunk["type"] == "content_block_delta":
                yield {"type": "text", "content": chunk["delta"]["text"]}
        
        # Yield citations at the end
        yield {"type": "citations", "citations": self._build_citations(results)}


# Test
if __name__ == "__main__":
    print("RAG Pipeline module loaded.")
    print("To test, run the full pipeline after indexing documents.")
    print()
    print("Example usage:")
    print("""
    from src.retrieve.pipeline import RAGPipeline
    
    pipeline = RAGPipeline()
    
    response = pipeline.query("How do I restart an EKS deployment?")
    
    print(f"Answer: {response.answer}")
    print(f"Citations:")
    for c in response.citations:
        print(f"  - {c.source_type}: {c.source_path}")
    """)
