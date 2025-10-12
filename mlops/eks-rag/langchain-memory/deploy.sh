#!/bin/bash

# Deployment script for LangChain RAG solution (Manual ECR/S3 approach)

set -e

echo "🚀 Deploying LangChain RAG Solution (Manual Setup)"

# Configuration
AWS_REGION="ap-southeast-2"
AWS_PROFILE="sandboxtest"
CLUSTER_NAME="eks-rag-weaviate"  # Use existing cluster

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
print_status "Checking prerequisites..."

# Check if ECR repositories exist
ECR_BACKEND_EXISTS=$(aws ecr describe-repositories --repository-names rag-backend-langchain --region ${AWS_REGION} --profile ${AWS_PROFILE} 2>/dev/null || echo "false")
ECR_FRONTEND_EXISTS=$(aws ecr describe-repositories --repository-names rag-frontend-langchain --region ${AWS_REGION} --profile ${AWS_PROFILE} 2>/dev/null || echo "false")

if [[ "$ECR_BACKEND_EXISTS" == "false" ]] || [[ "$ECR_FRONTEND_EXISTS" == "false" ]]; then
    print_error "ECR repositories not found. Please run manual setup first:"
    echo "See MANUAL_SETUP.md for instructions"
    exit 1
fi

# Check if S3 bucket is configured
if grep -q "MANUAL_S3_BUCKET_NAME" k8s-deploy/backend-deployment.yaml; then
    print_error "S3 bucket not configured in backend-deployment.yaml"
    echo "Please update MANUAL_S3_BUCKET_NAME with your actual bucket name"
    exit 1
fi

print_status "Prerequisites check passed!"

# Step 1: Build and push Docker images
print_status "Step 1: Building and pushing Docker images..."

# Get ECR login
aws ecr get-login-password --region ${AWS_REGION} --profile ${AWS_PROFILE} | docker login --username AWS --password-stdin xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com

# Build and push backend
print_status "Building LangChain backend..."
cd backend
docker build -t rag-backend-langchain .
docker tag rag-backend-langchain:latest xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-backend-langchain:latest
docker push xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-backend-langchain:latest
cd ..

# Build and push frontend
print_status "Building LangChain frontend..."
cd frontend
docker build -t rag-frontend-langchain .
docker tag rag-frontend-langchain:latest xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-frontend-langchain:latest
docker push xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-frontend-langchain:latest
cd ..

print_status "Docker images pushed successfully!"

# Step 2: Configure kubectl
print_status "Step 2: Configuring kubectl..."
aws eks --region ${AWS_REGION} --profile ${AWS_PROFILE} update-kubeconfig --name ${CLUSTER_NAME}

# Step 3: Deploy to Kubernetes
print_status "Step 3: Deploying to existing EKS cluster..."

# Deploy namespace first
kubectl apply -f k8s-deploy/00-namespace.yaml

# Deploy EFS storage
kubectl apply -f k8s-deploy/01-efs-storage.yaml

# Deploy service account
kubectl apply -f k8s-deploy/03-service-account.yaml

# Deploy Weaviate
kubectl apply -f k8s-deploy/02-weaviate-deployment.yaml

# Deploy backend
kubectl apply -f k8s-deploy/backend-deployment.yaml

# Deploy frontend
kubectl apply -f k8s-deploy/frontend-deployment.yaml

print_status "Kubernetes deployment completed!"

# Step 4: Wait for deployments
print_status "Step 4: Waiting for deployments to be ready..."

kubectl wait --for=condition=available --timeout=300s deployment/rag-backend-langchain -n langchain
kubectl wait --for=condition=available --timeout=300s deployment/rag-frontend-langchain -n langchain

# Step 5: Get service information
print_status "Step 5: Getting service information..."

echo ""
echo "🎉 LangChain RAG Solution deployed successfully!"
echo ""
echo "📊 Deployment Status:"
kubectl get pods -n langchain -l app=rag-backend-langchain -o wide
kubectl get pods -n langchain -l app=rag-frontend-langchain -o wide
echo ""

echo "🌐 Services:"
kubectl get svc -n langchain | grep langchain

echo ""
echo "🔗 Frontend URL:"
FRONTEND_URL=$(kubectl get svc rag-frontend-langchain-service -n langchain -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
if [ ! -z "$FRONTEND_URL" ]; then
    echo "http://${FRONTEND_URL}"
else
    print_warning "LoadBalancer URL not ready yet. Check again in a few minutes with:"
    echo "kubectl get svc rag-frontend-langchain-service -n langchain"
fi

echo ""
echo "🏷️ Node Placement:"
echo "Backend pods:"
kubectl get pods -n langchain -l app=rag-backend-langchain -o wide | grep -E "NAME|langchain"
echo "Frontend pods:"
kubectl get pods -n langchain -l app=rag-frontend-langchain -o wide | grep -E "NAME|langchain"

echo ""
echo "📝 Next Steps:"
echo "1. Wait for LoadBalancer to be ready (may take 2-3 minutes)"
echo "2. Access the frontend URL to test the LangChain RAG system"
echo "3. Upload documents and test queries"
echo "4. Compare performance with the original manual backend"

echo ""
print_status "Deployment completed successfully! 🚀"
