variable "cluster_name" {
  description = "The name of the EKS cluster"
  type        = string
}

variable "cluster_role_arn" {
  description = "The ARN of the IAM role for the EKS cluster"
  type        = string
}

variable "subnet_ids" {
  description = "The subnet IDs where the EKS cluster will be created"
  type        = list(string)
}

variable "node_role_arn" {
  description = "The ARN of the IAM role for the EKS nodes"
  type        = string
}

variable "desired_capacity" {
  description = "The desired number of nodes in the EKS node group"
  type        = number
}

variable "max_capacity" {
  description = "The maximum number of nodes in the EKS node group"
  type        = number
}

variable "min_capacity" {
  description = "The minimum number of nodes in the EKS node group"
  type        = number
}

variable "launch_template_id" {
  description = "The ID of the launch template to use for the EKS nodes"
  type        = string
}

variable "cluster_security_group_ids" {
  description = "The security group IDs to use for the EKS cluster"
  type        = list(string)
}
