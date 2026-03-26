# Cleanup & Re-Spin Guide — Platform Health Insight Assistant

> **Last Destroyed**: 2026-03-26  
> **Account**: 615299759525 (sandboxtest), ap-southeast-2  
> **Status**: All resources destroyed, $0/month cost

---

## What Was Destroyed

| Resource | Method | Verified Gone |
|----------|--------|---------------|
| ECS Cluster + 2 Services + Tasks | `terraform destroy` | ✅ |
| ALB + Target Groups + Listeners | `terraform destroy` | ✅ |
| ECR Repos + Images (18 total) | Manual `batch-delete-image` + `terraform destroy` | ✅ |
| S3 Bucket + 4 documents | Manual `s3 rm --recursive` + `terraform destroy` | ✅ |
| Bedrock Knowledge Base (II5KAPFHJP) | `terraform destroy` | ✅ |
| Bedrock Data Sources (S3, Web, Confluence) | `terraform destroy` | ✅ |
| OpenSearch Serverless Collection | Manual `delete-collection` (created outside TF) | ✅ |
| OpenSearch Policies (enc, net, access) | Manual `delete-security-policy` / `delete-access-policy` | ✅ |
| DynamoDB Tables (checklists, escalations) | `terraform destroy` | ✅ |
| EFS File System + Mount Targets | `terraform destroy` | ✅ |
| Lambda (kb-sync) | `terraform destroy` | ✅ |
| Secrets Manager (confluence creds) | `terraform destroy` | ✅ |
| CloudWatch Log Groups | `terraform destroy` | ✅ |
| Cloud Map Namespace | `terraform destroy` | ✅ |
| IAM Roles + Policies | `terraform destroy` | ✅ |
| Security Groups | `terraform destroy` | ✅ |

**Total**: 49 Terraform resources + 3 manual resources (OpenSearch collection + policies)

---

## How to Re-Spin the Entire Solution

Estimated time: **30-45 minutes** (OpenSearch activation is the bottleneck).

### Prerequisites

```bash
# Verify AWS access
export AWS_PROFILE=sandboxtest
aws sts get-caller-identity

# Verify tools
terraform --version   # >= 1.5
docker --version      # Docker Desktop running
python3 --version     # >= 3.10 (for OpenSearch index creation)
```

### Phase 1: OpenSearch Serverless Collection (START FIRST — takes 10-15 min)

```bash
# Create collection
aws opensearchserverless create-collection \
  --name platform-health-kb \
  --type VECTORSEARCH \
  --region ap-southeast-2

# Create encryption policy
aws opensearchserverless create-security-policy \
  --name platform-health-enc \
  --type encryption \
  --policy '{"Rules":[{"ResourceType":"collection","Resource":["collection/platform-health-kb"]}],"AWSOwnedKey":true}'

# Create network policy (public access for Bedrock)
aws opensearchserverless create-security-policy \
  --name platform-health-net \
  --type network \
  --policy '[{"Rules":[{"ResourceType":"collection","Resource":["collection/platform-health-kb"]},{"ResourceType":"dashboard","Resource":["collection/platform-health-kb"]}],"AllowFromPublic":true}]'

# Poll until ACTIVE (takes 10-15 min)
watch -n 30 'aws opensearchserverless batch-get-collection --names platform-health-kb --query "collectionDetails[0].status" --output text'
```

### Phase 2: Terraform Apply (while OpenSearch activates)

```bash
cd aws-deploy/terraform

# Set Confluence token (get from local .env or password manager)
# IMPORTANT: Include full token with =ABA7B279 suffix
export TF_VAR_confluence_token="ATATT3x...full-token...JGc=ABA7B279"

terraform init
terraform apply
```

**Terraform creates 49 resources** including: ECS cluster, services, ALB, ECR repos, S3 bucket, Bedrock KB, DynamoDB, EFS, Lambda, IAM roles, security groups, CloudWatch log groups.

### Phase 3: Create Vector Index (after OpenSearch is ACTIVE)

```python
# pip install opensearch-py requests-aws4auth boto3
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import boto3

credentials = boto3.Session(profile_name='sandboxtest').get_credentials()
auth = AWS4Auth(credentials.access_key, credentials.secret_key,
    'ap-southeast-2', 'aoss', session_token=credentials.token)

# Get collection endpoint from: aws opensearchserverless batch-get-collection --names platform-health-kb
client = OpenSearch(
    hosts=[{'host': '<COLLECTION_ID>.ap-southeast-2.aoss.amazonaws.com', 'port': 443}],
    http_auth=auth, use_ssl=True, connection_class=RequestsHttpConnection)

client.indices.create('bedrock-knowledge-base-default-index', body={
    "settings": {"index": {"knn": True, "knn.algo_param.ef_search": 512}},
    "mappings": {"properties": {
        "bedrock-knowledge-base-default-vector": {
            "type": "knn_vector", "dimension": 1024,
            "method": {"name": "hnsw", "engine": "faiss",
                "parameters": {"ef_construction": 512, "m": 16}, "space_type": "l2"}},
        "AMAZON_BEDROCK_TEXT_CHUNK": {"type": "text"},
        "AMAZON_BEDROCK_METADATA": {"type": "text"}}}})
```

### Phase 4: Create OpenSearch Access Policy

```bash
# Get the Bedrock KB role ARN from terraform output or:
ROLE_ARN=$(aws iam get-role --role-name platform-health-bedrock-kb --query 'Role.Arn' --output text)
TASK_ROLE_ARN=$(aws iam get-role --role-name platform-health-ecs-task --query 'Role.Arn' --output text)
ACCOUNT_ID=615299759525

aws opensearchserverless create-access-policy \
  --name platform-health-access \
  --type data \
  --policy "[{\"Rules\":[{\"ResourceType\":\"index\",\"Resource\":[\"index/platform-health-kb/*\"],\"Permission\":[\"aoss:*\"]},{\"ResourceType\":\"collection\",\"Resource\":[\"collection/platform-health-kb\"],\"Permission\":[\"aoss:*\"]}],\"Principal\":[\"${ROLE_ARN}\",\"${TASK_ROLE_ARN}\",\"arn:aws:iam::${ACCOUNT_ID}:root\"]}]"
```

### Phase 5: Docker Build & Push

```bash
cd aws-deploy
export ACCOUNT_ID=615299759525
export REGION=ap-southeast-2

# ECR login
aws ecr get-login-password --region $REGION | \
  docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

# Build & push backend
cd agent-backend
docker build --platform linux/amd64 -t platform-health-backend .
docker tag platform-health-backend:latest $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/platform-health/agent-backend:latest
docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/platform-health/agent-backend:latest

# Build & push frontend
cd ../frontend
docker build --platform linux/amd64 -t platform-health-frontend .
docker tag platform-health-frontend:latest $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/platform-health/frontend:latest
docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/platform-health/frontend:latest
```

### Phase 6: Force ECS Redeploy

```bash
aws ecs update-service --cluster platform-health-cluster \
  --service platform-health-backend --force-new-deployment
aws ecs update-service --cluster platform-health-cluster \
  --service platform-health-frontend --force-new-deployment

# Wait for steady state (~2-3 min)
aws ecs wait services-stable --cluster platform-health-cluster \
  --services platform-health-backend platform-health-frontend
```

### Phase 7: Upload Documents & Sync Data Sources

```bash
# Upload S3 docs (from local documents/ folder or backup)
aws s3 sync documents/ s3://platform-health-kb-documents-<ACCOUNT_ID>/documents/

# Sync KB data sources (one at a time — max 1 concurrent)
KB_ID=$(aws bedrock-agent list-knowledge-bases --query 'knowledgeBaseSummaries[0].knowledgeBaseId' --output text)

# Wait for S3 Lambda auto-sync to complete, then:
aws bedrock-agent start-ingestion-job --knowledge-base-id $KB_ID --data-source-id <WEB_DS_ID>
# Wait for completion...
aws bedrock-agent start-ingestion-job --knowledge-base-id $KB_ID --data-source-id <CONFLUENCE_DS_ID>
```

### Phase 8: Verify

```bash
# Health check
ALB_DNS=$(aws elbv2 describe-load-balancers --names platform-health-alb --query 'LoadBalancers[0].DNSName' --output text)
curl -s http://$ALB_DNS/health

# Test query
curl -s -X POST http://$ALB_DNS/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is Karpenter?"}' | python3 -m json.tool | head -5
```

---

## Destroy Checklist (For Next Time)

When you want to tear down again:

```bash
# 1. Empty S3 (terraform can't delete non-empty buckets)
aws s3 rm s3://platform-health-kb-documents-615299759525/ --recursive

# 2. Delete ECR images (terraform can't delete repos with images unless force_delete=true)
for repo in "platform-health/agent-backend" "platform-health/frontend"; do
  images=$(aws ecr list-images --repository-name "$repo" --query 'imageIds[*]' --output json)
  [ "$images" != "[]" ] && aws ecr batch-delete-image --repository-name "$repo" --image-ids "$images"
done

# 3. Terraform destroy
cd terraform
export TF_VAR_confluence_token="dummy"  # just needs a value to plan
terraform destroy -auto-approve

# 4. Delete OpenSearch collection + policies (created manually)
COLLECTION_ID=$(aws opensearchserverless list-collections --query 'collectionSummaries[?name==`platform-health-kb`].id' --output text)
aws opensearchserverless delete-collection --id $COLLECTION_ID
aws opensearchserverless delete-security-policy --name platform-health-enc --type encryption
aws opensearchserverless delete-security-policy --name platform-health-net --type network
aws opensearchserverless delete-access-policy --name platform-health-access --type data

# 5. Verify (should all return empty)
aws ecs list-clusters --query 'clusterArns[?contains(@,`platform-health`)]'
aws s3api list-buckets --query 'Buckets[?contains(Name,`platform-health`)]'
aws opensearchserverless list-collections --query 'collectionSummaries[?contains(name,`platform-health`)]'
```

---

## Files Preserved Locally

All code, tutorials, and docs remain in `aws-deploy/` — only AWS resources were destroyed:

```
aws-deploy/
├── terraform/                  # Re-run to recreate all 49 resources
├── agent-backend/              # Docker build source (graph.py = M5 ReAct loop)
├── frontend/                   # Streamlit UI
├── lambda/                     # S3 event trigger
├── documents/                  # S3 upload source (4 docs)
├── tutorials/                  # Steps 09-18
├── SESSION-HANDOFF.md
├── TROUBLESHOOTING.md          # 14 real issues
├── OPERATIONS-GUIDE.md
├── REBUILD-PLAYBOOK.md
├── AWS-MANAGED-RAG-VS-LOCAL-RAG.md
├── E2E-VALIDATION-REPORT.md
└── CLEANUP-AND-RESPIN.md       # This file
```

---

*All AWS resources verified destroyed on 2026-03-26. Monthly cost: $0.*
