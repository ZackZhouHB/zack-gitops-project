# IAM role for the Step Functions State Machine
resource "aws_iam_role" "step_function" {
  name = "${var.project_name}-step-function-role-${var.env}"

  assume_role_policy = jsonencode({
    Version   = "2012-10-17",
    Statement = [
      {
        Effect    = "Allow",
        Principal = {
          Service = "states.${var.aws_region}.amazonaws.com"
        },
        Action    = "sts:AssumeRole"
      }
    ]
  })
}

# IAM policy for the Step Function to invoke Lambda functions
resource "aws_iam_policy" "step_function" {
  name   = "${var.project_name}-step-function-policy-${var.env}"
  policy = jsonencode({
    Version   = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = "lambda:InvokeFunction",
        Resource = "arn:aws:lambda:${var.aws_region}:${var.aws_account_id}:function:${var.project_name}-*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "step_function" {
  role       = aws_iam_role.step_function.name
  policy_arn = aws_iam_policy.step_function.arn
}

# --- IAM Roles for Lambda Functions ---

resource "aws_iam_role" "lambda_base" {
  name = "${var.project_name}-lambda-base-role-${var.env}"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17",
    Statement = [
      {
        Effect    = "Allow",
        Principal = {
          Service = "lambda.amazonaws.com"
        },
        Action    = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_policy" "lambda_logging" {
  name   = "${var.project_name}-lambda-logging-policy-${var.env}"
  policy = jsonencode({
    Version   = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream"
        ],
        Resource = "arn:aws:logs:${var.aws_region}:${var.aws_account_id}:log-group:/aws/lambda/*"
      },
      {
        Effect   = "Allow",
        Action   = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Resource = "arn:aws:logs:${var.aws_region}:${var.aws_account_id}:log-group:/aws/lambda/*:*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_logging" {
  role       = aws_iam_role.lambda_base.name
  policy_arn = aws_iam_policy.lambda_logging.arn
}

# --- Validation Lambda ---
resource "aws_iam_role" "validation" {
  name = "${var.project_name}-validation-role-${var.env}"
  assume_role_policy = aws_iam_role.lambda_base.assume_role_policy
}

resource "aws_iam_policy" "validation" {
  name   = "${var.project_name}-validation-policy-${var.env}"
  policy = jsonencode({
    Version   = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = "states:StartExecution",
        Resource = "*" # Scoped down in a real project
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "validation" {
  role       = aws_iam_role.validation.name
  policy_arn = aws_iam_policy.validation.arn
}

resource "aws_iam_role_policy_attachment" "validation_logging" {
  role       = aws_iam_role.validation.name
  policy_arn = aws_iam_policy.lambda_logging.arn
}

# --- Parser Lambda ---
resource "aws_iam_role" "parser" {
  name = "${var.project_name}-parser-role-${var.env}"
  assume_role_policy = aws_iam_role.lambda_base.assume_role_policy
}

resource "aws_iam_policy" "parser" {
  name   = "${var.project_name}-parser-policy-${var.env}"
  policy = jsonencode({
    Version   = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = "s3:GetObject",
        Resource = "${var.results_bucket_arn}/*"
      },
      {
        Effect   = "Allow",
        Action   = [
          "kms:Decrypt",
          "kms:DescribeKey"
        ],
        Resource = var.kms_key_arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "parser" {
  role       = aws_iam_role.parser.name
  policy_arn = aws_iam_policy.parser.arn
}

resource "aws_iam_role_policy_attachment" "parser_logging" {
  role       = aws_iam_role.parser.name
  policy_arn = aws_iam_policy.lambda_logging.arn
}

# --- Batch Processor Lambda ---
resource "aws_iam_role" "batch_processor" {
  name = "${var.project_name}-batch-processor-role-${var.env}"
  assume_role_policy = aws_iam_role.lambda_base.assume_role_policy
}

resource "aws_iam_policy" "batch_processor" {
  name   = "${var.project_name}-batch-processor-policy-${var.env}"
  policy = jsonencode({
    Version   = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = [
          "dynamodb:BatchWriteItem",
          "dynamodb:PutItem"
        ],
        Resource = var.results_table_arn
      },
      {
        Effect   = "Allow",
        Action   = [
          "sqs:SendMessageBatch",
          "sqs:SendMessage"
        ],
        Resource = [
          var.sms_notification_queue_arn,
          var.email_notification_queue_arn
        ]
      },
      {
        Effect   = "Allow",
        Action   = [
          "kms:Decrypt",
          "kms:DescribeKey",
          "kms:GenerateDataKey",
          "kms:Encrypt"
        ],
        Resource = var.kms_key_arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "batch_processor" {
  role       = aws_iam_role.batch_processor.name
  policy_arn = aws_iam_policy.batch_processor.arn
}

resource "aws_iam_role_policy_attachment" "batch_processor_logging" {
  role       = aws_iam_role.batch_processor.name
  policy_arn = aws_iam_policy.lambda_logging.arn
}

# --- Email Notifier Lambda ---
resource "aws_iam_role" "email_notifier" {
  name = "${var.project_name}-email-notifier-role-${var.env}"
  assume_role_policy = aws_iam_role.lambda_base.assume_role_policy
}

resource "aws_iam_policy" "email_notifier" {
  name   = "${var.project_name}-email-notifier-policy-${var.env}"
  policy = jsonencode({
    Version   = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = "ses:SendEmail",
        Resource = "*"
      },
      {
        Effect   = "Allow",
        Action   = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ],
        Resource = var.email_notification_queue_arn
      },
      {
        Effect   = "Allow",
        Action   = [
          "dynamodb:UpdateItem",
          "dynamodb:GetItem"
        ],
        Resource = var.results_table_arn
      },
      {
        Effect   = "Allow",
        Action   = [
          "kms:Decrypt",
          "kms:GenerateDataKey",
          "kms:DescribeKey"
        ],
        Resource = var.kms_key_arn
      }
    ]
  })
}

# --- SMS Notifier Lambda ---
resource "aws_iam_role" "sms_notifier" {
  name = "${var.project_name}-sms-notifier-role-${var.env}"
  assume_role_policy = aws_iam_role.lambda_base.assume_role_policy
}

resource "aws_iam_policy" "sms_notifier" {
  name   = "${var.project_name}-sms-notifier-policy-${var.env}"
  policy = jsonencode({
    Version   = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = "sns:Publish",
        Resource = "*"
      },
      {
        Effect   = "Allow",
        Action   = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ],
        Resource = var.sms_notification_queue_arn
      },
      {
        Effect   = "Allow",
        Action   = [
          "dynamodb:UpdateItem",
          "dynamodb:GetItem"
        ],
        Resource = var.results_table_arn
      },
      {
        Effect   = "Allow",
        Action   = [
          "kms:Decrypt",
          "kms:GenerateDataKey",
          "kms:DescribeKey"
        ],
        Resource = var.kms_key_arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "sms_notifier" {
  role       = aws_iam_role.sms_notifier.name
  policy_arn = aws_iam_policy.sms_notifier.arn
}

resource "aws_iam_role_policy_attachment" "sms_notifier_logging" {
  role       = aws_iam_role.sms_notifier.name
  policy_arn = aws_iam_policy.lambda_logging.arn
}

resource "aws_iam_role_policy_attachment" "email_notifier" {
  role       = aws_iam_role.email_notifier.name
  policy_arn = aws_iam_policy.email_notifier.arn
}

resource "aws_iam_role_policy_attachment" "email_notifier_logging" {
  role       = aws_iam_role.email_notifier.name
  policy_arn = aws_iam_policy.lambda_logging.arn
}