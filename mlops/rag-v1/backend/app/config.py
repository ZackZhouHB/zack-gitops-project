import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # AWS
    aws_region: str = "ap-southeast-2"
    bedrock_model_id: str = "anthropic.claude-3-5-haiku-20241022-v1:0"
    embedding_model_id: str = "amazon.titan-embed-text-v1"
    
    # Weaviate
    weaviate_host: str = "weaviate"
    weaviate_port: int = 8080
    weaviate_class: str = "Document"
    
    # RAG settings
    chunk_size: int = 1000
    chunk_overlap: int = 200
    top_k: int = 5
    
    # Paths
    data_path: str = "/app/data"
    
    @property
    def weaviate_url(self) -> str:
        return f"http://{self.weaviate_host}:{self.weaviate_port}"

settings = Settings()
