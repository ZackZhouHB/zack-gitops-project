variable "name" {
  description = "The name of the load balancer"
}

variable "internal" {
  description = "Is the load balancer internal?"
  type        = bool
  default     = false
}

variable "security_groups" {
  description = "List of security group IDs"
  type        = list(string)
}

variable "subnets" {
  description = "List of subnet IDs"
  type        = list(string)
}

variable "vpc_id" {
  description = "VPC ID"
}

variable "target_group_name" {
  description = "Name of the target group"
}

variable "target_group_port" {
  description = "Port for the target group"
  type        = number
  default     = 80
}

variable "health_check_path" {
  description = "Path for health check"
  default     = "/"
}

variable "health_check_interval" {
  description = "Health check interval in seconds"
  default     = 30
}

variable "health_check_timeout" {
  description = "Health check timeout in seconds"
  default     = 5
}

variable "healthy_threshold" {
  description = "Number of consecutive successful health checks"
  default     = 2
}

variable "unhealthy_threshold" {
  description = "Number of consecutive failed health checks"
  default     = 2
}

variable "matcher" {
  description = "HTTP matcher code for health check"
  default     = "200"
}

variable "listener_port" {
  description = "Port for the load balancer listener"
  type        = number
  default     = 80
}
