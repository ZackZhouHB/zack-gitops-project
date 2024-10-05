variable "family" {
  description = "The family name of the ECS task definition"
}

variable "container_image" {
  description = "The container image to run"
}

variable "cpu" {
  description = "CPU for the task"
}

variable "memory" {
  description = "Memory for the task"
}

variable "execution_role_arn" {
  description = "The ARN of the task execution role"
}

variable "task_role_arn" {
  description = "The ARN of the task role"
}
