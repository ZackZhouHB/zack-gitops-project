resource "aws_s3_bucket" "kb_documents" {
  bucket        = "${var.project_name}-kb-documents-${data.aws_caller_identity.current.account_id}"
  force_destroy = true
}

resource "aws_s3_bucket_versioning" "kb_documents" {
  bucket = aws_s3_bucket.kb_documents.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_notification" "kb_sync" {
  bucket = aws_s3_bucket.kb_documents.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.kb_sync_trigger.arn
    events              = ["s3:ObjectCreated:*", "s3:ObjectRemoved:*"]
    filter_prefix       = "documents/"
  }

  depends_on = [aws_lambda_permission.s3_invoke]
}
