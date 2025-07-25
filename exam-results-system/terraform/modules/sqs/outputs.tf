output "email_notification_queue_url" {
  description = "The URL of the SQS email notification queue."
  value       = aws_sqs_queue.email_notifications.id
}

output "email_notification_queue_arn" {
  description = "The ARN of the SQS email notification queue."
  value       = aws_sqs_queue.email_notifications.arn
}

output "sms_notification_queue_url" {
  description = "The URL of the SQS SMS notification queue."
  value       = aws_sqs_queue.sms_notifications.id
}

output "sms_notification_queue_arn" {
  description = "The ARN of the SQS SMS notification queue."
  value       = aws_sqs_queue.sms_notifications.arn
}