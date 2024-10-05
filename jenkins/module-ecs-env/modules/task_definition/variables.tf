variable "family" {
  description = "The family name of the ECS task definition"
}

variable "container_image" {
  description = "The container image to run"
}


variable "container_name" {
  description = "The container image to run"
}

variable "cpu" {
  description = "CPU for the task"
  type        = number
}

variable "memory" {
  description = "Memory for the task"
  type        = number
}

variable "execution_role_arn" {
  description = "The ARN of the task execution role"
}

variable "task_role_arn" {
  description = "The ARN of the task role"
}

variable "network_mode" {
  description = "The network mode for the ECS task definition"
  default     = "awsvpc"
}

variable "compatibilities" {
  description = "The launch compatibility (FARGATE or EC2)"
  type        = list(string)
  default     = ["FARGATE"]
}

variable "container_port" {
  description = "The container port to expose"
  type        = number
  default     = 80
}
