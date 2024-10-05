output "ecs_service_task_definition" {
  description = "The task definition for the ECS service"
  value       = aws_ecs_service.app_service.task_definition
}


output "ecs_service_name" {
  description = "The name of the ECS service"
  value       = aws_ecs_service.app_service.name
}

output "ecs_service_arn" {
  description = "The ARN of the ECS service"
  value       = aws_ecs_service.app_service.id
}
