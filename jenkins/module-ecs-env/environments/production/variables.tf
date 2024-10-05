variable "aws_region" {
  description = "The AWS region to deploy resources"
  default     = "ap-southeast-2"
}

variable "ecs_cluster_name" {
  description = "The name of the ECS cluster"
}

variable "subnets" {
  description = "List of subnet IDs"
  type        = list(string)
}

variable "vpc_id" {
  description = "The VPC ID where resources will be deployed"
}

variable "alb_name" {
  description = "The name of the ALB"
}

variable "alb_internal" {
  description = "Is the ALB internal or external?"
  type        = bool
}

variable "target_group_name" {
  description = "The name of the target group"
}

variable "target_group_port" {
  description = "The port for the ALB target group"
  type        = number
}

variable "listener_port" {
  description = "The port for the ALB listener"
  type        = number
}

variable "desired_count" {
  description = "The number of ECS tasks to run"
  type        = number
}

variable "service_name" {
  description = "The name of the ECS service"
}


variable "s3_bucket" {
  description = "The S3 bucket for state storage"
}

variable "s3_key" {
  description = "The S3 key for state storage"
}

variable "task_family" {
  description = "The family name of the ECS task definition"
  type        = string
}

variable "container_image" {
  description = "The container image to be used in the ECS task definition"
  type        = string
}

variable "container_name" {
  description = "The container name to be used in the ECS task definition"
  type        = string
}


variable "container_port" {
  description = "The port the container exposes"
  type        = number
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


