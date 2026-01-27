variable "name" {}
variable "collection_name" {}
variable "vpc_id" {}
variable "subnet_ids" {}

# Security policy - allow access from VPC
resource "aws_opensearchserverless_security_policy" "encryption" {
  name = "${var.name}-encryption"
  type = "encryption"

  policy = jsonencode({
    Rules = [{
      ResourceType = "collection"
      Resource     = ["collection/${var.collection_name}"]
    }]
    AWSOwnedKey = true
  })
}

resource "aws_opensearchserverless_security_policy" "network" {
  name = "${var.name}-network"
  type = "network"

  policy = jsonencode([{
    Rules = [{
      ResourceType = "collection"
      Resource     = ["collection/${var.collection_name}"]
    }]
    AllowFromPublic = true # Change to false + VPC endpoint for production
  }])
}

# Data access policy
data "aws_caller_identity" "current" {}

resource "aws_opensearchserverless_access_policy" "data" {
  name = "${var.name}-data-access"
  type = "data"

  policy = jsonencode([{
    Rules = [
      {
        ResourceType = "collection"
        Resource     = ["collection/${var.collection_name}"]
        Permission   = ["aoss:CreateCollectionItems", "aoss:DeleteCollectionItems", "aoss:UpdateCollectionItems", "aoss:DescribeCollectionItems"]
      },
      {
        ResourceType = "index"
        Resource     = ["index/${var.collection_name}/*"]
        Permission   = ["aoss:CreateIndex", "aoss:DeleteIndex", "aoss:UpdateIndex", "aoss:DescribeIndex", "aoss:ReadDocument", "aoss:WriteDocument"]
      }
    ]
    Principal = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"]
  }])
}

# Collection
resource "aws_opensearchserverless_collection" "main" {
  name = var.collection_name
  type = "VECTORSEARCH"

  depends_on = [
    aws_opensearchserverless_security_policy.encryption,
    aws_opensearchserverless_security_policy.network,
    aws_opensearchserverless_access_policy.data,
  ]
}

output "collection_endpoint" {
  value = aws_opensearchserverless_collection.main.collection_endpoint
}

output "collection_arn" {
  value = aws_opensearchserverless_collection.main.arn
}

output "collection_id" {
  value = aws_opensearchserverless_collection.main.id
}
