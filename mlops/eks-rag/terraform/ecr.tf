# ECR repository for bedrock-gateway
resource "aws_ecr_repository" "bedrock_gateway" {
  name                 = "bedrock-gateway"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = false
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = local.common_tags
}
