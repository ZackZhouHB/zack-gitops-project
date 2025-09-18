# OpenWebUI ECS Fargate Deployment

Serverless deployment of OpenWebUI with AWS Bedrock using ECS Fargate and ECR for both container images.

## Architecture Overview

```
Internet → ALB → ECS Service (Fargate)
                    ├── Task 1: OpenWebUI (ECR) + Bedrock Gateway (ECR)
                    └── Task 2: OpenWebUI (ECR) + Bedrock Gateway (ECR)
```

## Container Image Strategy

### Both Images in ECR
- **OpenWebUI**: Custom image based on official image, stored in ECR
- **Bedrock Gateway**: Custom-built image with AWS CLI, stored in ECR
- **Benefits**: Full control, corporate compliance, image scanning

## Deployment Steps

### 1. Deploy Infrastructure (Creates ECR Repositories)
```bash
cd terraform-fargate

# Initialize Terraform
terraform init

# Deploy infrastructure - creates ECR repositories
terraform apply
```

### 2. Build and Push Container Images

#### Option A: Simple Approach (Pull + Push OpenWebUI)
```bash
# Pulls official OpenWebUI and builds custom Bedrock Gateway
./build-and-push.sh
```

#### Option B: Custom OpenWebUI Build
```bash
# Builds custom OpenWebUI from Dockerfile.openwebui
./build-and-push-custom.sh
```

### 3. Deploy ECS Service with Images
```bash
# Deploy/update ECS service with ECR images
terraform apply
```

## ECR Repositories Created

### 1. OpenWebUI Repository
- **Name**: `openwebui`
- **Image**: Based on `ghcr.io/open-webui/open-webui:main`
- **Customizations**: Corporate branding, default Bedrock configuration

### 2. Bedrock Gateway Repository  
- **Name**: `bedrock-gateway`
- **Image**: Built from AWS samples with AWS CLI integration
- **Modifications**: Added `awscli` package for AWS authentication

## Build Process Details

### OpenWebUI Image Build
```bash
# Option A: Simple retag
docker pull ghcr.io/open-webui/open-webui:main
docker tag ghcr.io/open-webui/open-webui:main $ECR_URL:latest
docker push $ECR_URL:latest

# Option B: Custom build
docker build -f Dockerfile.openwebui -t openwebui-custom .
docker tag openwebui-custom $ECR_URL:latest
docker push $ECR_URL:latest
```

### Bedrock Gateway Image Build
```bash
git clone https://github.com/aws-samples/bedrock-access-gateway.git
cd bedrock-access-gateway/src

# Add AWS CLI to Dockerfile
echo "RUN pip install --no-cache-dir awscli" >> Dockerfile_ecs

docker build -f Dockerfile_ecs -t bedrock-gateway .
docker tag bedrock-gateway $ECR_URL:latest
docker push $ECR_URL:latest
```

## Image Updates

### Update Both Images
```bash
# Rebuild and push updated images
./build-and-push.sh

# Force ECS service update
terraform apply -replace=aws_ecs_service.openwebui_service
```

### Update Single Image
```bash
# Update just OpenWebUI
docker pull ghcr.io/open-webui/open-webui:main
docker tag ghcr.io/open-webui/open-webui:main $OPENWEBUI_ECR_URL:latest
docker push $OPENWEBUI_ECR_URL:latest

# Force service update
aws ecs update-service --cluster openwebui-cluster --service openwebui-service --force-new-deployment --profile sandboxtest
```

## ECR Management

### View Images
```bash
# List OpenWebUI images
aws ecr describe-images --repository-name openwebui --profile sandboxtest

# List Bedrock Gateway images
aws ecr describe-images --repository-name bedrock-gateway --profile sandboxtest
```

### Image Scanning Results
```bash
# Check vulnerability scan results
aws ecr describe-image-scan-findings --repository-name openwebui --image-id imageTag=latest --profile sandboxtest
```

### Cleanup Old Images
```bash
# Delete old image versions (keep latest)
aws ecr batch-delete-image --repository-name openwebui --image-ids imageTag=old-tag --profile sandboxtest
```

## Cost Considerations

### ECR Storage Costs
- **OpenWebUI**: ~500MB image = ~$0.05/month
- **Bedrock Gateway**: ~200MB image = ~$0.02/month
- **Total ECR**: ~$0.07/month

### Fargate Runtime Costs
- **2 Tasks**: ~$44/month (24/7 operation)
- **Auto-scaling**: Additional costs during peak usage

## Security Features

### ECR Security
- **Vulnerability Scanning**: Automatic scan on push
- **Image Signing**: Optional image signing with AWS Signer
- **Access Control**: IAM-based repository access
- **Encryption**: Images encrypted at rest

### Runtime Security
- **Task IAM Roles**: No hardcoded AWS credentials
- **VPC Networking**: Isolated network per task
- **Security Groups**: Network-level access control
- **Corporate IP Restrictions**: Same CIDR blocks as EC2 approach

## Troubleshooting

### ECR Authentication Issues
```bash
# Re-authenticate with ECR
aws ecr get-login-password --region ap-southeast-2 --profile sandboxtest | \
    docker login --username AWS --password-stdin $ECR_URL
```

### Image Pull Issues
```bash
# Check ECS task events
aws ecs describe-services --cluster openwebui-cluster --services openwebui-service --profile sandboxtest

# Check task definition
aws ecs describe-task-definition --task-definition openwebui-task --profile sandboxtest
```

### Build Issues
```bash
# Test local build
docker build -f Dockerfile.openwebui -t test-openwebui .
docker run -p 8080:8080 test-openwebui

# Test Bedrock Gateway build
cd bedrock-access-gateway/src
docker build -f Dockerfile_ecs -t test-gateway .
```

## Production Enhancements

### Image Versioning
```bash
# Use semantic versioning instead of :latest
docker tag openwebui-custom $ECR_URL:v1.0.0
docker push $ECR_URL:v1.0.0

# Update task definition with specific version
image = "${aws_ecr_repository.openwebui.repository_url}:v1.0.0"
```

### CI/CD Integration
```yaml
# GitHub Actions example
name: Build and Deploy
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Build and push images
        run: ./build-and-push.sh
      - name: Update ECS service
        run: terraform apply -auto-approve
```

### Multi-Environment Support
```bash
# Tag images for different environments
docker tag openwebui-custom $ECR_URL:dev
docker tag openwebui-custom $ECR_URL:staging  
docker tag openwebui-custom $ECR_URL:prod
```
