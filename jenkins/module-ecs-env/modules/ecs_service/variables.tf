variable "service_name" {
  description = "The name of the ECS service"
}

variable "cluster_arn" {
  description = "The ARN of the ECS cluster"
}

variable "task_definition_arn" {
  description = "The ARN of the task definition"
}

variable "launch_type" {
  description = "The launch type for the ECS service (EC2 or FARGATE)"
  default     = "FARGATE"
}

variable "subnets" {
  description = "List of subnet IDs"
  type        = list(string)
}

variable "security_groups" {
  description = "List of security group IDs"
  type        = list(string)
}

variable "assign_public_ip" {
  description = "Should the service assign a public IP?"
  type        = bool
  default     = true
}

variable "desired_count" {
  description = "Number of desired ECS tasks"
  type        = number
}

variable "target_group_arn" {
  description = "The ARN of the ALB target group"
}

variable "container_name" {
  description = "The name of the container"
}

variable "container_port" {
  description = "The port the container listens on"
  type        = number
  default     = 80
}

variable "dependency" {
  description = "Dependency for the ECS service"
}
