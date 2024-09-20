---
layout: post
title:  "Serverless with AWS Fargate"
date:   2024-07-10 11:15:29 +1100
categories: jekyll Cat2
---

<b>Why go serverless</b>

Some of the company's applications recently moved from Rancher to Fargate, which is understandable as the cloud resource and traffic will be very intensive only during a certain period (HSC exam), hence AWS serverless with Fargate can be a better option for such business mode so rest of the year without exam we can save cost significantly. 

<b>Hosting our blog on Fargate? Why not!</b>

In the past, I used to try different methods to host this blog:

- [EC2 with docker](https://zackz.site/jekyll/cat2/2023/11/02/about-this-project.html)
- [K8s with ArgoCD](https://zackz.site/jekyll/cat2/2023/11/07/ArgoCD.html)
- [S3 with static website](https://zackz.site/jekyll/cat2/2024/04/30/serverless.html)
- [Customize Helm Chart for Zack' Blog](https://zackz.site/jekyll/cat2/2024/05/12/Helm.html)

Here I will use AWS Fargate, together with AWS ECR, Docker, Terraform and Github Action workflow to move this blog to AWS serverless compute for containers. 

- Terraform Provisioning

{% highlight shell %}

# Provider Configuration  "provider.tf"
provider "aws" {
 region = "ap-southeast-2"
}

# Create an ECR Repository "ecr.tf"
resource "aws_ecr_repository" "zackblog_repo" {
 name = "zackblog-repo"
}

# Fargate Task Definition  "task_definition.tf"
resource "aws_ecs_task_definition" "zackblog_task" {
 family                   = "zackblog-task"
 network_mode             = "awsvpc"
 requires_compatibilities = ["FARGATE"]
 cpu                      = "256"
 memory                   = "512"

 container_definitions = jsonencode([
 {
 name      = "zackblog-container",
 image     = "${aws_ecr_repository.zackblog_repo.repository_url}:latest",
 essential = true,
 portMappings = [
 {
 containerPort = 80,
 hostPort      = 80,
 protocol      = "tcp"
 }
 ]
 }
 ])
}

# Create an ECS Cluster "cluster.tf"
resource "aws_ecs_cluster" "zackblog_cluster" {
 name = "zackblog-cluster"
}

# Configure Networking to Use Default VPC - save cost haha
# use the data block to fetch existing resources
data "aws_vpc" "default" {
 default = true
}

data "aws_subnet" "default" {
 filter {
 name   = "vpc-id"
 values = [data.aws_vpc.default.id]
 }
}

resource "aws_security_group" "zackblog_sg" {
 name_prefix = "zackblog-sg"
 vpc_id      = data.aws_vpc.default.id

 ingress {
 from_port   = 80
 to_port     = 80
 protocol    = "tcp"
 cidr_blocks = ["0.0.0.0/0"]
 }

 egress {
 from_port   = 0
 to_port     = 0
 protocol    = "-1"
 cidr_blocks = ["0.0.0.0/0"]
 }
}

# Define the ECS Service "service.tf"
resource "aws_ecs_service" "zackblog_service" {
 name            = "zackblog-service"
 cluster         = aws_ecs_cluster.zackblog_cluster.id
 task_definition = aws_ecs_task_definition.zackblog_task.arn
 desired_count   = 1
 launch_type     = "FARGATE"

 network_configuration {
 subnets         = [for subnet in data.aws_subnet.default : subnet.id]
 security_groups = [aws_security_group.zackblog_sg.id]
 assign_public_ip = true
 }
}

# Configure Load Balancer and attach to Fargate service "load_balancer.tf"
resource "aws_lb" "zackblog_lb" {
 name               = "zackblog-lb"
 internal           = false
 load_balancer_type = "application"
 security_groups    = [aws_security_group.zackblog_sg.id]
 subnets            = [for subnet in data.aws_subnet.default : subnet.id]
}

resource "aws_lb_target_group" "zackblog_tg" {
 name     = "zackblog-tg"
 port     = 80
 protocol = "HTTP"
 vpc_id   = data.aws_vpc.default.id
}

resource "aws_lb_listener" "zackblog_listener" {
 load_balancer_arn = aws_lb.zackblog_lb.arn
 port              = 80
 protocol          = "HTTP"

 default_action {
 type             = "forward"
 target_group_arn = aws_lb_target_group.zackblog_tg.arn
 }
}

resource "aws_lb_target_group_attachment" "zackblog_tg_attachment" {
 target_group_arn = aws_lb_target_group.zackblog_tg.arn
 target_id        = aws_ecs_service.zackblog_service.id
 port             = 80
}
{% endhighlight %}

- Github Action Workflow fo CICD

1.First we need to create Github Secret to contain dockerhub and aws credentials and some other vars:

{% highlight shell %}
AWS_ACCESS_KEY_ID

AWS_SECRET_ACCESS_KEY

AWS_REGION

# xxx.dkr.ecr.ap-southeast-2.amazonaws.com
ECR_REGISTRY  

# zackblog-repo
ECR_REPOSITORY  

# zackblog-cluster
ECS_CLUSTER 

# zackblog-service
ECS_SERVICE 
{% endhighlight %}

2.Then define the workflow to create /.github/workflows/zackblog-fargate.yaml, in this configure Github runner, it will : 

Log in to Amazon ECR

Build and push Docker Image to the ECR repository

Deploy to ECS by updating the ECS service to use the new image by forcing a new deployment


{% highlight yaml %}
name: Deploy to AWS Fargate

on:
 push:
 branches:
 - editing  # not main branch

jobs:
 deploy:
 runs-on: ubuntu-latest

 steps:
 - name: Checkout code
 uses: actions/checkout@v3

 - name: Set up Docker Buildx
 uses: docker/setup-buildx-action@v2

 - name: Log in to Amazon ECR
 env:
 AWS_REGION: {% raw %}${{ secrets.AWS_REGION }}{% endraw %}
 run: |
 aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin {% raw %}${{ secrets.ECR_REGISTRY }}{% endraw %}

 - name: Build and push Docker image
 env:
 IMAGE_TAG: {% raw %}${{ github.sha }}{% endraw %}
 ECR_REGISTRY: {% raw %}${{ secrets.ECR_REGISTRY }}{% endraw %}
 ECR_REPOSITORY: {% raw %}${{ secrets.ECR_REPOSITORY }}{% endraw %}
 run: |
 docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
 docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG

 - name: Deploy to ECS
 env:
 AWS_REGION: {% raw %}${{ secrets.AWS_REGION }}{% endraw %}
 ECS_CLUSTER: {% raw %}${{ secrets.ECS_CLUSTER }}{% endraw %}
 ECS_SERVICE: {% raw %}${{ secrets.ECS_SERVICE }}{% endraw %}
 ECR_REGISTRY: {% raw %}${{ secrets.ECR_REGISTRY }}{% endraw %}
 ECR_REPOSITORY: {% raw %}${{ secrets.ECR_REPOSITORY }}{% endraw %}
 IMAGE_TAG: {% raw %}${{ github.sha }}{% endraw %}
 run: |
 aws ecs update-service --cluster $ECS_CLUSTER --service $ECS_SERVICE --force-new-deployment --region $AWS_REGION

{% endhighlight %}

<b> Conclusion</b>

Now we have a seamless incurvature as a code together with CICD pipeline to ensure that the "Zack's Blog" can be moved to AWS serverless container service Fargate, every time I update the blog by committing changes to "zack-gitops-project" editing branch, a new Docker image will be built, pushed to ECR, and the AWS Fargate service is automatically updated.  