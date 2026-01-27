from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # AWS
    aws_region: str = "ap-southeast-2"
    
    # OpenSearch Serverless
    opensearch_endpoint: str = ""
    opensearch_index: str = "documents"
    
    # Bedrock
    bedrock_model_id: str = "anthropic.claude-3-haiku-20240307-v1:0"
    embedding_model_id: str = "amazon.titan-embed-text-v2:0"
    
    # S3
    documents_bucket: str = ""
    
    # SQS
    sqs_queue_url: str = ""
    
    # DynamoDB
    dynamodb_jobs_table: str = ""
    dynamodb_sessions_table: str = ""
    
    # Cognito
    cognito_user_pool_id: str = ""
    cognito_client_id: str = ""
    
    # Redis
    redis_host: str = "redis-master.rag.svc.cluster.local"
    redis_port: int = 6379
    
    class Config:
        env_file = ".env"

settings = Settings()
