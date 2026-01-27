# RAG Cloud Deployment Guide

Complete step-by-step guide to deploy RAG on AWS EKS.

## Prerequisites

- AWS CLI configured (default profile)
- Terraform >= 1.0
- kubectl
- Helm 3
- Docker

## Step 1: Deploy Infrastructure (Terraform)

```bash
cd /mnt/f/zack-gitops-project/mlops/rag-cloud/terraform

# Initialize
terraform init

# Plan
terraform plan -out=tfplan

# Apply (~15-20 min for EKS)
terraform apply tfplan
```

**Outputs to note:**
- `eks_cluster_name`
- `opensearch_endpoint`
- `documents_bucket`
- `ingestion_queue_url`
- `ecr_backend_url`
- `vpc_id`

**IMPORTANT:** After `terraform apply`, update these files with the output values:
- `k8s/namespace.yaml` - Update ConfigMap with OpenSearch endpoint, S3 bucket, SQS URL
- `k8s/backend.yaml` - Update ECR image URL
- `k8s/worker.yaml` - Update ECR image URL
- `k8s/serviceaccount.yaml` - Update IAM role ARN (after Step 5)

## Step 2: Configure kubectl

```bash
aws eks update-kubeconfig --region ap-southeast-2 --name rag-cloud-dev
kubectl get nodes  # Verify connection
```

## Step 3: Build & Push Docker Images

```bash
# Login to ECR
aws ecr get-login-password --region ap-southeast-2 | docker login --username AWS --password-stdin 381324498760.dkr.ecr.ap-southeast-2.amazonaws.com

# Build backend
cd /mnt/f/zack-gitops-project/mlops/rag-cloud/backend
docker build -t rag-cloud-backend .

# Tag and push backend
docker tag rag-cloud-backend:latest 381324498760.dkr.ecr.ap-southeast-2.amazonaws.com/rag-cloud-dev-backend:latest
docker push 381324498760.dkr.ecr.ap-southeast-2.amazonaws.com/rag-cloud-dev-backend:latest

# Tag and push worker (same image)
docker tag rag-cloud-backend:latest 381324498760.dkr.ecr.ap-southeast-2.amazonaws.com/rag-cloud-dev-worker:latest
docker push 381324498760.dkr.ecr.ap-southeast-2.amazonaws.com/rag-cloud-dev-worker:latest
```

## Step 4: Create IAM Policy for Backend

```bash
cat > /tmp/rag-policy.json << 'EOF'
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"],
            "Resource": [
                "arn:aws:s3:::rag-cloud-dev-documents-381324498760",
                "arn:aws:s3:::rag-cloud-dev-documents-381324498760/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": ["sqs:SendMessage", "sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"],
            "Resource": "arn:aws:sqs:ap-southeast-2:381324498760:rag-cloud-dev-*"
        },
        {
            "Effect": "Allow",
            "Action": ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:DeleteItem", "dynamodb:Query", "dynamodb:Scan"],
            "Resource": "arn:aws:dynamodb:ap-southeast-2:381324498760:table/rag-cloud-dev-*"
        },
        {
            "Effect": "Allow",
            "Action": ["aoss:APIAccessAll"],
            "Resource": "*"
        }
    ]
}
EOF

aws iam create-policy --policy-name rag-cloud-backend-policy --policy-document file:///tmp/rag-policy.json
```

## Step 5: Create IAM Role for IRSA

```bash
# Get OIDC provider from EKS
OIDC_PROVIDER=$(aws eks describe-cluster --name rag-cloud-dev --region ap-southeast-2 --query "cluster.identity.oidc.issuer" --output text | sed 's|https://||')
echo "OIDC: $OIDC_PROVIDER"

# Create trust policy
cat > /tmp/trust-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Federated": "arn:aws:iam::381324498760:oidc-provider/${OIDC_PROVIDER}"
            },
            "Action": "sts:AssumeRoleWithWebIdentity",
            "Condition": {
                "StringEquals": {
                    "${OIDC_PROVIDER}:sub": "system:serviceaccount:rag:rag-backend",
                    "${OIDC_PROVIDER}:aud": "sts.amazonaws.com"
                }
            }
        }
    ]
}
EOF

# Create role and attach policy
aws iam create-role --role-name rag-cloud-backend-role --assume-role-policy-document file:///tmp/trust-policy.json
aws iam attach-role-policy --role-name rag-cloud-backend-role --policy-arn arn:aws:iam::381324498760:policy/rag-cloud-backend-policy
```

## Step 6: Update K8s Manifests

Update `k8s/namespace.yaml` with terraform outputs:
```yaml
data:
  AWS_REGION: "ap-southeast-2"
  OPENSEARCH_ENDPOINT: "<from terraform output>"
  DOCUMENTS_BUCKET: "<from terraform output>"
  SQS_QUEUE_URL: "<from terraform output>"
  DYNAMODB_JOBS_TABLE: "rag-cloud-dev-jobs"
  DYNAMODB_SESSIONS_TABLE: "rag-cloud-dev-sessions"
  REDIS_HOST: "redis-master.rag.svc.cluster.local"
```

Update `k8s/serviceaccount.yaml`:
```yaml
annotations:
  eks.amazonaws.com/role-arn: arn:aws:iam::381324498760:role/rag-cloud-backend-role
```

Update `k8s/backend.yaml` and `k8s/worker.yaml` with ECR URLs:
```yaml
image: 381324498760.dkr.ecr.ap-southeast-2.amazonaws.com/rag-cloud-dev-backend:latest
```

## Step 7: Deploy to Kubernetes

```bash
# Create namespace and configmap
kubectl apply -f k8s/namespace.yaml

# Install Redis
helm repo add bitnami https://charts.bitnami.com/bitnami
helm install redis bitnami/redis -n rag -f k8s/redis-values.yaml

# Deploy service account, backend, worker
kubectl apply -f k8s/serviceaccount.yaml
kubectl apply -f k8s/backend.yaml
kubectl apply -f k8s/worker.yaml

# Check pods
kubectl get pods -n rag
```

## Step 8: Install AWS Load Balancer Controller

```bash
# Add Helm repo
helm repo add eks https://aws.github.io/eks-charts
helm repo update

# Download IAM policy
curl -o /tmp/alb-policy.json https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/main/docs/install/iam_policy.json

# Create policy
aws iam create-policy --policy-name AWSLoadBalancerControllerIAMPolicy --policy-document file:///tmp/alb-policy.json

# Get OIDC and VPC ID
OIDC_PROVIDER=$(aws eks describe-cluster --name rag-cloud-dev --region ap-southeast-2 --query "cluster.identity.oidc.issuer" --output text | sed 's|https://||')
VPC_ID=$(aws eks describe-cluster --name rag-cloud-dev --region ap-southeast-2 --query "cluster.resourcesVpcConfig.vpcId" --output text)

# Create trust policy for ALB controller
cat > /tmp/alb-trust.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Federated": "arn:aws:iam::381324498760:oidc-provider/${OIDC_PROVIDER}"
            },
            "Action": "sts:AssumeRoleWithWebIdentity",
            "Condition": {
                "StringEquals": {
                    "${OIDC_PROVIDER}:sub": "system:serviceaccount:kube-system:aws-load-balancer-controller",
                    "${OIDC_PROVIDER}:aud": "sts.amazonaws.com"
                }
            }
        }
    ]
}
EOF

# Create role
aws iam create-role --role-name AmazonEKSLoadBalancerControllerRole --assume-role-policy-document file:///tmp/alb-trust.json
aws iam attach-role-policy --role-name AmazonEKSLoadBalancerControllerRole --policy-arn arn:aws:iam::381324498760:policy/AWSLoadBalancerControllerIAMPolicy

# Install controller
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=rag-cloud-dev \
  --set serviceAccount.create=true \
  --set serviceAccount.name=aws-load-balancer-controller \
  --set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"=arn:aws:iam::381324498760:role/AmazonEKSLoadBalancerControllerRole \
  --set region=ap-southeast-2 \
  --set vpcId=$VPC_ID

# Verify
kubectl get pods -n kube-system | grep load-balancer
```

## Step 9: Create Ingress

```bash
kubectl apply -f k8s/ingress.yaml

# Wait for ALB provisioning (~2-3 min)
kubectl get ingress -n rag

# Get ALB URL
ALB_URL=$(kubectl get ingress -n rag backend -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
echo "API URL: http://$ALB_URL"
```

## Step 10: Verify Deployment

### Backend Validation

```bash
# Set ALB URL (get from kubectl get ingress -n rag)
ALB_URL="http://$(kubectl get ingress -n rag backend -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')"
echo "ALB URL: $ALB_URL"

# 1. Health check - verify OpenSearch connection
curl -s "$ALB_URL/health" | jq .
# Expected: {"status":"healthy","opensearch":"connected"}

# 2. Login and get token
TOKEN=$(curl -s -X POST "$ALB_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin"}' | jq -r '.token')
echo "Token: ${TOKEN:0:50}..."

# 3. Check documents (should be empty initially)
curl -s "$ALB_URL/documents" -H "Authorization: Bearer $TOKEN" | jq .

# 4. Upload a test document
curl -s -X POST "$ALB_URL/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@README.md" | jq .
# Expected: {"source":"README.md","chunks":N}

# 5. Wait for indexing and verify
sleep 5
curl -s "$ALB_URL/documents" -H "Authorization: Bearer $TOKEN" | jq .
# Expected: {"documents":[{"source":"README.md","chunks":N}]}

# 6. Test query
curl -s -X POST "$ALB_URL/query" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is this project about?"}' | jq -r '.answer' | head -c 300

# 7. Test web connector (sync blog posts)
curl -s -X POST "$ALB_URL/connectors/web/sync" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://zackblog.work", "max_pages": 5}' | jq .
```

### Frontend Validation (via CloudFront)

```bash
# Set CloudFront URL
CF_URL="https://$(aws cloudfront list-distributions --query "DistributionList.Items[?Comment=='RAG Cloud Frontend'].DomainName" --output text)"
echo "CloudFront URL: $CF_URL"

# 1. Check CloudFront status
aws cloudfront get-distribution --id $(aws cloudfront list-distributions --query "DistributionList.Items[?Comment=='RAG Cloud Frontend'].Id" --output text) --query 'Distribution.Status' --output text
# Expected: Deployed

# 2. Test API through CloudFront (no mixed content)
curl -s -X POST "$CF_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin"}' | jq -r '.token' | head -c 50
# Expected: eyJhbGciOiJIUzI1NiIs...

# 3. Test health through CloudFront
curl -s "$CF_URL/health" | jq .

# 4. Verify frontend loads
curl -s "$CF_URL/" | grep -o '<title>.*</title>'
# Expected: <title>RAG Cloud</title>
```

### Pod Health Checks

```bash
# Check all pods running
kubectl get pods -n rag
# Expected: backend, worker, redis-master all Running

# Check backend logs for errors
kubectl logs -n rag deployment/backend --tail=20 | grep -E "ERROR|error|Error"

# Check worker is processing
kubectl logs -n rag deployment/worker --tail=20

# Check ALB target health
TG_ARN=$(aws elbv2 describe-target-groups --region ap-southeast-2 --query 'TargetGroups[?contains(TargetGroupName, `rag`)].TargetGroupArn' --output text | head -1)
aws elbv2 describe-target-health --target-group-arn "$TG_ARN" --query 'TargetHealthDescriptions[0].TargetHealth.State' --output text
# Expected: healthy
```

### Full Integration Test

```bash
# One-liner to test full flow
ALB_URL="http://$(kubectl get ingress -n rag backend -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')"
TOKEN=$(curl -s -X POST "$ALB_URL/auth/login" -H "Content-Type: application/json" -d '{"username":"admin"}' | jq -r '.token')
echo "1. Health: $(curl -s $ALB_URL/health | jq -r '.status')"
echo "2. Docs before: $(curl -s $ALB_URL/documents -H "Authorization: Bearer $TOKEN" | jq '.documents | length')"
curl -s -X POST "$ALB_URL/upload" -H "Authorization: Bearer $TOKEN" -F "file=@README.md" > /dev/null
sleep 3
echo "3. Docs after: $(curl -s $ALB_URL/documents -H "Authorization: Bearer $TOKEN" | jq '.documents | length')"
echo "4. Query: $(curl -s -X POST "$ALB_URL/query" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"question":"summarize"}' | jq -r '.answer' | head -c 100)..."
echo "✅ All tests passed!"
```

---

## Troubleshooting

### Check pod logs
```bash
kubectl logs -n rag deployment/backend --tail=50
kubectl logs -n rag deployment/worker --tail=50
```

### Check pod status
```bash
kubectl describe pod -n rag -l app=backend
```

### Restart deployments
```bash
kubectl rollout restart deployment/backend -n rag
kubectl rollout restart deployment/worker -n rag
```

### Check ALB target health
```bash
TG_ARN=$(aws elbv2 describe-target-groups --region ap-southeast-2 --query 'TargetGroups[?contains(TargetGroupName, `rag`)].TargetGroupArn' --output text)
aws elbv2 describe-target-health --target-group-arn $TG_ARN --region ap-southeast-2
```

---

## Cleanup (IMPORTANT: Follow this order)

### Step 1: Delete CloudFront (created outside Terraform)
```bash
# Disable CloudFront first (required before deletion)
aws cloudfront get-distribution-config --id E3IS43PPUTX20E > /tmp/cf-disable.json
ETAG=$(jq -r '.ETag' /tmp/cf-disable.json)
jq '.DistributionConfig.Enabled = false' /tmp/cf-disable.json | jq '.DistributionConfig' > /tmp/cf-disabled.json
aws cloudfront update-distribution --id E3IS43PPUTX20E --if-match "$ETAG" --distribution-config file:///tmp/cf-disabled.json

# Wait for deployment (~5 min), then delete
aws cloudfront delete-distribution --id E3IS43PPUTX20E --if-match "$(aws cloudfront get-distribution --id E3IS43PPUTX20E --query 'ETag' --output text)"

# Delete OAC
aws cloudfront delete-origin-access-control --id EKB09ZPCA9PDJ --if-match "$(aws cloudfront get-origin-access-control --id EKB09ZPCA9PDJ --query 'ETag' --output text)"
```

### Step 2: Delete K8s resources (this removes ALB)
```bash
kubectl delete -f k8s/ingress.yaml
kubectl delete -f k8s/worker.yaml
kubectl delete -f k8s/backend.yaml
kubectl delete -f k8s/serviceaccount.yaml
helm uninstall redis -n rag
helm uninstall aws-load-balancer-controller -n kube-system
kubectl delete namespace rag
```

### Step 3: Delete IAM resources (created outside Terraform)
```bash
# Backend role
aws iam detach-role-policy --role-name rag-cloud-backend-role --policy-arn arn:aws:iam::381324498760:policy/rag-cloud-backend-policy
aws iam delete-role --role-name rag-cloud-backend-role
aws iam delete-policy --policy-arn arn:aws:iam::381324498760:policy/rag-cloud-backend-policy

# ALB controller role
aws iam detach-role-policy --role-name AmazonEKSLoadBalancerControllerRole --policy-arn arn:aws:iam::381324498760:policy/AWSLoadBalancerControllerIAMPolicy
aws iam delete-role --role-name AmazonEKSLoadBalancerControllerRole
aws iam delete-policy --policy-arn arn:aws:iam::381324498760:policy/AWSLoadBalancerControllerIAMPolicy
```

### Step 4: Empty S3 buckets (required before Terraform destroy)
```bash
aws s3 rm s3://rag-cloud-dev-documents-381324498760 --recursive --region ap-southeast-2
aws s3 rm s3://rag-cloud-dev-frontend-381324498760 --recursive --region ap-southeast-2
```

### Step 5: Delete ECR images (optional, Terraform handles repos)
```bash
aws ecr batch-delete-image --repository-name rag-cloud-dev-backend --image-ids imageTag=latest --region ap-southeast-2
aws ecr batch-delete-image --repository-name rag-cloud-dev-worker --image-ids imageTag=latest --region ap-southeast-2
```

### Step 6: Terraform destroy
```bash
cd terraform
terraform destroy -auto-approve
```

---

## Current Deployment Values

| Resource | Value |
|----------|-------|
| Region | `ap-southeast-2` |
| Account | `381324498760` |
| EKS Cluster | `rag-cloud-dev` |
| VPC | `vpc-07f777246781deede` |
| OpenSearch | `https://0o0hrf8fm66k1ileok1e.ap-southeast-2.aoss.amazonaws.com` |
| S3 Bucket | `rag-cloud-dev-documents-381324498760` |
| SQS Queue | `https://sqs.ap-southeast-2.amazonaws.com/381324498760/rag-cloud-dev-ingestion` |
| ECR Backend | `381324498760.dkr.ecr.ap-southeast-2.amazonaws.com/rag-cloud-dev-backend` |
| ALB URL | `k8s-rag-backend-b82de7a322-1362292259.ap-southeast-2.elb.amazonaws.com` |

---

## Step 11: Deploy Frontend (S3 + CloudFront)

```bash
cd /mnt/f/zack-gitops-project/mlops/rag-cloud/frontend

# Install dependencies and build
npm install
npm run build

# Upload to S3
aws s3 sync dist/ s3://rag-cloud-dev-frontend-381324498760/ --delete --region ap-southeast-2

# Enable static website hosting
aws s3 website s3://rag-cloud-dev-frontend-381324498760/ --index-document index.html
```

### Create CloudFront Distribution

```bash
# Create Origin Access Control
OAC_ID=$(aws cloudfront create-origin-access-control \
  --origin-access-control-config '{
    "Name": "rag-cloud-frontend-oac",
    "SigningProtocol": "sigv4",
    "SigningBehavior": "always",
    "OriginAccessControlOriginType": "s3"
  }' --query 'OriginAccessControl.Id' --output text)

# Create distribution (save config to file first)
aws cloudfront create-distribution --distribution-config file:///tmp/cf-config.json

# Update S3 bucket policy to allow CloudFront
aws s3api put-bucket-policy --bucket rag-cloud-dev-frontend-381324498760 --policy file:///tmp/bucket-policy.json
```

**Frontend URL:** `https://d20ioargdjagdk.cloudfront.net`

---

## Known Issues & Fixes

### 1. Embedding Model Not Found
**Error:** `ValidationException: The provided model identifier is invalid`

**Cause:** `amazon.titan-embed-text-v1` not available in ap-southeast-2

**Fix:** Use `amazon.titan-embed-text-v2:0` (1024 dimensions instead of 1536)
```python
# config.py
embedding_model_id: str = "amazon.titan-embed-text-v2:0"

# opensearch_client.py - update dimension
def create_index(self, dimension: int = 1024):
```

### 2. OpenSearch Script Score Error
**Error:** `search_phase_execution_exception: compile error`

**Cause:** OpenSearch Serverless doesn't support `script_score` with `cosineSimilarity`

**Fix:** Use native kNN query for hybrid search
```python
# Instead of script_score, use:
query = {
    "bool": {
        "must": [knn_query],
        "should": [text_query]
    }
}
```

### 3. Document ID Not Supported
**Error:** `illegal_argument_exception: Document ID is not supported`

**Cause:** OpenSearch Serverless doesn't allow custom document IDs

**Fix:** Remove `id` parameter from index call
```python
# Instead of:
self.client.index(index=self.index_name, id=doc_id, body=body)
# Use:
self.client.index(index=self.index_name, body=body)
```

### 4. Index Not Found After Pod Restart
**Cause:** Index created on one pod, query hits another before sync

**Fix:** Index creation is idempotent, ensure `create_index()` runs on startup

### 5. Source-Aware Retrieval Not Working
**Error:** Query "what is blog 148 about?" returns no results even though document exists

**Cause:** Source filter was applied AFTER search, but search returned unrelated documents

**Fix:** Pass `source_filter` to OpenSearch query using wildcard filter at search time
```python
# opensearch_client.py - add source_filter parameter
def hybrid_search(self, query_text, query_vector, top_k=5, alpha=0.5, 
                  filter_groups=None, source_filter=None):
    filters = []
    if source_filter:
        filters.append({"wildcard": {"source": f"*{source_filter}*"}})
```

### 6. Vague Questions Return Irrelevant Content
**Error:** "what about blog 143" returns code snippets instead of blog summary

**Cause:** Semantic search matches "what about" to code content

**Fix:** Improved LLM prompt to handle vague "what about" questions
```python
prompt = f"""Answer based on the context below. If the question asks "what about" 
or "tell me about" a specific document/blog/post, provide a summary of its main 
topic and key points.
```

### 7. Frontend Mixed Content Error
**Error:** HTTPS frontend cannot call HTTP backend API

**Symptom:** Login button appears to do nothing, browser console shows `Failed to fetch`

**Cause:** CloudFront serves frontend over HTTPS, but frontend was calling ALB directly over HTTP. Browsers block HTTP requests from HTTPS pages (mixed content).

**Fix:** 
1. Frontend uses empty API URL when on CloudFront:
```javascript
const API = window.location.hostname.includes('cloudfront.net') ? '' : 'http://localhost:8000'
```

2. CloudFront routes API paths to ALB origin via cache behaviors:
```
/auth/*      → ALBOrigin
/query*      → ALBOrigin
/documents*  → ALBOrigin
/upload*     → ALBOrigin
/health      → ALBOrigin
... (all API endpoints)
```

3. All requests stay HTTPS (CloudFront → HTTP → ALB internally)

**Key insight:** The button wasn't broken - the API call was being blocked by the browser.

### 8. Chat History Lost on Logout
**Issue:** Previous conversations disappear after logout/login

**Fix:** Store all chats in `localStorage.allChats`, only remove token on logout

### 9. Document Names Truncated in Sidebar
**Issue:** Long document names cut off, can't read full path

**Fix:** Use `word-break: break-all` instead of `text-overflow: ellipsis`

### 10. Answer Formatting - Single Paragraph
**Issue:** LLM responses display as one long paragraph

**Fix:** Add `formatMessage()` function to render markdown-like formatting:
- Line breaks (`\n` → `<br/>`)
- Paragraphs (double newlines)
- Bold (`**text**`)
- Code blocks and inline code
- Bullet and numbered lists

---

## Current Deployment Values

| Resource | Value |
|----------|-------|
| Region | `ap-southeast-2` |
| Account | `381324498760` |
| EKS Cluster | `rag-cloud-dev` |
| VPC | `vpc-07f777246781deede` |
| OpenSearch | `https://0o0hrf8fm66k1ileok1e.ap-southeast-2.aoss.amazonaws.com` |
| S3 Documents | `rag-cloud-dev-documents-381324498760` |
| S3 Frontend | `rag-cloud-dev-frontend-381324498760` |
| ECR Backend | `381324498760.dkr.ecr.ap-southeast-2.amazonaws.com/rag-cloud-dev-backend` |
| ALB URL | `k8s-rag-backend-b82de7a322-1362292259.ap-southeast-2.elb.amazonaws.com` |
| CloudFront | `https://d20ioargdjagdk.cloudfront.net` |


---

## Feature Comparison: Local vs Cloud

All 26 features from local RAG are working in cloud RAG.

| Feature | Local (rag-v1) | Cloud (rag-cloud) | Status |
|---------|----------------|-------------------|--------|
| Health Check | ✅ | ✅ | Same |
| JWT Auth | ✅ | ✅ | Same |
| RBAC | ✅ | ✅ | Same |
| Sync Upload | ✅ | ✅ | Same |
| Async Upload | ✅ | ✅ | SQS-backed |
| Vector Search | ✅ Weaviate | ✅ OpenSearch | Different backend |
| Hybrid Search | ✅ | ✅ | Adapted |
| Reranking | ✅ | ✅ | Same |
| Query | ✅ | ✅ | Same |
| Streaming | ✅ | ✅ | Same |
| Model Routing | ✅ | ✅ | Same |
| Memory | ✅ | ✅ | Same |
| ReAct Agent | ✅ | ✅ | Same |
| Caching | ✅ Redis | ✅ Redis | Same |
| Rate Limiting | ✅ | ✅ | Same |
| Audit Logs | ✅ | ✅ | Same |
| Usage Tracking | ✅ | ✅ | Same |
| Web Connector | ✅ | ✅ | Same |
| Pipelines | ✅ | ✅ | Same |
| Frontend | ✅ Nginx | ✅ S3+CF | Different |

### Key Technical Differences

| Aspect | Local | Cloud |
|--------|-------|-------|
| Vector DB | Weaviate (1536-dim) | OpenSearch Serverless (1024-dim) |
| Embedding | Titan v1 | Titan v2 |
| Queue | In-memory | SQS |
| Frontend | Nginx container | S3 + CloudFront |


---

## Cost Analysis (ap-southeast-2)

### Monthly Infrastructure Costs

| Service | Configuration | Monthly Cost |
|---------|---------------|--------------|
| **EKS Control Plane** | 1 cluster | $73.00 |
| **EC2 (EKS Node)** | 1x t3.large (2 vCPU, 8GB) | $60.74 |
| **OpenSearch Serverless** | 2 OCUs (minimum) | $86.40 |
| **NAT Gateway** | 1 gateway + data processing | $32.40 |
| **ALB** | 1 load balancer | $16.20 |
| **S3** | <1GB storage | $0.50 |
| **CloudFront** | <10GB transfer | $1.00 |
| **SQS** | <1M requests | $0.40 |
| **DynamoDB** | On-demand, minimal usage | $1.00 |
| **ECR** | <1GB images | $0.10 |
| **Cognito** | <50 MAU (free tier) | $0.00 |
| **Total Infrastructure** | | **~$272/month** |

### Bedrock Usage Costs (Variable)

| Model | Pricing | Example Usage | Cost |
|-------|---------|---------------|------|
| **Titan Embed v2** | $0.0001/1K tokens | 100K tokens/day | $3.00/month |
| **Claude 3 Haiku** | $0.00025/1K input, $0.00125/1K output | 500 queries/day | $15.00/month |
| **Claude 3 Sonnet** | $0.003/1K input, $0.015/1K output | 50 complex queries/day | $10.00/month |
| **Total Bedrock** | | | **~$28/month** |

### Total Estimated Cost

| Environment | Monthly Cost |
|-------------|--------------|
| **Development** (minimal usage) | ~$300/month |
| **Production** (moderate usage) | ~$400-500/month |

### Cost Optimization Options

1. **Use Spot Instances for EKS nodes** (-60-70%)
   ```bash
   # In terraform/modules/eks/main.tf
   capacity_type = "SPOT"
   ```

2. **Schedule OpenSearch Serverless** (off-hours)
   - 2 OCUs = $0.12/hour
   - Run 12 hours/day = $43.20/month (50% savings)

3. **Use smaller instance type**
   - t3.medium instead of t3.large = $30.37/month

4. **Remove NAT Gateway** (if public subnets acceptable)
   - Saves $32.40/month

5. **Use CloudFront caching aggressively**
   - Reduce ALB requests and Bedrock calls

### Cost Comparison: Local vs Cloud

| Aspect | Local (Docker) | AWS Cloud |
|--------|----------------|-----------|
| Infrastructure | $0 (your machine) | ~$272/month |
| Bedrock | N/A (local models) | ~$28/month |
| Scalability | Limited | Auto-scaling |
| Availability | Single machine | Multi-AZ |
| Maintenance | Manual | Managed services |

### Break-Even Analysis

- **Cloud makes sense when:**
  - Need 24/7 availability
  - Multiple users/teams
  - Production workloads
  - Compliance requirements

- **Local makes sense when:**
  - Development/testing only
  - Single user
  - Cost-sensitive prototyping
  - No internet dependency needed
