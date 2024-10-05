resource "aws_ecs_service" "app_service" {
  name            = var.service_name      # Parameterized
  cluster         = var.cluster_arn
  task_definition = var.task_definition_arn  # Reference task definition created by the task_definition module
  launch_type     = var.launch_type       # Parameterized

  network_configuration {
    subnets         = var.subnets
    security_groups = var.security_groups
    assign_public_ip = var.assign_public_ip  # Parameterized
  }

  desired_count = var.desired_count

  load_balancer {
    target_group_arn = var.target_group_arn
    container_name   = var.container_name    # Parameterized
    container_port   = var.container_port    # Parameterized
  }

  depends_on = [var.dependency]
}
