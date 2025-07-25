output "s3_bucket_id" {
  description = "The ID of the S3 bucket for uploads."
  value       = module.s3.bucket_id
}

output "dynamodb_results_table_name" {
  description = "The name of the DynamoDB table for results."
  value       = module.dynamodb.results_table_name
}

output "email_notification_queue_url" {
  description = "The URL of the SQS email notification queue."
  value       = module.sqs.email_notification_queue_url
}

output "sms_notification_queue_url" {
  description = "The URL of the SQS SMS notification queue."
  value       = module.sqs.sms_notification_queue_url
}