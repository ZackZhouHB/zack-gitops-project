variable "project_name" {
  description = "The name of the project."
  type        = string
}

variable "env" {
  description = "The environment (e.g., 'dev', 'prod')."
  type        = string
}

variable "aws_region" {
  description = "The AWS region."
  type        = string
}

variable "aws_account_id" {
  description = "The AWS account ID."
  type        = string
}

variable "kms_key_arn" {
  description = "The ARN of the KMS key."
  type        = string
}

variable "results_bucket_arn" {
  description = "The ARN of the S3 bucket for results."
  type        = string
}

variable "results_table_arn" {
  description = "The ARN of the DynamoDB table for results."
  type        = string
}

variable "email_notification_queue_arn" {
  description = "The ARN of the SQS email notification queue."
  type        = string
}

variable "sms_notification_queue_arn" {
  description = "The ARN of the SQS SMS notification queue."
  type        = string
}