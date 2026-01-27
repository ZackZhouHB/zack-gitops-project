# VPC
output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = module.vpc.private_subnet_ids
}

# EKS
output "eks_cluster_name" {
  description = "EKS cluster name"
  value       = module.eks.cluster_name
}

output "eks_cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = module.eks.cluster_endpoint
}

output "eks_kubeconfig_command" {
  description = "Command to update kubeconfig"
  value       = "aws eks update-kubeconfig --region ${var.aws_region} --name ${module.eks.cluster_name}"
}

# ECR
output "ecr_backend_url" {
  description = "ECR backend repository URL"
  value       = module.ecr.backend_repository_url
}

output "ecr_worker_url" {
  description = "ECR worker repository URL"
  value       = module.ecr.worker_repository_url
}

# OpenSearch
output "opensearch_endpoint" {
  description = "OpenSearch Serverless endpoint"
  value       = module.opensearch.collection_endpoint
}

# S3
output "documents_bucket" {
  description = "S3 bucket for documents"
  value       = module.s3.documents_bucket_name
}

output "frontend_bucket" {
  description = "S3 bucket for frontend"
  value       = module.s3.frontend_bucket_name
}

# SQS
output "ingestion_queue_url" {
  description = "SQS ingestion queue URL"
  value       = module.sqs.queue_url
}
