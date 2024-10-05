resource "aws_ecs_service" "app_service" {
  name            = var.service_name
  cluster         = var.cluster_arn
  task_definition = var.task_definition_arn
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = var.subnets
    security_groups = var.security_groups
    assign_public_ip = true
  }

  desired_count = var.desired_count

  load_balancer {
    target_group_arn = var.active_target_group_arn
    container_name   = var.container_name
    container_port   = var.container_port
  }

  depends_on = [var.dependency]
}
