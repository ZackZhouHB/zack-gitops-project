variable "aws_region" {
  description = "The AWS region to deploy resources"
  default     = "ap-southeast-2"
}

variable "ecs_cluster_name" {
  description = "The name of the ECS cluster"
  default     = "zz-ecs"
}

variable "subnets" {
  description = "List of subnet IDs"
  type        = list(string)
  default     = ["subnet-080880543de1ce69a", "subnet-073a3529e120d46db"]
}

variable "vpc_id" {
  description = "The VPC ID where resources will be deployed"
  default     = "vpc-0de6953a6686478e8"
}

variable "desired_count" {
  description = "The number of ECS tasks to run"
  default     = 2
}

variable "s3_bucket" {
  description = "The S3 bucket for state storage"
  default     = "zz-asb-k8s-velero-backup-bucket"
}

variable "s3_key" {
  description = "The S3 key for state storage"
  default     = "terraform/module/prod/ecs.tfstate"
}

variable "task_family" {
  description = "The family name of the ECS task definition"
  type        = string
}

variable "container_image" {
  description = "The container image to be used in the ECS task definition"
  type        = string
}

variable "cpu" {
  description = "CPU units to allocate to the ECS task"
  type        = number
  default     = 256 # Ensure this is an integer
}

variable "memory" {
  description = "Memory (in MiB) to allocate to the ECS task"
  type        = number
  default     = 512 # Ensure this is an integer
}

variable "environment" {
  description = "The environment to deploy (blue or green)"
  type        = string
  default     = "blue"
}