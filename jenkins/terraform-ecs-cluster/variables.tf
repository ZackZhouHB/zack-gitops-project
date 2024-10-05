variable "aws_region" {
  default = "ap-southeast-2"
}

variable "ecs_cluster_name" {
  default = "zz-ecs"
}

variable "task_family" {
  description = "The family name of the ECS task definition."
}

variable "container_image" {
  default = "zackz001/jenkins:latest"
}

variable "cpu" {
  default = "256"
}

variable "memory" {
  default = "512"
}

variable "desired_count" {
  default = 2
}

variable "subnet_ids" {
  type    = list(string)
  default = ["subnet-080880543de1ce69a", "subnet-073a3529e120d46db"]
}

variable "vpc_id" {
  default = "vpc-0de6953a6686478e8"
}

variable "s3_bucket" {
  default = "zz-lambda-tag"
}

variable "s3_key" {
  default = "terraform/stage/ecs.tfstate"
}


variable "alb_name" {
  description = "The name of the Application Load Balancer"
  default     = "ecs-app-lb" # Default, but can be overridden
}

variable "target_group_name" {
  description = "The name of the ALB target group"
  default     = "ecs-app-target-group"
}

variable "ecs_task_execution_role_name" {
  description = "The name of the ECS task execution role"
  default     = "ecsTaskExecutionRole"
}

variable "ecs_task_role_name" {
  description = "The name of the ECS task role"
  default     = "ecsTaskRole"
}