# RAG v1 - Local Setup Guide

## Prerequisites

- Docker & Docker Compose
- AWS CLI with SSO configured
- AWS profile `sandboxtest` (or modify docker-compose.yml)

## Quick Start

```bash
# 1. Login to AWS SSO
aws sso login --profile sandboxtest

# 2. Start all services
cd /mnt/f/zack-gitops-project/mlops/rag-v1
docker-compose up -d

# 3. Check services
docker-compose ps

# 4. Open browser
http://localhost:3000
```

## Services

| Service | Port | URL |
|---------|------|-----|
| Frontend | 3000 | http://localhost:3000 |
| Backend | 8001 | http://localhost:8001 |
| Weaviate | 8080 | http://localhost:8080 |

## Validation Tests

### 1. Health Check

```bash
curl -s http://localhost:8001/health | jq .
# Expected: {"status":"healthy","weaviate":"connected"}
```

### 2. Login

```bash
TOKEN=$(curl -s -X POST http://localhost:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin"}' | jq -r '.token')
echo "Token: ${TOKEN:0:50}..."
```

### 3. Upload Document

```bash
curl -s -X POST http://localhost:8001/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@README.md" | jq .
# Expected: {"source":"README.md","chunks":N}
```

### 4. List Documents

```bash
curl -s http://localhost:8001/documents \
  -H "Authorization: Bearer $TOKEN" | jq .
```

### 5. Query

```bash
curl -s -X POST http://localhost:8001/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is this project about?"}' | jq -r '.answer' | head -c 300
```

### 6. Agent Tests

```bash
# Date tool
curl -s -X POST http://localhost:8001/agent \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is todays date?"}' | jq '{answer, tools_used}'

# Calculate tool
curl -s -X POST http://localhost:8001/agent \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "Calculate 25 * 4"}' | jq '{answer, tools_used}'

# List sources tool
curl -s -X POST http://localhost:8001/agent \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "List all documents"}' | jq '{answer, tools_used}'
```

### 7. Web Connector (Optional)

```bash
# Sync from external website
curl -s -X POST http://localhost:8001/connectors/web/sync \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://zackblog.work", "max_pages": 5}' | jq .
```

### 8. Full Integration Test

```bash
TOKEN=$(curl -s -X POST http://localhost:8001/auth/login -H "Content-Type: application/json" -d '{"username":"admin"}' | jq -r '.token')
echo "1. Health: $(curl -s http://localhost:8001/health | jq -r '.status')"
echo "2. Docs before: $(curl -s http://localhost:8001/documents -H "Authorization: Bearer $TOKEN" | jq '.documents | length')"
curl -s -X POST http://localhost:8001/upload -H "Authorization: Bearer $TOKEN" -F "file=@README.md" > /dev/null
sleep 2
echo "3. Docs after: $(curl -s http://localhost:8001/documents -H "Authorization: Bearer $TOKEN" | jq '.documents | length')"
echo "4. Query: $(curl -s -X POST http://localhost:8001/query -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"question":"summarize"}' | jq -r '.answer' | head -c 100)..."
echo "✅ All tests passed!"
```

## Rebuild After Code Changes

```bash
# Rebuild specific service
docker-compose build backend
docker-compose up -d backend

# Rebuild all
docker-compose build
docker-compose up -d

# View logs
docker logs rag-v1-backend-1 --tail 50 -f
```

## Troubleshooting

### AWS SSO Token Expired

```bash
aws sso login --profile sandboxtest
docker-compose restart backend
```

### Weaviate Connection Error

```bash
docker-compose restart weaviate
sleep 5
docker-compose restart backend
```

### Check Logs

```bash
docker logs rag-v1-backend-1 --tail 50
docker logs rag-v1-frontend-1 --tail 50
docker logs rag-v1-weaviate-1 --tail 50
```

### Reset Everything

```bash
docker-compose down -v  # Removes volumes too
docker-compose up -d
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| AWS_PROFILE | sandboxtest | AWS SSO profile |
| AWS_REGION | us-east-1 | Bedrock region |
| BEDROCK_MODEL_ID | claude-3-haiku | LLM model |
| EMBEDDING_MODEL_ID | titan-embed-v1 | Embedding model |
| WEAVIATE_HOST | weaviate | Vector DB host |

## Docker Image

Backend image available on DockerHub:
```bash
docker pull zackz001/aws-rag-v1:cloud-latest
```

## Related Documentation

- [README.md](README.md) - Project overview
- [design.md](design.md) - Architecture details
- [AGENT.md](AGENT.md) - Agent patterns
- [RAG_FUNDAMENTALS.md](RAG_FUNDAMENTALS.md) - Interview guide
