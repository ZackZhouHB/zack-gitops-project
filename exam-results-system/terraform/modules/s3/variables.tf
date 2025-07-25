variable "project_name" {
  description = "The project name."
  type        = string
}

variable "env" {
  description = "The deployment environment."
  type        = string
}

variable "kms_key_arn" {
  description = "The ARN of the KMS key for encryption."
  type        = string
}
