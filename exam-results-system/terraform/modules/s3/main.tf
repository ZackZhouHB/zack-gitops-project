resource "aws_s3_bucket" "main" {
  bucket = "${var.project_name}-results-${var.env}"

  tags = {
    Project = var.project_name
    Env     = var.env
  }
}

# S3 bucket for Lambda deployment packages
resource "aws_s3_bucket" "deployment_packages" {
  bucket = "${var.project_name}-deployment-packages-${var.env}"

  tags = {
    Project = var.project_name
    Env     = var.env
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "main" {
  bucket = aws_s3_bucket.main.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = var.kms_key_arn
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "deployment_packages" {
  bucket = aws_s3_bucket.deployment_packages.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = var.kms_key_arn
    }
  }
}

resource "aws_s3_bucket_public_access_block" "main" {
  bucket = aws_s3_bucket.main.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "deployment_packages" {
  bucket = aws_s3_bucket.deployment_packages.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
