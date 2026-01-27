# RAG Cloud - AWS Deployment

Production deployment of RAG system on AWS using EKS + OpenSearch Serverless.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              USERS                                       │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────────────┐
│                           CloudFront                                     │
│                      (HTTPS + API routing)                              │
└──────────────┬──────────────────────────────────────┬───────────────────┘
               │                                      │
┌──────────────▼──────────────┐        ┌──────────────▼──────────────┐
│      S3 (Frontend)          │        │         ALB                 │
│   React Static Assets       │        │   (Backend API)             │
└─────────────────────────────┘        └──────────────┬──────────────┘
                                                      │
┌─────────────────────────────────────────────────────▼───────────────────┐
│                              EKS Cluster                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐         │
│  │ Backend Pod     │  │ Worker Pod      │  │ Redis (Helm)    │         │
│  │ (FastAPI)       │  │ (SQS Consumer)  │  │ (Cache)         │         │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘         │
└──────┬──────────────────┬──────────────────┬────────────────────────────┘
       │                  │                  │
┌──────▼──────┐    ┌──────▼──────┐    ┌──────▼──────┐    ┌─────────────┐
│ OpenSearch  │    │   Bedrock   │    │     S3      │    │     SQS     │
│ Serverless  │    │ Claude/Titan│    │  Documents  │    │ Ingest Queue│
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

## Quick Start

### Automated Deployment

```bash
# Deploy everything
./deploy.sh

# Cleanup everything
./deploy.sh destroy
```

### Manual Deployment

See [GUIDE.md](GUIDE.md) for step-by-step instructions.

## Prerequisites

- AWS CLI configured (default profile)
- Terraform >= 1.0
- kubectl
- Helm 3
- Docker
- Node.js (for frontend build)

## Documentation

| Document | Description |
|----------|-------------|
| [GUIDE.md](GUIDE.md) | Step-by-step deployment guide with troubleshooting |
| [DESIGN.md](DESIGN.md) | Architecture design and technical decisions |
| [AGENT.md](AGENT.md) | Agent patterns and AWS Bedrock Agents reference |
| [CLEANUP.md](CLEANUP.md) | Cleanup log and procedures |

## Features

All 26 features from local RAG work in cloud:

| Category | Features |
|----------|----------|
| **Core** | Health check, JWT auth, RBAC |
| **Ingestion** | Sync/async upload, multi-format, web connector |
| **Search** | Vector, keyword, hybrid, reranking |
| **RAG** | Query, streaming, model routing, memory |
| **Agent** | ReAct pattern with 5 tools |
| **Security** | Rate limiting, audit logs, PII filtering |
| **Frontend** | Chat history, markdown rendering, document management |

## Cost Estimate

| Service | Monthly |
|---------|---------|
| EKS Control Plane | $73 |
| EC2 (t3.large node) | $61 |
| OpenSearch Serverless (2 OCUs) | $86 |
| NAT Gateway | $32 |
| ALB | $16 |
| S3, SQS, DynamoDB, CloudFront | ~$5 |
| Bedrock (moderate usage) | ~$28 |
| **Total** | **~$300/month** |

## Key Technical Differences (Local vs Cloud)

| Aspect | Local (rag-v1) | Cloud (rag-cloud) |
|--------|----------------|-------------------|
| Vector DB | Weaviate (1536-dim) | OpenSearch Serverless (1024-dim) |
| Embedding | Titan v1 | Titan v2 |
| Search | script_score | Native kNN |
| Doc IDs | Custom allowed | Auto-generated |
| Queue | In-memory | SQS |
| Frontend | Nginx container | S3 + CloudFront |

## Files

```
rag-cloud/
├── deploy.sh              # Automated deploy/destroy script
├── GUIDE.md               # Deployment guide
├── AGENT.md               # Agent documentation
├── CLEANUP.md             # Cleanup log
│
├── terraform/             # Infrastructure as Code
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   └── modules/
│       ├── vpc/
│       ├── eks/
│       ├── ecr/
│       ├── s3/
│       ├── sqs/
│       ├── dynamodb/
│       └── opensearch/
│
├── k8s/                   # Kubernetes manifests
│   ├── namespace.yaml     # Namespace + ConfigMap
│   ├── serviceaccount.yaml
│   ├── backend.yaml
│   ├── worker.yaml
│   ├── ingress.yaml
│   └── redis-values.yaml
│
├── backend/               # FastAPI application
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── rag/           # RAG service
│   │   ├── db/            # OpenSearch client
│   │   └── agents/        # ReAct agent
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/              # React application
│   ├── src/
│   │   ├── App.jsx
│   │   └── index.css
│   ├── package.json
│   └── vite.config.js
│
└── docs/
    └── DESIGN.md          # Architecture design
```

## Troubleshooting

See [GUIDE.md](GUIDE.md) for common issues:

1. Embedding model not found → Use Titan v2
2. OpenSearch script_score error → Use native kNN
3. Document ID not supported → Remove custom IDs
4. Mixed content error → Route API through CloudFront
5. Chat history lost → Store in localStorage.allChats

## Docker Image

Backend image available on DockerHub:
```bash
docker pull zackz001/aws-rag-v1:cloud-latest
```

## Related

- [rag-v1](../rag-v1/) - Local Docker deployment
- [RAG_FUNDAMENTALS.md](../rag-v1/RAG_FUNDAMENTALS.md) - Interview guide
