variable "alb_security_group_name" {
  description = "The name of the ALB security group"
  default     = "alb-security-group"
}

variable "ecs_security_group_name" {
  description = "The name of the ECS security group"
  default     = "ecs-security-group"
}

variable "alb_ingress_cidr_blocks" {
  description = "List of CIDR blocks allowed to access the ALB"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "vpc_id" {
  description = "The VPC ID where the security groups will be created"
}

variable "sg_prefix" {
  description = "Prefix for security group names to make them unique per environment"
}