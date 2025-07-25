variable "aws_region" {
  description = "The AWS region for deployment."
  type        = string
  default     = "ap-southeast-2"
}

variable "project_name" {
  description = "A unique name for the project."
  type        = string
  default     = "hsc-results"
}

variable "env" {
  description = "The deployment environment (e.g., 'dev', 'prod')."
  type        = string
}

variable "sender_email" {
  description = "The 'From' email address for notifications, verified in SES."
  type        = string
}

variable "verified_phone_numbers" {
  description = "List of phone numbers to register with SNS for SMS notifications (E.164 format: +61452025776)"
  type        = list(string)
  default     = []
}
