# =============================================================================
# ECS Cluster, Task Definitions, Services, Service Discovery
# =============================================================================

resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

# -----------------------------------------------------------------------------
# CloudWatch Log Groups
# -----------------------------------------------------------------------------
resource "aws_cloudwatch_log_group" "backend" {
  name              = "/ecs/${var.project_name}/agent-backend"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "frontend" {
  name              = "/ecs/${var.project_name}/frontend"
  retention_in_days = 14
}

# -----------------------------------------------------------------------------
# Task Definitions
# -----------------------------------------------------------------------------
resource "aws_ecs_task_definition" "backend" {
  family                   = "${var.project_name}-backend"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  volume {
    name = "efs-chat-history"
    efs_volume_configuration {
      file_system_id     = aws_efs_file_system.chat_history.id
      root_directory     = "/"
      transit_encryption = "ENABLED"
    }
  }

  container_definitions = jsonencode([{
    name  = "agent-backend"
    image = "${aws_ecr_repository.backend.repository_url}:latest"
    portMappings = [{
      containerPort = 8001
      protocol      = "tcp"
    }]
    mountPoints = [{
      sourceVolume  = "efs-chat-history"
      containerPath = "/mnt/efs"
      readOnly      = false
    }]
    environment = [
      { name = "AWS_REGION", value = var.aws_region },
      { name = "BEDROCK_MODEL_ID", value = var.bedrock_model_id },
      { name = "KNOWLEDGE_BASE_ID", value = aws_bedrockagent_knowledge_base.main.id },
      { name = "DYNAMODB_CHECKLISTS_TABLE", value = aws_dynamodb_table.checklists.name },
      { name = "DYNAMODB_ESCALATIONS_TABLE", value = aws_dynamodb_table.escalations.name },
      { name = "EFS_MOUNT_PATH", value = "/mnt/efs" },
    ]
    healthCheck = {
      command     = ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8001/health')\" || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 10
    }
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.backend.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ecs"
      }
    }
  }])
}

resource "aws_ecs_task_definition" "frontend" {
  family                   = "${var.project_name}-frontend"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name  = "frontend"
    image = "${aws_ecr_repository.frontend.repository_url}:latest"
    portMappings = [{
      containerPort = 8501
      protocol      = "tcp"
    }]
    environment = [
      { name = "AGENT_BACKEND_URL", value = "http://agent-backend.${var.project_name}.local:8001" },
    ]
    healthCheck = {
      command     = ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')\" || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 15
    }
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.frontend.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ecs"
      }
    }
  }])
}

# -----------------------------------------------------------------------------
# Security Group for ECS Tasks
# -----------------------------------------------------------------------------
resource "aws_security_group" "ecs_tasks" {
  name_prefix = "${var.project_name}-ecs-"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    from_port       = 8001
    to_port         = 8001
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  ingress {
    from_port       = 8501
    to_port         = 8501
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  # Allow ECS tasks to talk to each other via service discovery
  ingress {
    from_port = 0
    to_port   = 0
    protocol  = "-1"
    self      = true
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-ecs-tasks"
  }
}

# -----------------------------------------------------------------------------
# Service Discovery (Cloud Map)
# -----------------------------------------------------------------------------
resource "aws_service_discovery_private_dns_namespace" "main" {
  name = "${var.project_name}.local"
  vpc  = data.aws_vpc.default.id
}

resource "aws_service_discovery_service" "backend" {
  name = "agent-backend"
  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.main.id
    dns_records {
      ttl  = 10
      type = "A"
    }
    routing_policy = "MULTIVALUE"
  }
  health_check_custom_config {
    failure_threshold = 1
  }
}

# -----------------------------------------------------------------------------
# ECS Services
# -----------------------------------------------------------------------------
resource "aws_ecs_service" "backend" {
  name            = "${var.project_name}-backend"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.backend.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = data.aws_subnets.default.ids
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.backend.arn
    container_name   = "agent-backend"
    container_port   = 8001
  }

  service_registries {
    registry_arn = aws_service_discovery_service.backend.arn
  }

  depends_on = [aws_lb_listener.http]
}

resource "aws_ecs_service" "frontend" {
  name            = "${var.project_name}-frontend"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.frontend.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = data.aws_subnets.default.ids
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.frontend.arn
    container_name   = "frontend"
    container_port   = 8501
  }

  depends_on = [aws_lb_listener.http]
}
