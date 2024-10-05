resource "aws_ecs_task_definition" "app" {
  family                   = var.task_family
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn # Use the IAM role created by Terraform
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name      = "app"
      image     = var.container_image # Use a variable for the container image
      cpu       = 256
      memory    = 512
      essential = true
      portMappings = [{
        containerPort = 80
        protocol      = "tcp"
      }]
    }
  ])
}
