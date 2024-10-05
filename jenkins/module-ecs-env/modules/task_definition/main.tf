resource "aws_ecs_task_definition" "app" {
  family                   = var.family        # Parameterized
  network_mode             = var.network_mode  # Parameterized
  requires_compatibilities = var.compatibilities  # Parameterized
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = var.execution_role_arn
  task_role_arn            = var.task_role_arn

  container_definitions = jsonencode([{
    name      = var.container_name
    image     = var.container_image
    cpu       = var.cpu
    memory    = var.memory
    essential = true
    portMappings = [{
      containerPort = var.container_port  # Parameterized
      protocol      = "tcp"
    }]
  }])
}
