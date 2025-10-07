# IAM role for RAG backend pods
resource "aws_iam_role" "rag_backend_role" {
  name = "${local.cluster_name}-rag-backend-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = module.eks.oidc_provider_arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "${replace(module.eks.cluster_oidc_issuer_url, "https://", "")}:sub": "system:serviceaccount:rag-system:rag-backend"
            "${replace(module.eks.cluster_oidc_issuer_url, "https://", "")}:aud": "sts.amazonaws.com"
          }
        }
      }
    ]
  })

  tags = local.common_tags
}

# IAM policy for RAG backend
resource "aws_iam_policy" "rag_backend_policy" {
  name        = "${local.cluster_name}-rag-backend-policy"
  description = "IAM policy for RAG backend to access AWS services"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [

      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = [
          "arn:aws:bedrock:*::foundation-model/*",
          "arn:aws:bedrock:${var.aws_region}:*:inference-profile/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.documents.arn,
          "${aws_s3_bucket.documents.arn}/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "rag_backend_policy_attachment" {
  role       = aws_iam_role.rag_backend_role.name
  policy_arn = aws_iam_policy.rag_backend_policy.arn
}

# Service account for RAG backend
resource "kubernetes_service_account" "rag_backend" {
  depends_on = [module.eks]
  
  metadata {
    name      = "rag-backend"
    namespace = "rag-system"
    annotations = {
      "eks.amazonaws.com/role-arn" = aws_iam_role.rag_backend_role.arn
    }
  }
}

# IAM role for EBS CSI driver
resource "aws_iam_role" "ebs_csi_role" {
  name = "${local.cluster_name}-ebs-csi-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = module.eks.oidc_provider_arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "${replace(module.eks.cluster_oidc_issuer_url, "https://", "")}:sub": "system:serviceaccount:kube-system:ebs-csi-controller-sa"
            "${replace(module.eks.cluster_oidc_issuer_url, "https://", "")}:aud": "sts.amazonaws.com"
          }
        }
      }
    ]
  })

  tags = local.common_tags
}

# Attach AWS managed policy for EBS CSI driver
resource "aws_iam_role_policy_attachment" "ebs_csi_policy" {
  role       = aws_iam_role.ebs_csi_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy"
}

# Bedrock policy for EKS node group
resource "aws_iam_policy" "eks_node_bedrock_access" {
  name        = "EKSNodeBedrockAccess"
  description = "IAM policy for EKS nodes to access Bedrock services"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:ListInferenceProfiles",
          "bedrock:ListFoundationModels",
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = "*"
      }
    ]
  })

  tags = local.common_tags
}

# Create namespace
resource "kubernetes_namespace" "rag_system" {
  depends_on = [module.eks]
  
  metadata {
    name = "rag-system"
    labels = {
      name = "rag-system"
    }
  }
}
