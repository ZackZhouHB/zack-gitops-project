---
title: "AWS Bedrock with Open WebUI"
date: 2025-09-16T14:56:30Z
slug: aws-bedrock-with-open-webui
categories: ["Machine Learning"]
aliases: ["/post/150/"]
legacy_id: 150
---
Recently Data team reached out, trying to build an EC2 running Open WebUI, connecting to AWS Bedrock, to offer team member AI application. This guide provides step-by-step instructions for deploying and integrating with AWS Bedrock models. .

The architecture consists of two Docker containers operating on a single EC2 instance: Open WebUI serves as the user-facing chat interface, while a Bedrock Access Gateway acts as middleware. This gateway securely forwards requests from Open WebUI to the AWS Bedrock API using the EC2 instance's attached IAM role. The containers communicate over a private Docker network, isolating traffic between them.

**Prerequisites**

Before proceeding, ensure the following requirements are met:

- Ensure access granted for desired model via AWS console Bedrock model catelogy
- Launch an EC2 (e.g., Ubuntu 24.04 LTS) and create an IAM role with permissions to access AWS Bedrock (e.g., `bedrock:\*`), and attach to the instance.
- Ensure Security group allows inbound TCP traffic on port 80 for Open WebUI and port 8000 for bedrock-gateway. Also Docker is installed.

**Step 1: Get Bedrock model access granted**

Go AWS console Bedrock, choose the model and request for access.

[![[Image Placeholder 01: Introduction Graphic]](/images/bedrock0.png)](/images/bedrock0.png)

**Step 2: Launch EC2 and Deploy the OpenWebUI Container**

Run the OpenWebUI container, attach it to the previously created network, and map the instance's port 80 to the container's port 8080 for public access.

```bash
# Create a custom network for container communication
docker network create bedrock-net

# Run the OpenWebUI container
docker run -d \
  --name openwebui \
  --network bedrock-net \
  --restart unless-stopped \
  -p 80:8080 \
  ghcr.io/open-webui/open-webui:main
```

**Step 3: Build Bedrock Access Gateway Docker Image**

Clone the official [GitHub repo](https://github.com/aws-samples/bedrock-access-gateway), modify the `Dockerfile\_ecs` to add the AWS CLI package, then Build the custom Docker image and tag it as `bedrock-gateway`:

```bash
git clone https://github.com/aws-samples/bedrock-access-gateway.git
cd bedrock-access-gateway/src

vim Dockerfile_ecs
# add bellow
RUN pip install --no-cache-dir awscli

docker build -f Dockerfile_ecs -t bedrock-gateway .
```

**Step 4: Launch the Bedrock Gateway Securely**

To avoid hardcoding AWS credentials, dynamically fetch temporary credentials from the EC2 instance metadata service and pass them to the Docker container as environment variables. This script fetches the credentials and starts the container.

```bash
# Get a session token from the instance metadata service
TOKEN=$(curl -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")

# Get the IAM role name attached to the instance
ROLE_NAME=$(curl -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/iam/security-credentials/)

# Fetch the full credential set for the role (requires jq)
CREDS=$(curl -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/iam/security-credentials/$ROLE_NAME)
export AWS_ACCESS_KEY_ID=$(echo $CREDS | jq -r '.AccessKeyId')
export AWS_SECRET_ACCESS_KEY=$(echo $CREDS | jq -r '.SecretAccessKey')
export AWS_SESSION_TOKEN=$(echo $CREDS | jq -r '.Token')

# Run the gateway container, injecting the credentials and region
docker run \
  -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
  -e AWS_SESSION_TOKEN=$AWS_SESSION_TOKEN \
  -e AWS_REGION=ap-southeast-2 \
  -d --name bedrock-gateway \
  --network bedrock-net \
  -p 8000:80 \
  bedrock-gateway
```

[![[Image Placeholder 01: Introduction Graphic]](/images/bedrock1.png)](/images/bedrock1.png)

**Step 5: Configure OpenWebUI connection to the Gateway and set up the Bedrock Model**

The final step is to configure OpenWebUI to use the gateway, this can be followed by the [offical Doc](https://docs.openwebui.com/tutorials/integrations/amazon-bedrock/).

1. Navigate to the OpenWebUI interface at your EC2 instance's public IP address and sign up for a local account.

2. Go to **Settings → Connections**.

3. Enter the following API details:

- **API URL**: `http://bedrock-gateway:80/api/v1`. This address resolves correctly because both containers are on the same Docker network.
- **API Key**: `bedrock`. This is a placeholder value, as the gateway relies on the IAM role for authentication.

4. Add the desired Bedrock model IDs, such as `anthropic.claude-3-sonnet-20240229-v1:0`.

[![[Image Placeholder 01: Introduction Graphic]](/images/bedrock2.png)](/images/bedrock2.png)

5. Now we can now start a new chat and select a Bedrock model from the dropdown list.

After addressing a few issues, now we have a fully functional and secure chat interface powered by AWS Bedrock, running in your own environment with no hardcoded credentials.

[![[Image Placeholder 01: Introduction Graphic]](/images/bedrock3.png)](/images/bedrock3.png)

**Evolution Summary: From Manual to Automated**

Our initial approach involved manually deploying two Docker containers on a single EC2 instance: Open WebUI as the chat interface and a Bedrock Access Gateway as middleware. While functional, this manual setup had limitations:

- Manual EC2 provisioning and Docker container management
- No persistent storage - data lost on container restarts
- Single point of failure with one EC2 instance
- Manual credential management via instance metadata
- No infrastructure as code or version control

The manual approach served as our proof of concept, validating the architecture and integration patterns. However, for production use, we needed something more robust and maintainable.

**The Serverless Transformation**

Our new architecture leverages modern AWS services to address every limitation of the manual approach:

```text
Internet → ALB → ECS Service (Fargate)
                    ├── Task 1: OpenWebUI (ECR) + Bedrock Gateway (ECR)
                    └── Task 2: OpenWebUI (ECR) + Bedrock Gateway (ECR)
                              ↓
                         EFS Filesystem (Persistent Storage)
```

**Key Improvements Achieved**

**1. Infrastructure as Code with Terraform**

Everything is now defined in Terraform, enabling version control, reproducible deployments, and easy environment management:

```bash
# Deploy entire infrastructure with one command
terraform init
terraform apply

# Creates: VPC, subnets, ALB, ECS cluster, ECR repositories,
# EFS filesystem, security groups, IAM roles, and more
```

**2. Serverless with ECS Fargate**

No more EC2 instances to manage. Fargate handles all the underlying infrastructure:

- Automatic scaling based on demand
- Built-in high availability across multiple AZs
- No server patching or maintenance
- Pay only for actual container runtime

**3. Container Images in ECR**

Both OpenWebUI and Bedrock Gateway images are now stored in Amazon ECR with automated build and push:

```bash
# Automated image build and deployment
./build-and-push.sh

# Builds custom images and pushes to ECR
# Updates ECS service with new images automatically
```

**4. Persistent Storage with EFS**

The biggest improvement: all user data, chat history, and configurations now persist across deployments:

- Chat conversations survive container restarts
- User uploads and settings maintained
- Shared storage across multiple tasks for session consistency
- Automatic backups and cross-AZ replication

**5. High Availability and Load Balancing**

Application Load Balancer distributes traffic across multiple Fargate tasks:

- Zero-downtime deployments with rolling updates
- Health checks ensure only healthy containers receive traffic
- Automatic failover if a task becomes unhealthy
- SSL termination at the load balancer

**Step 1: Infrastructure Deployment**

Clone the [GitHub repo](https://github.com/ZackZhouHB/zack-gitops-project/tree/editing/mlops/terraform-fargate-bedrock-openwebui) and deploy the complete infrastructure:

```bash
cd terraform-fargate-bedrock-openwebui

# Initialize and deploy infrastructure
terraform init
terraform apply

# Creates: ECR repositories, ECS cluster, VPC, ALB, EFS, security groups
```

**Step 2: Build and Push Container Images**

Automated script handles the entire image build and deployment process:

```bash
# Build and push both images to ECR
./build-and-push.sh

# This script:
# 1. Authenticates with ECR
# 2. Pulls/builds OpenWebUI image
# 3. Builds custom Bedrock Gateway with AWS CLI
# 4. Pushes both images to ECR repositories
# 5. Triggers ECS service update
```

**Step 3: Service Deployment**

ECS automatically deploys the containers with the new images:

```bash
# Deploy ECS service with ECR images
terraform apply

# ECS handles:
# - Task definition updates
# - Rolling deployment
# - Health checks
# - Load balancer registration
```

**Configuration and Usage**

**OpenWebUI Configuration**

With EFS persistence, configuration only needs to be done once:

- **API URL**: `http://localhost:11434/api/v1` (internal container communication)
- **API Key**: Any value (e.g., `bedrock-key`)
- **Models**: Auto-populated from Bedrock Gateway or manually add `anthropic.claude-3-5-haiku-20241022-v1:0`

All settings persist across deployments thanks to EFS storage mounted at `/app/backend/data`.

**Operational Benefits**

**Monitoring and Logging**

- CloudWatch logs for both containers with 7-day retention
- ECS service metrics and health monitoring
- ALB access logs and target group health checks

**Security Improvements**

- No hardcoded credentials - IAM roles for service authentication
- VPC isolation with security groups controlling access
- ECR image vulnerability scanning
- Corporate IP restrictions via security groups

**Cost Optimization**

- Fargate: ~$44/month for 2 tasks (vs. EC2 instance costs)
- EFS: ~$3-5/month for typical usage
- ECR: ~$0.07/month for image storage
- No idle EC2 costs - pay only for actual usage

**Troubleshooting and Maintenance**

[![[Image Placeholder 01: Introduction Graphic]](/images/bedrock4.png)](/images/bedrock4.png)

[![[Image Placeholder 01: Introduction Graphic]](/images/bedrock6.png)](/images/bedrock6.png)

[![[Image Placeholder 01: Introduction Graphic]](/images/bedrock5.png)](/images/bedrock5.png)

**Future Enhancements**

The Terraform-based architecture provides a foundation for additional improvements:

- Auto-scaling based on CPU/memory metrics
- Multi-environment deployments (dev/staging/prod)
- CI/CD pipeline integration with GitHub Actions
- Custom domain with Route 53 and ACM certificates
- Enhanced monitoring with CloudWatch dashboards

This evolution from manual EC2 deployment to automated serverless architecture demonstrates how modern AWS services can transform a proof of concept into a production-ready solution. The combination of Terraform, ECS Fargate, ECR, and EFS provides a robust, scalable, and maintainable platform for AI applications.
