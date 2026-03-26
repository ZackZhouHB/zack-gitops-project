output "ecr_backend_url" {
  value = aws_ecr_repository.backend.repository_url
}

output "ecr_frontend_url" {
  value = aws_ecr_repository.frontend.repository_url
}

output "s3_bucket_name" {
  value = aws_s3_bucket.kb_documents.id
}

output "efs_id" {
  value = aws_efs_file_system.chat_history.id
}

output "dynamodb_checklists_table" {
  value = aws_dynamodb_table.checklists.name
}

output "dynamodb_escalations_table" {
  value = aws_dynamodb_table.escalations.name
}

output "alb_dns_name" {
  value       = aws_lb.main.dns_name
  description = "ALB public URL"
}

output "knowledge_base_id" {
  value = aws_bedrockagent_knowledge_base.main.id
}
