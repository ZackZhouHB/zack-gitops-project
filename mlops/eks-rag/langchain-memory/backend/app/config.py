import os
from typing import Optional

class Config:
    """Configuration class for LangChain-based AWS EKS RAG application"""
    
    # AWS Configuration
    aws_region: str = os.getenv("AWS_REGION", "ap-southeast-2")
    
    # S3 Configuration - SEPARATE BUCKET for isolation
    s3_bucket: str = os.getenv("S3_BUCKET_NAME", "")
    
    # Weaviate Configuration
    weaviate_host: str = os.getenv("WEAVIATE_HOST", "weaviate-service.langchain.svc.cluster.local")
    weaviate_port: str = os.getenv("WEAVIATE_PORT", "8080")
    weaviate_class_name: str = os.getenv("WEAVIATE_CLASS_NAME", "DocumentsLangChain")  # Separate schema
    
    # Bedrock Configuration
    bedrock_model_id: str = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-5-haiku-20241022-v1:0")
    embedding_model_id: str = os.getenv("EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v1")
    
    # EFS Configuration - SEPARATE SUBDIRECTORY for isolation
    efs_mount_path: str = os.getenv("EFS_MOUNT_PATH", "/efs")
    efs_chat_subdir: str = os.getenv("EFS_CHAT_SUBDIR", "langchain_chat_history")  # Separate path
    
    # Application Configuration
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    # LangChain specific configuration
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "1000"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "200"))
    max_tokens: int = int(os.getenv("MAX_TOKENS", "4000"))
    temperature: float = float(os.getenv("TEMPERATURE", "0.1"))
    
    def __init__(self):
        """Initialize configuration and validate required settings"""
        self._validate_config()
    
    def _validate_config(self):
        """Validate that required configuration is present"""
        required_configs = [
            ("S3_BUCKET_NAME", self.s3_bucket),
            ("WEAVIATE_HOST", self.weaviate_host)
        ]
        
        missing_configs = []
        for name, value in required_configs:
            if not value:
                missing_configs.append(name)
        
        if missing_configs:
            raise ValueError(f"Missing required configuration: {', '.join(missing_configs)}")
    
    def get_chat_history_path(self) -> str:
        """Get the full path for chat history storage - SEPARATE from original"""
        return os.path.join(self.efs_mount_path, self.efs_chat_subdir)
    
    @property
    def weaviate_url(self) -> str:
        """Get full Weaviate URL"""
        return f"http://{self.weaviate_host}:{self.weaviate_port}"
    
    def __str__(self) -> str:
        """String representation of configuration (without sensitive data)"""
        return f"""Config(
    aws_region={self.aws_region},
    s3_bucket={self.s3_bucket},
    weaviate_host={self.weaviate_host},
    weaviate_class_name={self.weaviate_class_name},
    efs_chat_path={self.get_chat_history_path()},
    chunk_size={self.chunk_size},
    chunk_overlap={self.chunk_overlap}
)"""
