terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile
}

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# ECR Repository only for Bedrock Gateway (custom build)
resource "aws_ecr_repository" "bedrock_gateway" {
  name                 = "bedrock-gateway"
  image_tag_mutability = "MUTABLE"
  force_delete         = true  # Allow deletion even with images
  
  image_scanning_configuration {
    scan_on_push = true
  }
  
  tags = {
    Name      = "bedrock-gateway"
    createdby = var.created_by
  }
}

# EFS File System for persistent data
resource "aws_efs_file_system" "openwebui_data" {
  creation_token = "openwebui-data"
  
  performance_mode = "generalPurpose"
  throughput_mode  = "provisioned"
  provisioned_throughput_in_mibps = 10
  
  tags = {
    Name      = "openwebui-data"
    createdby = var.created_by
  }
}

# EFS Mount Targets (one per subnet for availability)
resource "aws_efs_mount_target" "openwebui_data" {
  count           = length(data.aws_subnets.default.ids)
  file_system_id  = aws_efs_file_system.openwebui_data.id
  subnet_id       = data.aws_subnets.default.ids[count.index]
  security_groups = [aws_security_group.efs_sg.id]
}

# EFS Security Group - Allow NFS access from ECS tasks
resource "aws_security_group" "efs_sg" {
  name_prefix = "efs-sg"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description     = "NFS from ECS tasks"
    from_port       = 2049
    to_port         = 2049
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_sg.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name      = "efs-sg"
    createdby = var.created_by
  }
}

# ECS Cluster
resource "aws_ecs_cluster" "openwebui_cluster" {
  name = "openwebui-cluster"
  
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
  
  tags = {
    Name      = "openwebui-cluster"
    createdby = var.created_by
  }
}

# IAM Role for ECS Tasks
resource "aws_iam_role" "ecs_task_role" {
  name = "ecs-openwebui-task-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
  
  tags = {
    Name      = "ecs-openwebui-task-role"
    createdby = var.created_by
  }
}

# IAM Policy for Bedrock access
resource "aws_iam_role_policy" "bedrock_policy" {
  name = "BedrockAccessPolicy"
  role = aws_iam_role.ecs_task_role.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["bedrock:*"]
      Resource = "*"
    }]
  })
}

# ECS Task Execution Role
resource "aws_iam_role" "ecs_execution_role" {
  name = "ecs-openwebui-execution-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
  
  tags = {
    Name      = "ecs-openwebui-execution-role"
    createdby = var.created_by
  }
}

resource "aws_iam_role_policy_attachment" "ecs_execution_role_policy" {
  role       = aws_iam_role.ecs_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "openwebui_logs" {
  name              = "/ecs/openwebui"
  retention_in_days = 7
  
  tags = {
    Name      = "openwebui-logs"
    createdby = var.created_by
  }
}

resource "aws_cloudwatch_log_group" "bedrock_gateway_logs" {
  name              = "/ecs/bedrock-gateway"
  retention_in_days = 7
  
  tags = {
    Name      = "bedrock-gateway-logs"
    createdby = var.created_by
  }
}

# Security Groups
resource "aws_security_group" "alb_sg" {
  name_prefix = "alb-sg"
  vpc_id      = data.aws_vpc.default.id
  
  # Corporate IP restrictions + temporary public access
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = [
      "10.103.0.0/16",
      "10.104.0.0/16", 
      "10.102.2.0/24",
      "10.80.0.0/22",
      "10.80.4.0/22",
      "10.80.8.0/22",
      "0.0.0.0/0" # Temporary for local testing
    ]
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = {
    Name      = "alb-sg"
    createdby = var.created_by
  }
}

resource "aws_security_group" "ecs_sg" {
  name_prefix = "ecs-sg"
  vpc_id      = data.aws_vpc.default.id
  
  ingress {
    from_port       = 8080
    to_port         = 8080
    protocol        = "tcp"
    security_groups = [aws_security_group.alb_sg.id]
  }
  
  ingress {
    from_port = 8000
    to_port   = 8000
    protocol  = "tcp"
    self      = true
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = {
    Name      = "ecs-sg"
    createdby = var.created_by
  }
}

# Application Load Balancer
resource "aws_lb" "openwebui_alb" {
  name               = "openwebui-fargate-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb_sg.id]
  subnets           = data.aws_subnets.default.ids

  tags = {
    Name      = "openwebui-fargate-alb"
    createdby = var.created_by
  }
}

resource "aws_lb_target_group" "openwebui_tg" {
  name        = "openwebui-fargate-tg"
  port        = 8080
  protocol    = "HTTP"
  vpc_id      = data.aws_vpc.default.id
  target_type = "ip"
  
  health_check {
    path                = "/"
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 5
    interval            = 30
    matcher             = "200"
  }
  
  tags = {
    Name      = "openwebui-fargate-tg"
    createdby = var.created_by
  }
}

resource "aws_lb_listener" "openwebui_listener" {
  load_balancer_arn = aws_lb.openwebui_alb.arn
  port              = "80"
  protocol          = "HTTP"
  
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.openwebui_tg.arn
  }
}

# ECS Task Definition
resource "aws_ecs_task_definition" "openwebui_task" {
  family                   = "openwebui-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "2048"  # 2 vCPU
  memory                   = "4096"  # 4 GB RAM
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  task_role_arn           = aws_iam_role.ecs_task_role.arn
  
  container_definitions = jsonencode([
    {
      name  = "openwebui"
      image = "ghcr.io/open-webui/open-webui:main"  # Pull directly from public registry
      
      portMappings = [{
        containerPort = 8080
        protocol      = "tcp"
      }]
      
      environment = [
        {
          name  = "DATA_DIR"
          value = "/app/backend/data"
        },
        {
          name  = "WEBUI_SECRET_KEY_FILE"
          value = "/app/backend/data/.webui_secret_key"
        }
      ]
      
      # EFS Mount Point for persistent data
      mountPoints = [{
        sourceVolume  = "openwebui-data"
        containerPath = "/app/backend/data"
        readOnly      = false
      }]
      
      # Temporarily remove health dependency
      # dependsOn = [
      #   {
      #     containerName = "bedrock-gateway"
      #     condition     = "HEALTHY"
      #   }
      # ]
      
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.openwebui_logs.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
      
      essential = true
    },
    {
      name  = "bedrock-gateway"
      image = "${aws_ecr_repository.bedrock_gateway.repository_url}:latest"  # Custom ECR image
      
      portMappings = [{
        containerPort = 80
        protocol      = "tcp"
      }]
      
      environment = [
        {
          name  = "AWS_REGION"
          value = var.aws_region
        }
      ]
      
      # Temporarily disable health check to troubleshoot
      # healthCheck = {
      #   command     = ["CMD-SHELL", "curl http://localhost:80/ || exit 1"]
      #   interval    = 30
      #   timeout     = 5
      #   retries     = 3
      #   startPeriod = 60
      # }
      

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.bedrock_gateway_logs.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
      
      essential = true
    }
  ])
  
  # EFS Volume for persistent data
  volume {
    name = "openwebui-data"
    
    efs_volume_configuration {
      file_system_id = aws_efs_file_system.openwebui_data.id
      root_directory = "/"
    }
  }
  
  tags = {
    Name      = "openwebui-task"
    createdby = var.created_by
  }
}

# ECS Service
resource "aws_ecs_service" "openwebui_service" {
  name            = "openwebui-service"
  cluster         = aws_ecs_cluster.openwebui_cluster.id
  task_definition = aws_ecs_task_definition.openwebui_task.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"
  
  network_configuration {
    subnets          = data.aws_subnets.default.ids
    security_groups  = [aws_security_group.ecs_sg.id]
    assign_public_ip = true
  }
  
  load_balancer {
    target_group_arn = aws_lb_target_group.openwebui_tg.arn
    container_name   = "openwebui"
    container_port   = 8080
  }
  
  depends_on = [aws_lb_listener.openwebui_listener]
  
  tags = {
    Name      = "openwebui-service"
    createdby = var.created_by
  }
}
