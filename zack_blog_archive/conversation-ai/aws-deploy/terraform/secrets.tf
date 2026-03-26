resource "aws_kms_key" "secrets" {
  description             = "${var.project_name} secrets encryption key"
  deletion_window_in_days = 7
  enable_key_rotation     = true
}

resource "aws_kms_alias" "secrets" {
  name          = "alias/${var.project_name}-secrets"
  target_key_id = aws_kms_key.secrets.key_id
}

resource "aws_secretsmanager_secret" "confluence_token" {
  name       = "${var.project_name}/confluence-credentials"
  kms_key_id = aws_kms_key.secrets.arn
}

resource "aws_secretsmanager_secret_version" "confluence_token" {
  secret_id = aws_secretsmanager_secret.confluence_token.id
  secret_string = jsonencode({
    confluenceUrl    = var.confluence_host
    username         = var.confluence_email
    password         = var.confluence_token
  })
}
