output "alb_dns_name" {
  description = "The DNS name of the ALB"
  value       = aws_lb.app.dns_name
}

output "alb_arn" {
  description = "The ARN of the ALB"
  value       = aws_lb.app.arn
}

output "target_group_arn" {
  description = "The ARN of the target group"
  value       = aws_lb_target_group.app.arn
}

output "listener_arn" {
  description = "The ARN of the ALB listener"
  value       = aws_lb_listener.front_end.arn
}
