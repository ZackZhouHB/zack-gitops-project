# Outputs for the security group IDs

output "alb_sg" {
  description = "The ALB security group ID"
  value       = aws_security_group.alb_sg.id
}

output "ecs_sg" {
  description = "The ECS security group ID"
  value       = aws_security_group.ecs_sg.id
}
