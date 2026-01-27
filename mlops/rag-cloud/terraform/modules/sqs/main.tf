variable "name" {}

resource "aws_sqs_queue" "dlq" {
  name                      = "${var.name}-ingestion-dlq"
  message_retention_seconds = 1209600 # 14 days
}

resource "aws_sqs_queue" "ingestion" {
  name                       = "${var.name}-ingestion"
  visibility_timeout_seconds = 300 # 5 min for processing
  message_retention_seconds  = 86400 # 1 day

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 3
  })
}

resource "aws_sqs_queue_policy" "ingestion" {
  queue_url = aws_sqs_queue.ingestion.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "s3.amazonaws.com" }
      Action    = "sqs:SendMessage"
      Resource  = aws_sqs_queue.ingestion.arn
    }]
  })
}

output "queue_url" {
  value = aws_sqs_queue.ingestion.url
}

output "queue_arn" {
  value = aws_sqs_queue.ingestion.arn
}

output "dlq_url" {
  value = aws_sqs_queue.dlq.url
}

output "dlq_arn" {
  value = aws_sqs_queue.dlq.arn
}
