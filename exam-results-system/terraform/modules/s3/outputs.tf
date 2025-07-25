output "bucket_id" {
  description = "The ID (name) of the S3 bucket."
  value       = aws_s3_bucket.main.id
}

output "bucket_arn" {
  description = "The ARN of the S3 bucket."
  value       = aws_s3_bucket.main.arn
}

output "deployment_packages_bucket_id" {
  description = "The ID (name) of the deployment packages S3 bucket."
  value       = aws_s3_bucket.deployment_packages.id
}

output "deployment_packages_bucket_arn" {
  description = "The ARN of the deployment packages S3 bucket."
  value       = aws_s3_bucket.deployment_packages.arn
}
