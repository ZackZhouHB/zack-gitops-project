# RAG Cloud - AWS Deployment

Production deployment of RAG system on AWS using EKS + OpenSearch Serverless.

## Architecture

```
CloudFront → ALB → EKS (Backend + Worker + Redis)
                      │
         ┌────────────┼────────────┐
         ▼            ▼            ▼
    OpenSearch    Bedrock       S3/SQS
    Serverless    (LLM)        (Storage)
```

## Prerequisites

- AWS CLI configured with `sandboxtest` profile
- Terraform >= 1.0
- kubectl
- Helm 3

## Deployment

### 1. Deploy Infrastructure

```bash
cd terraform

# Initialize
terraform init

# Plan
terraform plan -out=tfplan

# Apply
terraform apply tfplan
```

### 2. Configure kubectl

```bash
aws eks update-kubeconfig --region ap-southeast-2 --name rag-cloud-dev
```

### 3. Deploy Redis

```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
helm install redis bitnami/redis -n rag -f k8s/redis-values.yaml
```

### 4. Build & Push Images

```bash
# Login to ECR
aws ecr get-login-password --region ap-southeast-2 | docker login --username AWS --password-stdin <account>.dkr.ecr.ap-southeast-2.amazonaws.com

# Build and push backend
docker build -t rag-cloud-backend ./backend
docker tag rag-cloud-backend:latest <ecr-url>/rag-cloud-dev-backend:latest
docker push <ecr-url>/rag-cloud-dev-backend:latest
```

### 5. Deploy to EKS

```bash
# Update ConfigMap with terraform outputs
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/serviceaccount.yaml
kubectl apply -f k8s/backend.yaml
kubectl apply -f k8s/worker.yaml
kubectl apply -f k8s/ingress.yaml
```

## Cost Estimate

| Service | Monthly |
|---------|---------|
| EKS Control Plane | $73 |
| EC2 (2x t3.medium) | $60 |
| OpenSearch Serverless | $86 |
| NAT Gateway | $32 |
| ALB | $16 |
| Other (S3, SQS, DynamoDB) | ~$5 |
| **Total** | **~$270** |

## Files

```
rag-cloud/
├── terraform/           # Infrastructure as Code
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
│       ├── opensearch/
│       └── cognito/
│
├── k8s/                 # Kubernetes manifests
│   ├── namespace.yaml
│   ├── backend.yaml
│   ├── worker.yaml
│   ├── ingress.yaml
│   └── redis-values.yaml
│
├── backend/             # Application code (copy from rag-v1)
│
└── docs/
    └── DESIGN.md
```

## Local vs Cloud Mapping

| Local | Cloud |
|-------|-------|
| Weaviate | OpenSearch Serverless |
| docker-compose | EKS |
| In-memory queue | SQS |
| In-memory cache | Redis on EKS |
| Mock JWT | Cognito |
| localhost | ALB + CloudFront |
