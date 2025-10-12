#!/bin/bash

# Build script for LangChain-based RAG backend

set -e

# Configuration
IMAGE_NAME="rag-backend-langchain"
TAG="latest"
AWS_REGION="ap-southeast-2"
AWS_PROFILE="sandboxtest"

echo "Building LangChain RAG Backend Docker image..."

# Build the Docker image
docker build -t ${IMAGE_NAME}:${TAG} .

echo "Docker image built successfully: ${IMAGE_NAME}:${TAG}"

# Optional: Push to ECR (uncomment when ready)
# echo "Getting ECR login token..."
# aws ecr get-login-password --region ${AWS_REGION} --profile ${AWS_PROFILE} | docker login --username AWS --password-stdin ${ECR_REGISTRY}

# echo "Tagging image for ECR..."
# docker tag ${IMAGE_NAME}:${TAG} ${ECR_REGISTRY}/${IMAGE_NAME}:${TAG}

# echo "Pushing to ECR..."
# docker push ${ECR_REGISTRY}/${IMAGE_NAME}:${TAG}

echo "Build completed successfully!"
echo "To run locally: docker run -p 8000:8000 ${IMAGE_NAME}:${TAG}"
