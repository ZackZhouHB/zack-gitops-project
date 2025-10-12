# LangChain-based RAG Backend

This is the LangChain-optimized version of the RAG backend, designed to simplify and standardize the RAG pipeline using industry-standard components.

## Key Improvements over Manual Backend

### Code Simplification
- **Document Processing**: Uses LangChain's `RecursiveCharacterTextSplitter` instead of custom chunking logic
- **Vector Store**: Uses LangChain's `Weaviate` integration instead of custom client
- **RAG Chain**: Uses `RetrievalQA` and `ConversationalRetrievalChain` instead of manual orchestration
- **LLM Integration**: Uses LangChain's `Bedrock` wrapper instead of direct API calls

### Architecture Benefits
- **Standardization**: Industry-standard patterns and interfaces
- **Maintainability**: ~70% less custom code to maintain
- **Extensibility**: Easy to swap components (different LLMs, vector stores)
- **Memory Management**: Built-in conversation memory and context handling

## Components

### Core Files
- `main.py` - FastAPI application with LangChain integration
- `langchain_rag_service.py` - Main RAG service using LangChain components
- `config.py` - Configuration management

### LangChain Components Used
- **Document Loaders**: For processing various file types
- **Text Splitters**: `RecursiveCharacterTextSplitter` for intelligent chunking
- **Vector Stores**: `Weaviate` integration with automatic embedding
- **Embeddings**: `BedrockEmbeddings` for AWS Bedrock integration
- **LLMs**: `Bedrock` wrapper for Claude models
- **Chains**: `RetrievalQA` and `ConversationalRetrievalChain`
- **Memory**: `ConversationBufferMemory` for chat context

## API Endpoints

Same endpoints as the manual backend for compatibility:
- `POST /upload` - Upload and process documents
- `POST /query` - Query documents with RAG
- `GET /documents` - List processed documents
- `GET /health` - Health check
- `GET /chat-history` - Get conversation history
- `DELETE /documents/{id}` - Delete documents

## Environment Variables

```bash
AWS_REGION=ap-southeast-2
S3_BUCKET_NAME=your-bucket-name
WEAVIATE_HOST=weaviate-service.rag-system.svc.cluster.local
WEAVIATE_PORT=8080
BEDROCK_MODEL_ID=anthropic.claude-3-5-haiku-20241022-v1:0
EMBEDDING_MODEL_ID=amazon.titan-embed-text-v1
EFS_MOUNT_PATH=/efs
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
MAX_TOKENS=4000
TEMPERATURE=0.1
```

## Building and Running

```bash
# Build Docker image
docker build -t rag-backend-langchain .

# Run locally
docker run -p 8000:8000 \
  -e AWS_REGION=ap-southeast-2 \
  -e S3_BUCKET_NAME=your-bucket \
  rag-backend-langchain
```

## Deployment

This backend is designed to be a drop-in replacement for the manual backend:
- Same Kubernetes deployment structure
- Same service configuration
- Same external dependencies (Weaviate, S3, EFS, Bedrock)
- Compatible API interface

## Performance Considerations

- **Memory Usage**: LangChain adds some overhead but provides better memory management
- **Startup Time**: Slightly longer due to LangChain initialization
- **Query Performance**: Similar or better due to optimized retrieval chains
- **Scalability**: Better horizontal scaling due to standardized components
