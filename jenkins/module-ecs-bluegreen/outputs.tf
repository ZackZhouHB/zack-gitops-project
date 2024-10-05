output "alb_dns_name" {
  description = "The DNS name of the Application Load Balancer"
  value       = module.alb.alb_dns_name
}

output "ecs_cluster_arn" {
  description = "The ARN of the ECS cluster"
  value       = module.ecs_cluster.ecs_cluster_arn
}

output "ecs_service_name" {
  description = "The name of the ECS service"
  value       = module.ecs_service.ecs_service_name
}

output "ecs_service_arn" {
  description = "The ARN of the ECS service"
  value       = module.ecs_service.ecs_service_arn
}

output "blue_task_definition_arn" {
  description = "The ARN of the blue ECS task definition"
  value       = module.task_definition.blue_task_definition_arn
}

output "green_task_definition_arn" {
  description = "The ARN of the green ECS task definition"
  value       = module.task_definition.green_task_definition_arn
}

output "active_target_group_arn" {
  description = "The ARN of the active target group"
  value       = var.environment == "blue" ? module.alb.blue_target_group_arn : module.alb.green_target_group_arn
}
