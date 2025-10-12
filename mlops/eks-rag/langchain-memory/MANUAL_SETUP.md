# Manual Setup Instructions for LangChain RAG Solution

## Prerequisites Setup (Manual)

### 1. Create ECR Repositories
```bash
# Create ECR repositories manually
aws ecr create-repository --repository-name rag-backend-langchain --region ap-southeast-2 --profile sandboxtest
aws ecr create-repository --repository-name rag-frontend-langchain --region ap-southeast-2 --profile sandboxtest

# Get repository URIs
aws ecr describe-repositories --repository-names rag-backend-langchain rag-frontend-langchain --region ap-southeast-2 --profile sandboxtest
```

### 2. Create S3 Bucket
```bash
# Create S3 bucket manually (replace with unique name)
aws s3 mb s3://eks-rag-langchain-docs-$(date +%s) --region ap-southeast-2 --profile sandboxtest

# Note the bucket name for later use
BUCKET_NAME="eks-rag-langchain-docs-XXXXXX"
```

### 3. Create Dedicated Node Group
```bash
# Create dedicated node group for LangChain workloads
aws eks create-nodegroup \
  --cluster-name eks-rag-weaviate \
  --nodegroup-name langchain-nodes \
  --subnets subnet-XXXXX subnet-YYYYY \
  --instance-types t3.medium \
  --ami-type AL2_x86_64 \
  --capacity-type ON_DEMAND \
  --scaling-config minSize=1,maxSize=3,desiredSize=2 \
  --labels node-group=langchain \
  --region ap-southeast-2 \
  --profile sandboxtest
```

## Configuration Updates

### 4. Update Kubernetes Manifests
```bash
# Update backend deployment with actual S3 bucket name
sed -i 's/MANUAL_S3_BUCKET_NAME/your-actual-bucket-name/g' k8s-deploy/backend-deployment.yaml

# Update image URIs in deployments (if different from default)
# Edit k8s-deploy/backend-deployment.yaml and k8s-deploy/frontend-deployment.yaml
```

### 5. Build and Push Images
```bash
# Get ECR login
aws ecr get-login-password --region ap-southeast-2 --profile sandboxtest | docker login --username AWS --password-stdin 615299759525.dkr.ecr.ap-southeast-2.amazonaws.com

# Build and push backend
cd backend
docker build -t rag-backend-langchain .
docker tag rag-backend-langchain:latest 615299759525.dkr.ecr.ap-southeast-2.amazonaws.com/rag-backend-langchain:latest
docker push 615299759525.dkr.ecr.ap-southeast-2.amazonaws.com/rag-backend-langchain:latest

# Build and push frontend
cd ../frontend
docker build -t rag-frontend-langchain .
docker tag rag-frontend-langchain:latest 615299759525.dkr.ecr.ap-southeast-2.amazonaws.com/rag-frontend-langchain:latest
docker push 615299759525.dkr.ecr.ap-southeast-2.amazonaws.com/rag-frontend-langchain:latest
```

## Deployment

### 6. Deploy to Existing EKS Cluster
```bash
# Configure kubectl for existing cluster
aws eks --region ap-southeast-2 --profile sandboxtest update-kubeconfig --name eks-rag-weaviate

# Deploy LangChain services (will use dedicated node group)
kubectl apply -f k8s-deploy/backend-deployment.yaml
kubectl apply -f k8s-deploy/frontend-deployment.yaml

# Verify deployment on dedicated nodes
kubectl get pods -n rag-system -o wide | grep langchain
```

## Verification

### 7. Check Node Placement
```bash
# Verify pods are running on dedicated node group
kubectl get pods -n rag-system -l app=rag-backend-langchain -o wide
kubectl get pods -n rag-system -l app=rag-frontend-langchain -o wide

# Check node labels
kubectl get nodes --show-labels | grep langchain
```

### 8. Test Services
```bash
# Get LoadBalancer URL
kubectl get svc rag-frontend-langchain-service -n rag-system

# Test API
FRONTEND_URL=$(kubectl get svc rag-frontend-langchain-service -n rag-system -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
curl http://${FRONTEND_URL}/api/health
```

## Resource Summary

After manual setup, you will have:

- **ECR Repositories**: 
  - `rag-backend-langchain`
  - `rag-frontend-langchain`
- **S3 Bucket**: `eks-rag-langchain-docs-XXXXXX`
- **Node Group**: `langchain-nodes` with label `node-group=langchain`
- **Services**: Running on existing EKS cluster but dedicated nodes
- **Separation**: Complete isolation from original RAG solution

## Benefits of This Approach

- **Cost Effective**: Reuses existing EKS cluster and infrastructure
- **Isolated**: Dedicated node group ensures separation
- **Flexible**: Manual resource creation allows custom naming/configuration
- **Safe**: No risk of affecting existing Terraform state or resources
