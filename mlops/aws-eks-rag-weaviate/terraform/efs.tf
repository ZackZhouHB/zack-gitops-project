resource "aws_efs_file_system" "chat_history" {
  creation_token = "${local.cluster_name}-shared-storage"
  
  performance_mode = "generalPurpose"
  throughput_mode  = "elastic"

  encrypted = true

  tags = merge(local.common_tags, {
    Name = "RAG Shared Storage EFS"
  })
}

resource "aws_efs_mount_target" "chat_history" {
  count = length(module.vpc.private_subnets)
  
  file_system_id  = aws_efs_file_system.chat_history.id
  subnet_id       = module.vpc.private_subnets[count.index]
  security_groups = [aws_security_group.efs.id]
}

resource "aws_security_group" "efs" {
  name_prefix = "${local.cluster_name}-efs-"
  vpc_id      = module.vpc.vpc_id

  ingress {
    description = "NFS"
    from_port   = 2049
    to_port     = 2049
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "EFS Security Group"
  })
}

# EFS CSI Driver IAM policy
resource "aws_iam_policy" "efs_csi_policy" {
  name        = "${local.cluster_name}-efs-csi-policy"
  description = "IAM policy for EFS CSI driver"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "elasticfilesystem:ClientMount",
          "elasticfilesystem:ClientWrite",
          "elasticfilesystem:ClientRootAccess",
          "elasticfilesystem:DescribeMountTargets",
          "elasticfilesystem:DescribeFileSystems"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role" "efs_csi_role" {
  name = "${local.cluster_name}-efs-csi-role"

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
            "${replace(module.eks.cluster_oidc_issuer_url, "https://", "")}:sub": "system:serviceaccount:kube-system:efs-csi-controller-sa"
            "${replace(module.eks.cluster_oidc_issuer_url, "https://", "")}:aud": "sts.amazonaws.com"
          }
        }
      }
    ]
  })

  tags = local.common_tags
}

# Attach custom EFS policy
resource "aws_iam_role_policy_attachment" "efs_csi_policy_attachment" {
  role       = aws_iam_role.efs_csi_role.name
  policy_arn = aws_iam_policy.efs_csi_policy.arn
}

# Attach AWS managed EFS CSI driver policy
resource "aws_iam_role_policy_attachment" "efs_csi_driver_policy" {
  role       = aws_iam_role.efs_csi_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEFSCSIDriverPolicy"
}

# Service account annotation for EFS CSI driver
resource "kubernetes_annotations" "efs_csi_controller_sa" {
  api_version = "v1"
  kind        = "ServiceAccount"
  
  metadata {
    name      = "efs-csi-controller-sa"
    namespace = "kube-system"
  }
  
  annotations = {
    "eks.amazonaws.com/role-arn" = aws_iam_role.efs_csi_role.arn
  }
  
  depends_on = [module.eks]
}
