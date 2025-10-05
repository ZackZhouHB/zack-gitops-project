variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-southeast-2"
}

variable "aws_profile" {
  description = "AWS profile"
  type        = string
  default     = "sandboxtest"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "node_group_instance_types" {
  description = "Instance types for EKS node group"
  type        = list(string)
  default     = ["t3.large"]
}

variable "node_group_min_size" {
  description = "Minimum size of the node group"
  type        = number
  default     = 2
}

variable "node_group_max_size" {
  description = "Maximum size of the node group"
  type        = number
  default     = 3
}

variable "node_group_desired_size" {
  description = "Desired size of the node group"
  type        = number
  default     = 2
}
