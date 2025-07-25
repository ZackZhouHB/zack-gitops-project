resource "aws_dynamodb_table" "results" {
  name         = "${var.project_name}-results-${var.env}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "student_id"

  attribute {
    name = "student_id"
    type = "S"
  }

  server_side_encryption {
    enabled     = true
    kms_key_arn = var.kms_key_arn
  }

  tags = {
    Project = var.project_name
    Env     = var.env
  }
}
