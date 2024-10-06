variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-southeast-2"
}

variable "cluster_name" {
  description = "EKS Cluster name"
  type        = string
  default     = "module-eks-cluster-stage"
}

variable "vpc_id" {
  description = "VPC ID for EKS"
  type        = string
}

variable "subnets" {
  description = "Subnets for EKS"
  type        = list(string)
}

variable "node_group_instance_type" {
  description = "Instance type for the node groups"
  type        = string
}

variable "desired_capacity" {
  description = "Desired capacity for the node group"
  type        = number
}

variable "max_capacity" {
  description = "Maximum capacity for the node group"
  type        = number
}

variable "min_capacity" {
  description = "Minimum capacity for the node group"
  type        = number
}

variable "s3_bucket" {
  description = "S3 bucket name for Terraform state"
  type        = string
}

variable "disk_size" {
  description = "Disk size for the node group in GB"
  type        = number
}

variable "environment" {
  description = "Environment name (e.g., dev, prod)"
  type        = string
}

variable "instance_type" {
  description = "Instance type for the EKS cluster nodes."
  type        = string
}

variable "eks_version" {
  description = "eks version for the EKS cluster nodes."
  type        = string
}
