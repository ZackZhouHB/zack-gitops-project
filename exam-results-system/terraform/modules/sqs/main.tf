resource "aws_sqs_queue" "email_notifications" {
  name                        = "${var.project_name}-email-notifications-${var.env}.fifo"
  fifo_queue                  = true
  content_based_deduplication = true
  kms_master_key_id           = "alias/aws/sqs"
  kms_data_key_reuse_period_seconds = 300

  tags = {
    Project = var.project_name
    Env     = var.env
  }
}

resource "aws_sqs_queue" "sms_notifications" {
  name                        = "${var.project_name}-sms-notifications-${var.env}.fifo"
  fifo_queue                  = true
  content_based_deduplication = true
  kms_master_key_id           = "alias/aws/sqs"
  kms_data_key_reuse_period_seconds = 300

  tags = {
    Project = var.project_name
    Env     = var.env
  }
}