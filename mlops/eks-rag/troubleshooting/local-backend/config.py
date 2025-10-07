import os
from typing import Optional

class Config:
    """Configuration class for AWS EKS RAG application"""
    
    # AWS Configuration
    AWS_REGION: str = os.getenv("AWS_REGION", "ap-southeast-2")
    
    # S3 Configuration
    S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "")
    
    # Weaviate Configuration
    WEAVIATE_HOST: str = os.getenv("WEAVIATE_HOST", "weaviate-service.rag-system.svc.cluster.local")
    WEAVIATE_PORT: str = os.getenv("WEAVIATE_PORT", "8080")
    
    # Bedrock Configuration
    BEDROCK_MODEL_ID: str = os.getenv("BEDROCK_MODEL_ID", "apac.anthropic.claude-sonnet-4-20250514-v1:0")
    
    # EFS Configuration
    EFS_MOUNT_PATH: str = os.getenv("EFS_MOUNT_PATH", "/efs")
    
    # Application Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    def __init__(self):
        """Initialize configuration and validate required settings"""
        self._validate_config()
    
    def _validate_config(self):
        """Validate that required configuration is present"""
        required_configs = [
            ("S3_BUCKET_NAME", self.S3_BUCKET_NAME),
            ("WEAVIATE_HOST", self.WEAVIATE_HOST)
        ]
        
        missing_configs = []
        for name, value in required_configs:
            if not value:
                missing_configs.append(name)
        
        if missing_configs:
            raise ValueError(f"Missing required configuration: {', '.join(missing_configs)}")
    
    def get_chat_history_path(self) -> str:
        """Get the full path for chat history storage"""
        return os.path.join(self.EFS_MOUNT_PATH, "chat_history")
    
    def __str__(self) -> str:
        """String representation of configuration (without sensitive data)"""
        return f"""Config(
    AWS_REGION={self.AWS_REGION},
    S3_BUCKET_NAME={self.S3_BUCKET_NAME},
    WEAVIATE_HOST={self.WEAVIATE_HOST},
    BEDROCK_MODEL_ID={self.BEDROCK_MODEL_ID},
    EFS_MOUNT_PATH={self.EFS_MOUNT_PATH}
)"""
