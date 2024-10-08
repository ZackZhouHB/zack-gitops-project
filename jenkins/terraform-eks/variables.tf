variable "aws_region" {
  description = "The AWS region to deploy the EKS cluster."
  type        = string
}

variable "cluster_name" {
  description = "The name of the EKS cluster."
  type        = string
}

variable "desired_size" {
  description = "The desired number of nodes in the node group."
  type        = number
}

variable "max_size" {
  description = "The maximum number of nodes in the node group."
  type        = number
}

variable "min_size" {
  description = "The minimum number of nodes in the node group."
  type        = number
}

variable "instance_type" {
  description = "The EC2 instance type for the EKS nodes."
  type        = string
}

variable "disk_size" {
  description = "The size of the EBS volume attached to the nodes in GB."
  type        = number
}

variable "vpc_id" {
  description = "default vpc."
  type        = string
}

variable "subnet_ids" {
  description = "List of subnet IDs."
  type        = list(string) # Change from string to list(string)
}

variable "role_prefix" {
  description = "A prefix for IAM role names to avoid duplication across environments."
  type        = string
  default     = "myapp" # Default value, you can change it as needed
}

variable "s3_key" {
  description = "default s3"
  type        = string
}

variable "s3_bucket" {
  description = "The name of the S3 bucket for storing Terraform state."
  type        = string
}

variable "environment" {
  description = "The environment (e.g., dev, prod) for the Terraform state."
  type        = string
}
