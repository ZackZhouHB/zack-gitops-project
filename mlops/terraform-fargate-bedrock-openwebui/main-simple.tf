# Simplified Fargate - No ECR required
# Use this if you build and push bedrock-gateway to Docker Hub

# Remove ECR repository section entirely

# Simplified task definition
resource "aws_ecs_task_definition" "openwebui_task_simple" {
  family                   = "openwebui-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "1024"
  memory                   = "2048"
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  task_role_arn           = aws_iam_role.ecs_task_role.arn
  
  container_definitions = jsonencode([
    {
      name  = "openwebui"
      image = "ghcr.io/open-webui/open-webui:main"  # Public registry
      
      portMappings = [{
        containerPort = 8080
        protocol      = "tcp"
      }]
      
      environment = [
        {
          name  = "OPENAI_API_BASE_URL"
          value = "http://localhost:8000/api/v1"
        }
      ]
      
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
      image = "your-dockerhub/bedrock-gateway:latest"  # Your Docker Hub image
      
      portMappings = [{
        containerPort = 8000
        protocol      = "tcp"
      }]
      
      environment = [
        {
          name  = "AWS_REGION"
          value = var.aws_region
        }
      ]
      
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
}
