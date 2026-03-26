###############################################################################
# Lambda – KB Sync Trigger
# Invoked by S3 events to start a Bedrock KB data-source ingestion job.
###############################################################################

# --- Package the Lambda function ---------------------------------------------

data "archive_file" "kb_sync" {
  type        = "zip"
  source_file = "${path.module}/../lambda/kb_sync_trigger.py"
  output_path = "${path.module}/../lambda/kb_sync_trigger.zip"
}

# --- Lambda function ---------------------------------------------------------

resource "aws_lambda_function" "kb_sync_trigger" {
  function_name    = "${var.project_name}-kb-sync-trigger"
  runtime          = "python3.12"
  handler          = "kb_sync_trigger.handler"
  role             = aws_iam_role.lambda_kb_sync.arn
  filename         = data.archive_file.kb_sync.output_path
  source_code_hash = data.archive_file.kb_sync.output_base64sha256
  timeout          = 30

  environment {
    variables = {
      KNOWLEDGE_BASE_ID = aws_bedrockagent_knowledge_base.main.id
      DATA_SOURCE_ID    = aws_bedrockagent_data_source.s3.data_source_id
    }
  }
}

# --- Allow S3 to invoke the Lambda ------------------------------------------

resource "aws_lambda_permission" "s3_invoke" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.kb_sync_trigger.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.kb_documents.arn
}
