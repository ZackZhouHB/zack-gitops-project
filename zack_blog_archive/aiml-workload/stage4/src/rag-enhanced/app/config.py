"""Configuration for RAG Enhanced"""
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # LLM Backend
    llm_backend: str = os.getenv("LLM_BACKEND", "vllm")
    vllm_url: str = os.getenv("VLLM_URL", "http://llm-server:8000")
    
    # Embedding Backend
    embed_backend: str = os.getenv("EMBED_BACKEND", "ollama")
    ollama_url: str = os.getenv("OLLAMA_URL", "http://192.168.50.61:11434")
    embed_model: str = os.getenv("EMBED_MODEL", "nomic-embed-text")
    
    # Bedrock fallback
    aws_region: str = os.getenv("AWS_REGION", "ap-southeast-2")
    bedrock_model_id: str = "anthropic.claude-3-haiku-20240307-v1:0"
    
    # Weaviate
    weaviate_url: str = os.getenv("WEAVIATE_URL", "http://weaviate:8080")
    weaviate_class: str = "Document"
    
    # Chunking defaults
    chunk_size: int = 1000
    chunk_overlap: int = 200
    
    # Retrieval defaults
    default_top_k: int = 5
    default_alpha: float = 0.5  # Hybrid search balance
    use_rerank: bool = True

settings = Settings()
