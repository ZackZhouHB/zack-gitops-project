# LangChain RAG System - Deployment Guide

## Prerequisites

- EKS cluster running (e.g., `eks-rag-weaviate`)
- kubectl configured to access the cluster
- AWS CLI configured with appropriate credentials
- Docker installed for building images
- ECR repository created for storing images

## IAM Setup

### 1. Create IAM Policy

Create a policy named `eks-rag-weaviate-rag-backend-policy` with the following permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream",
        "bedrock:ListInferenceProfiles",
        "bedrock:ListFoundationModels",
        "bedrock:GetInferenceProfile"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::eks-rag-weaviate-documents-*",
        "arn:aws:s3:::eks-rag-weaviate-documents-*/*",
        "arn:aws:s3:::eks-rag-langchain-docs-*",
        "arn:aws:s3:::eks-rag-langchain-docs-*/*"
      ]
    }
  ]
}
```

**Using AWS CLI:**

```bash
# Create policy
aws iam create-policy \
  --policy-name eks-rag-weaviate-rag-backend-policy \
  --policy-document file://iam-policy.json \
  --profile sandboxtest

# Note the PolicyArn from the output
```

**Key Permissions Explained:**

- `bedrock:InvokeModel` - Call Bedrock models
- `bedrock:GetInferenceProfile` - **Critical for inference profiles** (cross-region access)
- `s3:GetObject/PutObject/DeleteObject` - Document storage operations
- `s3:ListBucket` - List documents in bucket

### 2. Create or Update IAM Role

If the role `eks-rag-weaviate-rag-backend-role` doesn't exist, create it:

```bash
# Create trust policy file
cat > trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::xx88accountid:oidc-provider/oidc.eks.ap-southeast-2.amazonaws.com/id/<OIDC_ID>"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "oidc.eks.ap-southeast-2.amazonaws.com/id/<OIDC_ID>:sub": "system:serviceaccount:langchain:rag-service-account",
          "oidc.eks.ap-southeast-2.amazonaws.com/id/<OIDC_ID>:aud": "sts.amazonaws.com"
        }
      }
    }
  ]
}
EOF

# Create role
aws iam create-role \
  --role-name eks-rag-weaviate-rag-backend-role \
  --assume-role-policy-document file://trust-policy.json \
  --profile sandboxtest

# Attach policy to role
aws iam attach-role-policy \
  --role-name eks-rag-weaviate-rag-backend-role \
  --policy-arn arn:aws:iam::xx88accountid:policy/eks-rag-weaviate-rag-backend-policy \
  --profile sandboxtest
```

**To get your OIDC ID:**

```bash
aws eks describe-cluster \
  --name eks-rag-weaviate \
  --query "cluster.identity.oidc.issuer" \
  --output text \
  --profile sandboxtest
# Extract the ID from the URL (last part after /id/)
```

### 3. Update Existing IAM Policy (If Role Already Exists)

If you're updating an existing deployment:

```bash
# List existing policy versions
aws iam list-policy-versions \
  --policy-arn arn:aws:iam::xx88accountid:policy/eks-rag-weaviate-rag-backend-policy \
  --profile sandboxtest

# Delete old versions if at limit (max 5 versions)
aws iam delete-policy-version \
  --policy-arn arn:aws:iam::xx88accountid:policy/eks-rag-weaviate-rag-backend-policy \
  --version-id v2 \
  --profile sandboxtest

# Create new policy version
aws iam create-policy-version \
  --policy-arn arn:aws:iam::xx88accountid:policy/eks-rag-weaviate-rag-backend-policy \
  --policy-document file://iam-policy.json \
  --set-as-default \
  --profile sandboxtest
```

## Kubernetes Setup

### 1. Create Namespace

```bash
kubectl create namespace langchain
```

### 2. Create Service Account with IRSA

Create `k8s/service-account.yaml`:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: rag-service-account
  namespace: langchain
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::xx88accountid:role/eks-rag-weaviate-rag-backend-role
```

Apply:

```bash
kubectl apply -f k8s/service-account.yaml
```

**Verify Service Account:**

```bash
kubectl get sa rag-service-account -n langchain -o yaml
# Should show the role-arn annotation
```

### 3. Create S3 Bucket

```bash
# Create bucket with unique name
aws s3 mb s3://eks-rag-langchain-docs-xx88accountid \
  --region ap-southeast-2 \
  --profile sandboxtest

# Enable versioning (optional)
aws s3api put-bucket-versioning \
  --bucket eks-rag-langchain-docs-xx88accountid \
  --versioning-configuration Status=Enabled \
  --profile sandboxtest
```

## Deploy Weaviate

### 1. Create Weaviate StatefulSet

Create `k8s/weaviate-statefulset.yaml`:

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: weaviate
  namespace: langchain
spec:
  serviceName: weaviate-service
  replicas: 1
  selector:
    matchLabels:
      app: weaviate
  template:
    metadata:
      labels:
        app: weaviate
    spec:
      containers:
      - name: weaviate
        image: semitechnologies/weaviate:1.23.0
        ports:
        - containerPort: 8080
          name: http
        env:
        - name: QUERY_DEFAULTS_LIMIT
          value: "25"
        - name: AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED
          value: "true"
        - name: PERSISTENCE_DATA_PATH
          value: "/var/lib/weaviate"
        - name: DEFAULT_VECTORIZER_MODULE
          value: "none"
        - name: ENABLE_MODULES
          value: ""
        - name: CLUSTER_HOSTNAME
          value: "node1"
        volumeMounts:
        - name: weaviate-data
          mountPath: /var/lib/weaviate
  volumeClaimTemplates:
  - metadata:
      name: weaviate-data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 10Gi
```

### 2. Create Weaviate Service

Create `k8s/weaviate-service.yaml`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: weaviate-service
  namespace: langchain
spec:
  selector:
    app: weaviate
  ports:
  - port: 8080
    targetPort: 8080
    name: http
  clusterIP: None
```

Apply:

```bash
kubectl apply -f k8s/weaviate-statefulset.yaml
kubectl apply -f k8s/weaviate-service.yaml

# Wait for Weaviate to be ready
kubectl wait --for=condition=ready pod -l app=weaviate -n langchain --timeout=300s
```

## Deploy Backend

### 1. Build and Push Docker Image

```bash
cd langchain-way/backend

# Build image
docker build -t rag-backend-langchain:latest .

# Tag for ECR
docker tag rag-backend-langchain:latest xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-backend-langchain:latest

# Login to ECR
aws ecr get-login-password --region ap-southeast-2 --profile sandboxtest | \
  docker login --username AWS --password-stdin xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com

# Push image
docker push xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-backend-langchain:latest
```

### 2. Create Backend Deployment

Create `k8s/backend-deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rag-backend-langchain
  namespace: langchain
spec:
  replicas: 1
  selector:
    matchLabels:
      app: rag-backend-langchain
  template:
    metadata:
      labels:
        app: rag-backend-langchain
    spec:
      serviceAccountName: rag-service-account
      containers:
      - name: backend
        image: xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-backend-langchain:latest
        ports:
        - containerPort: 8000
        env:
        - name: AWS_REGION
          value: "ap-southeast-2"
        - name: S3_BUCKET_NAME
          value: "eks-rag-langchain-docs-xx88accountid"
        - name: WEAVIATE_HOST
          value: "weaviate-service.langchain.svc.cluster.local"
        - name: WEAVIATE_PORT
          value: "8080"
        - name: WEAVIATE_CLASS_NAME
          value: "DocumentsLangChain"
        - name: BEDROCK_MODEL_ID
          value: "apac.anthropic.claude-sonnet-4-20250514-v1:0"
        - name: EMBEDDING_MODEL_ID
          value: "amazon.titan-embed-text-v2:0"
        - name: EFS_MOUNT_PATH
          value: "/efs"
        - name: EFS_CHAT_SUBDIR
          value: "chat_history"
        - name: CHUNK_SIZE
          value: "1000"
        - name: CHUNK_OVERLAP
          value: "200"
        - name: MAX_TOKENS
          value: "4000"
        - name: TEMPERATURE
          value: "0.1"
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
```

### 3. Create Backend Service

Create `k8s/backend-service.yaml`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: rag-backend-service
  namespace: langchain
spec:
  selector:
    app: rag-backend-langchain
  ports:
  - port: 8000
    targetPort: 8000
  type: ClusterIP
```

Apply:

```bash
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/backend-service.yaml

# Wait for backend to be ready
kubectl wait --for=condition=ready pod -l app=rag-backend-langchain -n langchain --timeout=300s
```

## Deploy Frontend

### 1. Build and Push Frontend Image

```bash
cd langchain-way/frontend

# Build image
docker build -t rag-frontend-langchain:latest .

# Tag for ECR
docker tag rag-frontend-langchain:latest xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-frontend-langchain:latest

# Push image
docker push xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-frontend-langchain:latest
```

### 2. Create Frontend Deployment

Create `k8s/frontend-deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rag-frontend-langchain
  namespace: langchain
spec:
  replicas: 1
  selector:
    matchLabels:
      app: rag-frontend-langchain
  template:
    metadata:
      labels:
        app: rag-frontend-langchain
    spec:
      containers:
      - name: frontend
        image: xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-frontend-langchain:latest
        ports:
        - containerPort: 80
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "200m"
```

### 3. Create Frontend Service (LoadBalancer)

Create `k8s/frontend-service.yaml`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: rag-frontend-service
  namespace: langchain
spec:
  selector:
    app: rag-frontend-langchain
  ports:
  - port: 80
    targetPort: 80
  type: LoadBalancer
```

Apply:

```bash
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/frontend-service.yaml

# Get LoadBalancer URL
kubectl get svc rag-frontend-service -n langchain
```

## Verification

### 1. Check All Pods are Running

```bash
kubectl get pods -n langchain

# Expected output:
# NAME                                      READY   STATUS    RESTARTS   AGE
# rag-backend-langchain-xxx                 1/1     Running   0          5m
# rag-frontend-langchain-xxx                1/1     Running   0          3m
# weaviate-0                                1/1     Running   0          10m
```

### 2. Check Backend Logs

```bash
kubectl logs -n langchain $(kubectl get pods -n langchain -l app=rag-backend-langchain -o jsonpath='{.items[0].metadata.name}')

# Should see:
# INFO:app.langchain_rag_service:LangChain RAG service initialized successfully
# INFO:app.main:LangChain RAG service initialized successfully
```

### 3. Test Backend Health

```bash
kubectl port-forward -n langchain svc/rag-backend-service 8000:8000

# In another terminal:
curl http://localhost:8000/health
```

### 4. Access Frontend

Get the LoadBalancer URL:

```bash
kubectl get svc rag-frontend-service -n langchain -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
```

Open in browser and verify:
- Vector Database Status shows statistics
- Can upload documents
- Can ask questions and get responses with sources

## Troubleshooting

### Backend Pod Not Starting

```bash
# Check pod status
kubectl describe pod -n langchain -l app=rag-backend-langchain

# Check logs
kubectl logs -n langchain -l app=rag-backend-langchain --tail=100
```

**Common Issues:**
- IAM role not attached: Check service account annotation
- S3 bucket doesn't exist: Create bucket
- Weaviate not ready: Wait for Weaviate pod to be Running

### Model Access Denied

```bash
# Check IAM policy has GetInferenceProfile
aws iam get-policy-version \
  --policy-arn arn:aws:iam::xx88accountid:policy/eks-rag-weaviate-rag-backend-policy \
  --version-id v7 \
  --profile sandboxtest
```

Ensure policy includes:
```json
{
  "Action": [
    "bedrock:GetInferenceProfile"
  ],
  "Resource": "*"
}
```

### Sources Showing "Unknown"

```bash
# Check Weaviate schema
kubectl exec -n langchain $(kubectl get pods -n langchain -l app=rag-backend-langchain -o jsonpath='{.items[0].metadata.name}') -- python3 -c "
import weaviate
client = weaviate.Client('http://weaviate-service.langchain.svc.cluster.local:8080')
schema = client.schema.get('DocumentsLangChain')
print('Properties:')
for prop in schema.get('properties', []):
    print(f\"  - {prop['name']}: {prop['dataType']}\")"
```

Should show `source`, `content`, `s3_key` properties.

### Weaviate Connection Issues

```bash
# Test Weaviate connectivity
kubectl run -it --rm debug --image=curlimages/curl --restart=Never -n langchain -- \
  curl http://weaviate-service.langchain.svc.cluster.local:8080/v1/meta
```

## Updating the Deployment

### Update Backend Code

```bash
cd langchain-way/backend

# Rebuild and push
docker build -t rag-backend-langchain:latest .
docker tag rag-backend-langchain:latest xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-backend-langchain:latest
docker push xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-backend-langchain:latest

# Restart deployment
kubectl rollout restart deployment/rag-backend-langchain -n langchain
kubectl rollout status deployment/rag-backend-langchain -n langchain
```

### Update IAM Policy

```bash
# Delete old version if at limit
aws iam delete-policy-version \
  --policy-arn arn:aws:iam::xx88accountid:policy/eks-rag-weaviate-rag-backend-policy \
  --version-id v2 \
  --profile sandboxtest

# Create new version
aws iam create-policy-version \
  --policy-arn arn:aws:iam::xx88accountid:policy/eks-rag-weaviate-rag-backend-policy \
  --policy-document file://iam-policy.json \
  --set-as-default \
  --profile sandboxtest
```

## Cleanup

### Delete Kubernetes Resources

```bash
kubectl delete namespace langchain
```

### Delete S3 Bucket

```bash
# Empty bucket first
aws s3 rm s3://eks-rag-langchain-docs-xx88accountid --recursive --profile sandboxtest

# Delete bucket
aws s3 rb s3://eks-rag-langchain-docs-xx88accountid --profile sandboxtest
```

### Delete IAM Resources

```bash
# Detach policy from role
aws iam detach-role-policy \
  --role-name eks-rag-weaviate-rag-backend-role \
  --policy-arn arn:aws:iam::xx88accountid:policy/eks-rag-weaviate-rag-backend-policy \
  --profile sandboxtest

# Delete role
aws iam delete-role \
  --role-name eks-rag-weaviate-rag-backend-role \
  --profile sandboxtest

# Delete policy
aws iam delete-policy \
  --policy-arn arn:aws:iam::xx88accountid:policy/eks-rag-weaviate-rag-backend-policy \
  --profile sandboxtest
```

## Quick Deployment Script

Save as `deploy.sh`:

```bash
#!/bin/bash
set -e

NAMESPACE="langchain"
REGION="ap-southeast-2"
ACCOUNT_ID="xx88accountid"
ECR_REPO="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

echo "=== Deploying LangChain RAG System ==="

# Create namespace
kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -

# Deploy Weaviate
kubectl apply -f k8s/weaviate-statefulset.yaml
kubectl apply -f k8s/weaviate-service.yaml
kubectl wait --for=condition=ready pod -l app=weaviate -n ${NAMESPACE} --timeout=300s

# Build and push backend
cd backend
docker build -t rag-backend-langchain:latest .
docker tag rag-backend-langchain:latest ${ECR_REPO}/rag-backend-langchain:latest
aws ecr get-login-password --region ${REGION} | docker login --username AWS --password-stdin ${ECR_REPO}
docker push ${ECR_REPO}/rag-backend-langchain:latest
cd ..

# Deploy backend
kubectl apply -f k8s/service-account.yaml
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/backend-service.yaml
kubectl wait --for=condition=ready pod -l app=rag-backend-langchain -n ${NAMESPACE} --timeout=300s

# Build and push frontend
cd frontend
docker build -t rag-frontend-langchain:latest .
docker tag rag-frontend-langchain:latest ${ECR_REPO}/rag-frontend-langchain:latest
docker push ${ECR_REPO}/rag-frontend-langchain:latest
cd ..

# Deploy frontend
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/frontend-service.yaml

echo "=== Deployment Complete ==="
echo "Get LoadBalancer URL:"
echo "kubectl get svc rag-frontend-service -n ${NAMESPACE}"
```

Make executable and run:

```bash
chmod +x deploy.sh
./deploy.sh
```
