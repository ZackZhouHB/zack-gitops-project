variable "name" {}

resource "aws_cognito_user_pool" "main" {
  name = var.name

  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]

  password_policy {
    minimum_length    = 8
    require_lowercase = true
    require_numbers   = true
    require_symbols   = false
    require_uppercase = true
  }

  schema {
    name                = "email"
    attribute_data_type = "String"
    required            = true
    mutable             = true
  }

  admin_create_user_config {
    allow_admin_create_user_only = false
  }
}

resource "aws_cognito_user_pool_client" "main" {
  name         = "${var.name}-client"
  user_pool_id = aws_cognito_user_pool.main.id

  generate_secret     = false
  explicit_auth_flows = ["ALLOW_USER_PASSWORD_AUTH", "ALLOW_REFRESH_TOKEN_AUTH", "ALLOW_USER_SRP_AUTH"]

  access_token_validity  = 1  # hours
  id_token_validity      = 1
  refresh_token_validity = 30 # days
}

# Create default groups
resource "aws_cognito_user_group" "admin" {
  name         = "admin"
  user_pool_id = aws_cognito_user_pool.main.id
  description  = "Admin users"
}

resource "aws_cognito_user_group" "users" {
  name         = "users"
  user_pool_id = aws_cognito_user_pool.main.id
  description  = "Regular users"
}

output "user_pool_id" {
  value = aws_cognito_user_pool.main.id
}

output "user_pool_arn" {
  value = aws_cognito_user_pool.main.arn
}

output "client_id" {
  value = aws_cognito_user_pool_client.main.id
}

output "user_pool_endpoint" {
  value = aws_cognito_user_pool.main.endpoint
}
