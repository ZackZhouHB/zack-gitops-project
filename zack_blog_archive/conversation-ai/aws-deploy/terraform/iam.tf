# =============================================================================
# IAM Roles & Policies
# =============================================================================

# -----------------------------------------------------------------------------
# 1. ECS Task Execution Role (pulling images, logging, secrets)
# -----------------------------------------------------------------------------
resource "aws_iam_role" "ecs_task_execution" {
  name = "${var.project_name}-ecs-execution"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# -----------------------------------------------------------------------------
# 2. ECS Task Role (backend service → AWS APIs)
# -----------------------------------------------------------------------------
resource "aws_iam_role" "ecs_task" {
  name = "${var.project_name}-ecs-task"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "ecs_task_bedrock" {
  name = "bedrock-access"
  role = aws_iam_role.ecs_task.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:Retrieve",
          "bedrock:RetrieveAndGenerate"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem"
        ]
        Resource = [
          aws_dynamodb_table.checklists.arn,
          aws_dynamodb_table.escalations.arn
        ]
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# 3. Bedrock Knowledge Base Role (S3, OpenSearch, Bedrock embedding)
# -----------------------------------------------------------------------------
resource "aws_iam_role" "bedrock_kb" {
  name = "${var.project_name}-bedrock-kb"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "bedrock.amazonaws.com" }
      Condition = {
        StringEquals = {
          "aws:SourceAccount" = data.aws_caller_identity.current.account_id
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "bedrock_kb" {
  name = "kb-access"
  role = aws_iam_role.bedrock_kb.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:ListBucket"]
        Resource = [
          aws_s3_bucket.kb_documents.arn,
          "${aws_s3_bucket.kb_documents.arn}/*"
        ]
      },
      {
        Effect   = "Allow"
        Action   = ["bedrock:InvokeModel"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["aoss:APIAccessAll"]
        Resource = [var.opensearch_collection_arn]
      },
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = [aws_secretsmanager_secret.confluence_token.arn]
      },
      {
        Effect   = "Allow"
        Action   = ["kms:Decrypt"]
        Resource = [aws_kms_key.secrets.arn]
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# 4. Lambda Role (S3 → KB sync trigger)
# -----------------------------------------------------------------------------
resource "aws_iam_role" "lambda_kb_sync" {
  name = "${var.project_name}-lambda-kb-sync"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_kb_sync.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_bedrock" {
  name = "bedrock-kb-sync"
  role = aws_iam_role.lambda_kb_sync.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["bedrock:StartIngestionJob"]
      Resource = "*"
    }]
  })
}
