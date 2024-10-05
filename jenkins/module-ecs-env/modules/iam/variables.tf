variable "execution_role_name" {
  description = "Name of the ECS Task Execution Role"
  default     = "ecsTaskExecutionRole"
}

variable "execution_policy_arn" {
  description = "The ARN of the ECS Task Execution Role Policy"
  default     = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

variable "task_role_name" {
  description = "Name of the ECS Task Role"
  default     = "ecsTaskRole"
}

variable "role_prefix" {
  description = "Prefix for IAM role names to make them unique per environment"
}