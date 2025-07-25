variable "function_name" {
  description = "The name of the Lambda function."
  type        = string
}

variable "role_arn" {
  description = "The ARN of the IAM role for the Lambda."
  type        = string
}

variable "handler" {
  description = "The handler for the Lambda function."
  type        = string
  default     = "handler.handler"
}

variable "runtime" {
  description = "The runtime for the Lambda function."
  type        = string
  default     = "python3.11"
}

variable "timeout" {
  description = "The timeout for the Lambda function."
  type        = number
  default     = 60
}

variable "memory_size" {
  description = "The memory size for the Lambda function."
  type        = number
  default     = 128
}

variable "source_dir" {
  description = "The source directory for the Lambda function code."
  type        = string
}

variable "environment_variables" {
  description = "A map of environment variables for the Lambda function."
  type        = map(string)
  default     = {}
}

variable "deployment_packages_bucket_id" {
  description = "The ID of the S3 bucket for Lambda deployment packages."
  type        = string
}

variable "dist_path" {
  description = "The path to the dist directory."
  type        = string
}