output "blue_task_definition_arn" {
  description = "The ARN of the blue ECS task definition"
  value       = aws_ecs_task_definition.blue.arn
}

output "green_task_definition_arn" {
  description = "The ARN of the green ECS task definition"
  value       = aws_ecs_task_definition.green.arn
}
