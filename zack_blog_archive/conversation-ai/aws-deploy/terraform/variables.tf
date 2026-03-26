variable "aws_region" {
  default = "ap-southeast-2"
}

variable "aws_profile" {
  default = "sandboxtest"
}

variable "project_name" {
  default = "platform-health"
}

variable "bedrock_model_id" {
  default = "apac.anthropic.claude-sonnet-4-20250514-v1:0"
}

variable "bedrock_embed_model_id" {
  default = "amazon.titan-embed-text-v2:0"
}

variable "confluence_token" {
  description = "Confluence API token (set via TF_VAR_confluence_token or -var)"
  type        = string
  sensitive   = true
}

variable "confluence_email" {
  default = "Hongbo.Zhou@nesa.nsw.edu.au"
}

variable "confluence_host" {
  default = "https://educationstandards.atlassian.net"
}

variable "blog_url" {
  default = "https://zackblog.work/"
}

variable "opensearch_collection_arn" {
  description = "ARN of the pre-created OpenSearch Serverless collection"
  default     = "arn:aws:aoss:ap-southeast-2:615299759525:collection/0s43wsj0nu6nsj4bdlxf"
}
