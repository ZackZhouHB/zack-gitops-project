output "alb_dns_name" {
  description = "ALB DNS name"
  value       = aws_lb.openwebui_alb.dns_name
}

output "openwebui_url" {
  description = "OpenWebUI access URL via ALB"
  value       = "http://${aws_lb.openwebui_alb.dns_name}"
}

output "bedrock_gateway_ecr_repository_url" {
  description = "ECR repository URL for Bedrock Gateway"
  value       = aws_ecr_repository.bedrock_gateway.repository_url
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.openwebui_cluster.name
}

output "ecs_service_name" {
  description = "ECS service name"
  value       = aws_ecs_service.openwebui_service.name
}

output "efs_filesystem_id" {
  description = "EFS filesystem ID for persistent data"
  value       = aws_efs_file_system.openwebui_data.id
}
