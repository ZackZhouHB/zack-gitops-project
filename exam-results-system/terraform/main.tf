provider "aws" {
  region = var.aws_region
}

locals {
  dist_path = abspath("${path.root}/../dist")
}

# S3 backend for storing Terraform state remotely
terraform {
  # backend "s3" {
  #   # Configure this with your state bucket details
  #   bucket = "my-terraform-state-bucket-hsc"
  #   key    = "hsc-results/terraform.tfstate"
  #   region = "ap-southeast-2"
  # }
}

# --- Shared Resources ---
resource "aws_kms_key" "main" {
  description             = "KMS key for HSC Results System (${var.env})"
  enable_key_rotation     = true
  deletion_window_in_days = 10
  tags = {
    Project = var.project_name
    Env     = var.env
  }
}

# --- SES Identity Verification ---
resource "aws_ses_email_identity" "sender" {
  email = var.sender_email
}

# --- SNS Phone Registration ---
resource "aws_sns_topic" "sms_verification" {
  name = "${var.project_name}-sms-verification-${var.env}"
}

# SNS phone registration for sandbox environment
resource "aws_sns_topic_subscription" "verified_phones" {
  count = length(var.verified_phone_numbers)
  
  topic_arn = aws_sns_topic.sms_verification.arn
  protocol  = "sms"
  endpoint  = var.verified_phone_numbers[count.index]
  
  depends_on = [aws_sns_topic.sms_verification]
}

# --- Modules ---
module "s3" {
  source = "./modules/s3"
  
  project_name = var.project_name
  env          = var.env
  kms_key_arn  = aws_kms_key.main.arn
}

module "dynamodb" {
  source = "./modules/dynamodb"
  
  project_name = var.project_name
  env          = var.env
  kms_key_arn  = aws_kms_key.main.arn
}

module "sqs" {
  source = "./modules/sqs"
  
  project_name = var.project_name
  env          = var.env
  kms_key_arn  = aws_kms_key.main.arn
}

module "iam" {
  source = "./modules/iam"

  project_name      = var.project_name
  env               = var.env
  aws_region        = var.aws_region
  aws_account_id    = data.aws_caller_identity.current.account_id
  kms_key_arn       = aws_kms_key.main.arn
  results_bucket_arn = module.s3.bucket_arn
  results_table_arn = module.dynamodb.results_table_arn
  email_notification_queue_arn = module.sqs.email_notification_queue_arn
  sms_notification_queue_arn   = module.sqs.sms_notification_queue_arn
}

# --- Lambda Functions ---

module "validation_lambda" {
  source                        = "./modules/lambda"
  function_name                 = "${var.project_name}-validation-${var.env}"
  role_arn                      = module.iam.validation_lambda_role_arn
  source_dir                    = "../src/validation"
  deployment_packages_bucket_id = module.s3.deployment_packages_bucket_id
  dist_path                     = local.dist_path
  environment_variables = {
    STATE_MACHINE_ARN = aws_sfn_state_machine.hsc_processing.arn
  }
}

module "parser_lambda" {
  source                        = "./modules/lambda"
  function_name                 = "${var.project_name}-parser-${var.env}"
  role_arn                      = module.iam.parser_lambda_role_arn
  source_dir                    = "../src/parser"
  deployment_packages_bucket_id = module.s3.deployment_packages_bucket_id
  dist_path                     = local.dist_path
  timeout                       = 300
  memory_size                   = 1024
}

module "batch_processor_lambda" {
  source                        = "./modules/lambda"
  function_name                 = "${var.project_name}-batch-processor-${var.env}"
  role_arn                      = module.iam.batch_processor_lambda_role_arn
  source_dir                    = "../src/batch_processor"
  deployment_packages_bucket_id = module.s3.deployment_packages_bucket_id
  dist_path                     = local.dist_path
  environment_variables = {
    RESULTS_TABLE_NAME     = module.dynamodb.results_table_name
    EMAIL_QUEUE_URL = module.sqs.email_notification_queue_url
    SMS_QUEUE_URL = module.sqs.sms_notification_queue_url
  }
}

module "email_notifier_lambda" {
  source                        = "./modules/lambda"
  function_name                 = "${var.project_name}-email-notifier-${var.env}"
  role_arn                      = module.iam.email_notifier_lambda_role_arn
  source_dir                    = "../src/email_notifier"
  deployment_packages_bucket_id = module.s3.deployment_packages_bucket_id
  dist_path                     = local.dist_path
  timeout                       = 25
  environment_variables = {
    SENDER_EMAIL       = var.sender_email
    RESULTS_TABLE_NAME = module.dynamodb.results_table_name
  }
}

module "sms_notifier_lambda" {
  source                        = "./modules/lambda"
  function_name                 = "${var.project_name}-sms-notifier-${var.env}"
  role_arn                      = module.iam.sms_notifier_lambda_role_arn
  source_dir                    = "../src/sms_notifier"
  deployment_packages_bucket_id = module.s3.deployment_packages_bucket_id
  dist_path                     = local.dist_path
  timeout                       = 25
  environment_variables = {
    RESULTS_TABLE_NAME = module.dynamodb.results_table_name
  }
}

# --- State Machine ---

resource "aws_sfn_state_machine" "hsc_processing" {
  name     = "${var.project_name}-processing-${var.env}"
  role_arn = module.iam.step_function_role_arn

  definition = templatefile("${path.module}/state_machine.json.tpl", {
    parser_lambda_arn          = module.parser_lambda.arn
    batch_processor_lambda_arn = module.batch_processor_lambda.arn
  })

  tags = {
    Project = var.project_name
    Env     = var.env
  }
}

# --- Triggers ---

resource "aws_s3_bucket_notification" "s3_upload_trigger" {
  bucket = module.s3.bucket_id

  lambda_function {
    lambda_function_arn = module.validation_lambda.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "uploads/ready-for-processing/"
  }

  depends_on = [aws_lambda_permission.allow_s3_to_call_validation]
}

resource "aws_lambda_permission" "allow_s3_to_call_validation" {
  statement_id  = "AllowS3ToCallValidationLambda"
  action        = "lambda:InvokeFunction"
  function_name = module.validation_lambda.name
  principal     = "s3.amazonaws.com"
  source_arn    = module.s3.bucket_arn
}

resource "aws_lambda_event_source_mapping" "email_notifier_trigger" {
  event_source_arn = module.sqs.email_notification_queue_arn
  function_name    = module.email_notifier_lambda.name
  batch_size       = 10
}

resource "aws_lambda_event_source_mapping" "sms_notifier_trigger" {
  event_source_arn = module.sqs.sms_notification_queue_arn
  function_name    = module.sms_notifier_lambda.name
  batch_size       = 10
}

data "aws_caller_identity" "current" {}
