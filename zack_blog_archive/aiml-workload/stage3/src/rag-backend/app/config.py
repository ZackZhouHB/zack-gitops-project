import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # LLM Backend: vllm, ollama, or bedrock
    llm_backend: str = os.getenv("LLM_BACKEND", "vllm")
    vllm_url: str = os.getenv("VLLM_URL", "http://llm-server:8000")
    ollama_url: str = os.getenv("OLLAMA_URL", "http://192.168.50.61:11434")
    
    # Embedding Backend: ollama or bedrock
    embed_backend: str = os.getenv("EMBED_BACKEND", "ollama")
    embed_model: str = os.getenv("EMBED_MODEL", "nomic-embed-text")
    
    # Bedrock fallback
    aws_region: str = os.getenv("AWS_REGION", "ap-southeast-2")
    bedrock_model_id: str = "anthropic.claude-3-haiku-20240307-v1:0"
    bedrock_embed_model: str = "amazon.titan-embed-text-v1"
    
    # Weaviate
    weaviate_url: str = os.getenv("WEAVIATE_URL", "http://weaviate:8080")
    weaviate_class: str = "Document"
    
    # RAG settings
    chunk_size: int = 500
    chunk_overlap: int = 50
    top_k: int = 3

settings = Settings()
