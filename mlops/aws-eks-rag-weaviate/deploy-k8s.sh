#!/bin/bash

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Deploying Kubernetes Manifests${NC}"
echo "=================================="

# Get Terraform outputs
cd terraform
S3_BUCKET_NAME=$(terraform output -raw s3_bucket_name)
KENDRA_INDEX_ID=$(terraform output -raw kendra_index_id)
KENDRA_DATA_SOURCE_ID=$(terraform output -raw kendra_data_source_id)
EFS_FILE_SYSTEM_ID=$(terraform output -raw efs_file_system_id)
cd ..

# ECR URIs
ECR_BACKEND_URI="615299759525.dkr.ecr.ap-southeast-2.amazonaws.com/aws-eks-rag-backend:latest"
ECR_FRONTEND_URI="615299759525.dkr.ecr.ap-southeast-2.amazonaws.com/aws-eks-rag-frontend:latest"

echo "Using values:"
echo "S3 Bucket: $S3_BUCKET_NAME"
echo "Kendra Index: $KENDRA_INDEX_ID"
echo "EFS ID: $EFS_FILE_SYSTEM_ID"

# Update ConfigMap with Terraform outputs
echo -e "${YELLOW}Creating ConfigMap...${NC}"
cat > k8s/configmap-updated.yaml << EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: rag-config
  namespace: rag-system
data:
  AWS_REGION: "ap-southeast-2"
  BEDROCK_MODEL_ID: "anthropic.claude-3-sonnet-20240229-v1:0"
  EFS_MOUNT_PATH: "/efs"
  LOG_LEVEL: "INFO"
  S3_BUCKET_NAME: "$S3_BUCKET_NAME"
  KENDRA_INDEX_ID: "$KENDRA_INDEX_ID"
  KENDRA_DATA_SOURCE_ID: "$KENDRA_DATA_SOURCE_ID"
EOF

# Update EFS storage class
echo -e "${YELLOW}Creating EFS storage class...${NC}"
sed "s/\${EFS_FILE_SYSTEM_ID}/$EFS_FILE_SYSTEM_ID/g" k8s/efs-storage.yaml > k8s/efs-storage-updated.yaml

# Update Kubernetes manifests with ECR URIs
echo -e "${YELLOW}Updating deployment manifests...${NC}"
sed "s|\${ECR_REPOSITORY_URI}|$ECR_BACKEND_URI|g" k8s/backend-deployment.yaml > k8s/backend-deployment-updated.yaml
sed "s|\${ECR_FRONTEND_URI}|$ECR_FRONTEND_URI|g" k8s/frontend-deployment.yaml > k8s/frontend-deployment-updated.yaml

# Deploy to Kubernetes
echo -e "${YELLOW}Deploying to Kubernetes...${NC}"

kubectl apply -f k8s/configmap-updated.yaml
kubectl apply -f k8s/efs-storage-updated.yaml
kubectl apply -f k8s/backend-deployment-updated.yaml
kubectl apply -f k8s/frontend-deployment-updated.yaml

# Wait for deployments
echo -e "${YELLOW}Waiting for deployments...${NC}"
kubectl wait --for=condition=available --timeout=300s deployment/rag-backend -n rag-system
kubectl wait --for=condition=available --timeout=300s deployment/rag-frontend -n rag-system

# Get service information
echo -e "${GREEN}Deployment completed!${NC}"
echo ""
echo "Service Information:"
kubectl get services -n rag-system
echo ""
echo "Pod Status:"
kubectl get pods -n rag-system

# Cleanup temporary files
rm -f k8s/configmap-updated.yaml k8s/efs-storage-updated.yaml k8s/backend-deployment-updated.yaml k8s/frontend-deployment-updated.yaml

echo ""
echo -e "${GREEN}Next Steps:${NC}"
echo "1. Wait for LoadBalancer external IP"
echo "2. Upload documents to S3: $S3_BUCKET_NAME"
echo "3. Start using your RAG system!"
