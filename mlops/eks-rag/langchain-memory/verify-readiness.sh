#!/bin/bash

# Verification script for LangChain RAG deployment readiness

set -e

echo "🔍 Verifying LangChain RAG Deployment Readiness"
echo "================================================"

# Check node group status
echo "1. Checking LangChain node group..."
NODEGROUP_STATUS=$(aws eks describe-nodegroup --cluster-name eks-rag-weaviate --nodegroup-name langchain-nodes --region ap-southeast-2 --profile sandboxtest --query 'nodegroup.status' --output text)
echo "   Node group status: $NODEGROUP_STATUS"

if [ "$NODEGROUP_STATUS" != "ACTIVE" ]; then
    echo "   ❌ Node group not ready yet. Current status: $NODEGROUP_STATUS"
    exit 1
fi

# Check node labels
echo "2. Checking node labels..."
LANGCHAIN_NODES=$(kubectl get nodes -l node-group=langchain --no-headers | wc -l)
echo "   LangChain nodes available: $LANGCHAIN_NODES"

if [ "$LANGCHAIN_NODES" -eq 0 ]; then
    echo "   ❌ No nodes with langchain label found"
    exit 1
fi

# Check ECR images
echo "3. Checking ECR images..."
BACKEND_IMAGE=$(aws ecr describe-images --repository-name rag-backend-langchain --region ap-southeast-2 --profile sandboxtest --query 'imageDetails[?contains(imageTags, `latest`)]' --output text 2>/dev/null)
FRONTEND_IMAGE=$(aws ecr describe-images --repository-name rag-frontend-langchain --region ap-southeast-2 --profile sandboxtest --query 'imageDetails[?contains(imageTags, `latest`)]' --output text 2>/dev/null)

if [ -z "$BACKEND_IMAGE" ]; then
    echo "   ❌ Backend image not found in ECR"
    exit 1
fi

if [ -z "$FRONTEND_IMAGE" ]; then
    echo "   ❌ Frontend image not found in ECR"
    exit 1
fi

echo "   ✅ Backend and frontend images available in ECR"

# Check S3 bucket
echo "4. Checking S3 bucket..."
S3_BUCKET="eks-rag-langchain-docs-615299759525"
aws s3 ls s3://$S3_BUCKET --region ap-southeast-2 --profile sandboxtest > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "   ✅ S3 bucket accessible: $S3_BUCKET"
else
    echo "   ❌ S3 bucket not accessible: $S3_BUCKET"
    exit 1
fi

# Check Kubernetes manifests
echo "5. Checking Kubernetes manifests..."
if [ -f "k8s-deploy/backend-deployment.yaml" ] && [ -f "k8s-deploy/frontend-deployment.yaml" ]; then
    echo "   ✅ Kubernetes manifests present"
    
    # Verify node selector in manifests
    if grep -q "node-group: langchain" k8s-deploy/backend-deployment.yaml && grep -q "node-group: langchain" k8s-deploy/frontend-deployment.yaml; then
        echo "   ✅ Node selectors configured correctly"
    else
        echo "   ❌ Node selectors not configured properly"
        exit 1
    fi
else
    echo "   ❌ Kubernetes manifests missing"
    exit 1
fi

echo ""
echo "🎉 All checks passed! Ready for deployment."
echo ""
echo "Next steps:"
echo "1. Run: ./deploy.sh"
echo "2. Monitor deployment: kubectl get pods -n rag-system -w"
echo "3. Check node placement: kubectl get pods -n rag-system -o wide"
