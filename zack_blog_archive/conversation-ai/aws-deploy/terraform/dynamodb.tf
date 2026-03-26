resource "aws_dynamodb_table" "checklists" {
  name         = "${var.project_name}-checklists"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "checklist_id"

  attribute {
    name = "checklist_id"
    type = "S"
  }

  tags = {
    Project = var.project_name
  }
}

resource "aws_dynamodb_table" "escalations" {
  name         = "${var.project_name}-escalations"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "escalation_id"

  attribute {
    name = "escalation_id"
    type = "S"
  }

  tags = {
    Project = var.project_name
  }
}
