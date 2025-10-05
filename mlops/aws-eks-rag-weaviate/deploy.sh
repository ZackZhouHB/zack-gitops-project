#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}AWS EKS RAG Deployment Script${NC}"
echo "=================================="

# Check if AWS CLI is configured
if ! aws sts get-caller-identity --profile sandboxtest > /dev/null 2>&1; then
    echo -e "${RED}Error: AWS CLI not configured with sandboxtest profile${NC}"
    exit 1
fi

# Step 1: Deploy Infrastructure
echo -e "${YELLOW}Step 1: Deploying Infrastructure with Terraform...${NC}"
cd terraform

if [ ! -f "terraform.tfstate" ]; then
    echo "Initializing Terraform..."
    terraform init
fi

echo "Planning Terraform deployment..."
terraform plan -var-file="terraform.tfvars"

read -p "Do you want to apply the Terraform plan? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Applying Terraform..."
    terraform apply -auto-approve -var-file="terraform.tfvars"
else
    echo "Terraform deployment cancelled."
    exit 0
fi

# Get Terraform outputs
echo "Getting Terraform outputs..."
CLUSTER_NAME=$(terraform output -raw cluster_name)
S3_BUCKET_NAME=$(terraform output -raw s3_bucket_name)
KENDRA_INDEX_ID=$(terraform output -raw kendra_index_id)
KENDRA_DATA_SOURCE_ID=$(terraform output -raw kendra_data_source_id)
EFS_FILE_SYSTEM_ID=$(terraform output -raw efs_file_system_id)

echo -e "${GREEN}Infrastructure deployed successfully!${NC}"
echo "Cluster Name: $CLUSTER_NAME"
echo "S3 Bucket: $S3_BUCKET_NAME"
echo "Kendra Index ID: $KENDRA_INDEX_ID"

cd ..

# Step 2: Configure kubectl
echo -e "${YELLOW}Step 2: Configuring kubectl...${NC}"
aws eks --region ap-southeast-2 --profile sandboxtest update-kubeconfig --name $CLUSTER_NAME

# Step 3: Update Kubernetes manifests with Terraform outputs
echo -e "${YELLOW}Step 3: Updating Kubernetes manifests...${NC}"

# Update ConfigMap with Terraform outputs
cat > k8s/configmap-updated.yaml << EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: rag-config
  namespace: rag-system
data:
  AWS_REGION: "ap-southeast-2"
  BEDROCK_MODEL_ID: "apac.anthropic.claude-sonnet-4-20250514-v1:0"
  EFS_MOUNT_PATH: "/efs"
  LOG_LEVEL: "INFO"
  S3_BUCKET_NAME: "$S3_BUCKET_NAME"
  KENDRA_INDEX_ID: "$KENDRA_INDEX_ID"
  KENDRA_DATA_SOURCE_ID: "$KENDRA_DATA_SOURCE_ID"
EOF

# Update EFS storage class
sed "s/\${EFS_FILE_SYSTEM_ID}/$EFS_FILE_SYSTEM_ID/g" k8s/efs-storage.yaml > k8s/efs-storage-updated.yaml

# Step 4: Build and push Docker images
echo -e "${YELLOW}Step 4: Building and pushing Docker images...${NC}"

# Get ECR repository URIs
ACCOUNT_ID=$(aws sts get-caller-identity --profile sandboxtest --query Account --output text)
ECR_BACKEND_URI="$ACCOUNT_ID.dkr.ecr.ap-southeast-2.amazonaws.com/aws-eks-rag-backend"
ECR_FRONTEND_URI="$ACCOUNT_ID.dkr.ecr.ap-southeast-2.amazonaws.com/aws-eks-rag-frontend"

# Create ECR repositories if they don't exist
echo "Creating ECR repositories..."
aws ecr describe-repositories --repository-names aws-eks-rag-backend --region ap-southeast-2 --profile sandboxtest > /dev/null 2>&1 || \
aws ecr create-repository --repository-name aws-eks-rag-backend --region ap-southeast-2 --profile sandboxtest

aws ecr describe-repositories --repository-names aws-eks-rag-frontend --region ap-southeast-2 --profile sandboxtest > /dev/null 2>&1 || \
aws ecr create-repository --repository-name aws-eks-rag-frontend --region ap-southeast-2 --profile sandboxtest

# Login to ECR
echo "Logging into ECR..."
aws ecr get-login-password --region ap-southeast-2 --profile sandboxtest | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.ap-southeast-2.amazonaws.com

# Build and push backend image
echo "Building backend image..."
docker build -t aws-eks-rag-backend:latest backend/
docker tag aws-eks-rag-backend:latest $ECR_BACKEND_URI:latest
echo "Pushing backend image to ECR..."
docker push $ECR_BACKEND_URI:latest

# Build and push frontend image
echo "Building frontend image..."
docker build -t aws-eks-rag-frontend:latest frontend/
docker tag aws-eks-rag-frontend:latest $ECR_FRONTEND_URI:latest
echo "Pushing frontend image to ECR..."
docker push $ECR_FRONTEND_URI:latest

# Update Kubernetes manifests with ECR URIs
echo "Updating Kubernetes manifests with ECR URIs..."
sed "s|\${ECR_REPOSITORY_URI}:latest|$ECR_BACKEND_URI:latest|g" k8s/backend-deployment.yaml > k8s/backend-deployment-updated.yaml
sed "s|\${ECR_FRONTEND_URI}:latest|$ECR_FRONTEND_URI:latest|g" k8s/frontend-deployment.yaml > k8s/frontend-deployment-updated.yaml

# Step 5: Deploy to Kubernetes
echo -e "${YELLOW}Step 5: Deploying to Kubernetes...${NC}"

# Apply manifests in order
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap-updated.yaml
kubectl apply -f k8s/efs-storage-updated.yaml

# Deploy Karpenter NodePool and EC2NodeClass
echo "Deploying Karpenter NodePool and EC2NodeClass..."
kubectl apply -f k8s/karpenter-nodepool.yaml

kubectl apply -f k8s/backend-deployment-updated.yaml
kubectl apply -f k8s/frontend-deployment-updated.yaml

# Wait for deployments
echo "Waiting for deployments to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/rag-backend -n rag-system
kubectl wait --for=condition=available --timeout=300s deployment/rag-frontend -n rag-system

# Step 6: Get service URLs
echo -e "${YELLOW}Step 6: Getting service information...${NC}"
echo -e "${GREEN}Deployment completed successfully!${NC}"
echo ""
echo "Service Information:"
echo "==================="
kubectl get services -n rag-system
echo ""
echo "Ingress Information:"
echo "==================="
kubectl get ingress -n rag-system
echo ""
echo "Pod Status:"
echo "==========="
kubectl get pods -n rag-system

echo ""
echo -e "${GREEN}Next Steps:${NC}"
echo "1. Wait for the LoadBalancer to get an external IP"
echo "2. Upload documents to S3 bucket: $S3_BUCKET_NAME"
echo "3. Sync documents with Kendra using the API"
echo "4. Start querying your documents!"

# Cleanup temporary files
rm -f k8s/configmap-updated.yaml k8s/efs-storage-updated.yaml k8s/backend-deployment-updated.yaml k8s/frontend-deployment-updated.yaml
