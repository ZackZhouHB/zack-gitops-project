output "results_table_name" {
  description = "The name of the DynamoDB results table."
  value       = aws_dynamodb_table.results.name
}

output "results_table_arn" {
  description = "The ARN of the DynamoDB results table."
  value       = aws_dynamodb_table.results.arn
}
