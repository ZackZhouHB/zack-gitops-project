# S3 bucket for Lambda deployment packages
resource "aws_s3_object" "lambda_package" {
  bucket = var.deployment_packages_bucket_id
  key    = "${var.function_name}.zip"
  source = "${var.dist_path}/${var.function_name}.zip"
  etag   = filemd5("${var.dist_path}/${var.function_name}.zip")
}

resource "aws_lambda_function" "this" {
  function_name = var.function_name
  role          = var.role_arn
  handler       = var.handler
  runtime       = var.runtime
  timeout       = var.timeout
  memory_size   = var.memory_size

  s3_bucket         = aws_s3_object.lambda_package.bucket
  s3_key            = aws_s3_object.lambda_package.key
  source_code_hash  = filebase64sha256("${var.dist_path}/${var.function_name}.zip")

  environment {
    variables = var.environment_variables
  }
}