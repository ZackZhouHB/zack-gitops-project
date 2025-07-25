output "validation_lambda_role_arn" {
  description = "The ARN of the IAM role for the validation Lambda."
  value       = aws_iam_role.validation.arn
}

output "parser_lambda_role_arn" {
  description = "The ARN of the IAM role for the parser Lambda."
  value       = aws_iam_role.parser.arn
}

output "batch_processor_lambda_role_arn" {
  description = "The ARN of the IAM role for the batch processor Lambda."
  value       = aws_iam_role.batch_processor.arn
}

output "email_notifier_lambda_role_arn" {
  description = "The ARN of the IAM role for the email notifier Lambda."
  value       = aws_iam_role.email_notifier.arn
}

output "sms_notifier_lambda_role_arn" {
  description = "The ARN of the IAM role for the SMS notifier Lambda."
  value       = aws_iam_role.sms_notifier.arn
}

output "step_function_role_arn" {
  description = "The ARN of the IAM role for the Step Functions State Machine."
  value       = aws_iam_role.step_function.arn
}