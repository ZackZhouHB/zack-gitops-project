#!/bin/bash
set -e

# Configuration
AWS_REGION="ap-southeast-2"
AWS_PROFILE="sandboxtest"

echo "Building and pushing both custom images to ECR..."

# Get ECR repository URLs from Terraform output
OPENWEBUI_ECR_URL=$(terraform output -raw openwebui_ecr_repository_url)
BEDROCK_GATEWAY_ECR_URL=$(terraform output -raw bedrock_gateway_ecr_repository_url)

if [ -z "$OPENWEBUI_ECR_URL" ] || [ -z "$BEDROCK_GATEWAY_ECR_URL" ]; then
    echo "Error: Could not get ECR repository URLs. Run 'terraform apply' first."
    exit 1
fi

echo "OpenWebUI ECR: $OPENWEBUI_ECR_URL"
echo "Bedrock Gateway ECR: $BEDROCK_GATEWAY_ECR_URL"

# Login to ECR
aws ecr get-login-password --region $AWS_REGION --profile $AWS_PROFILE | \
    docker login --username AWS --password-stdin $OPENWEBUI_ECR_URL

echo "=== Building Custom OpenWebUI Image ==="
# Build custom OpenWebUI from local Dockerfile
docker build -f Dockerfile.openwebui -t openwebui-custom:latest .
docker tag openwebui-custom:latest $OPENWEBUI_ECR_URL:latest

# Push OpenWebUI to ECR
echo "Pushing custom OpenWebUI to ECR..."
docker push $OPENWEBUI_ECR_URL:latest

echo "=== Building Bedrock Gateway Image ==="
# Clone and build Bedrock Gateway
echo "Cloning Bedrock Gateway repository..."
rm -rf bedrock-access-gateway
git clone https://github.com/aws-samples/bedrock-access-gateway.git
cd bedrock-access-gateway/src

# Modify Dockerfile to include AWS CLI
echo "Modifying Dockerfile to include AWS CLI..."
cat >> Dockerfile_ecs << 'EOF'
RUN pip install --no-cache-dir awscli
EOF

# Build the Bedrock Gateway image
echo "Building Bedrock Gateway Docker image..."
docker build -f Dockerfile_ecs -t bedrock-gateway:latest .

# Tag for ECR
docker tag bedrock-gateway:latest $BEDROCK_GATEWAY_ECR_URL:latest

# Push Bedrock Gateway to ECR
echo "Pushing Bedrock Gateway to ECR..."
docker push $BEDROCK_GATEWAY_ECR_URL:latest

echo "=== Build and Push Completed Successfully! ==="
echo "OpenWebUI ECR: $OPENWEBUI_ECR_URL:latest"
echo "Bedrock Gateway ECR: $BEDROCK_GATEWAY_ECR_URL:latest"

# Cleanup
cd ../..
rm -rf bedrock-access-gateway

echo "Next step: Run 'terraform apply' to update ECS service with new images"
