module "eks" {
  source = "terraform-aws-modules/eks/aws"
  version = "~> 19.0"

  cluster_name    = local.cluster_name
  cluster_version = "1.30"

  vpc_id                         = module.vpc.vpc_id
  subnet_ids                     = module.vpc.private_subnets
  cluster_endpoint_public_access = true

  # Enable IRSA (IAM Roles for Service Accounts)
  enable_irsa = true

  # Essential addons for cluster functionality
  cluster_addons = {
    coredns = {
      most_recent = true
    }
    kube-proxy = {
      most_recent = true
    }
    vpc-cni = {
      most_recent = true
    }
    aws-ebs-csi-driver = {
      most_recent                 = true
      service_account_role_arn    = aws_iam_role.ebs_csi_role.arn
    }
    aws-efs-csi-driver = {
      most_recent              = true
      service_account_role_arn = aws_iam_role.efs_csi_role.arn
    }
  }

  # EKS Managed Node Groups
  eks_managed_node_groups = {
    main = {
      name = "main-node-group"
      
      instance_types = var.node_group_instance_types
      capacity_type  = "SPOT"
      
      min_size     = var.node_group_min_size
      max_size     = var.node_group_max_size
      desired_size = var.node_group_desired_size

      # Explicit subnet configuration for HA
      subnet_ids = module.vpc.private_subnets

      # Launch template configuration
      use_custom_launch_template = false

      disk_size = 50  # Increased for t3.large
      ami_type  = "AL2_x86_64"

      # Force replacement on instance type change
      force_update_version = true

      # Additional IAM policies for EBS CSI driver and Bedrock access
      iam_role_additional_policies = {
        AmazonEBSCSIDriverPolicy = "arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy"
        EKSNodeBedrockAccess     = aws_iam_policy.eks_node_bedrock_access.arn
      }

      # Kubernetes labels
      labels = {
        Environment = "development"
        NodeGroup   = "main"
      }

      # Resource constraints for t3.large
      taints = []

      # Prevent unnecessary replacements
      update_config = {
        max_unavailable_percentage = 33
      }

      tags = local.common_tags
    }
  }

  tags = local.common_tags
}
