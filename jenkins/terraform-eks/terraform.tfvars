# terraform.tfvars
subnet_ids    = ["subnet-080880543de1ce69a", "subnet-073a3529e120d46db"] # Replace with your subnet IDs
desired_size  = 1
max_size      = 3
min_size      = 1
aws_region    = "ap-southeast-2"                  # Your desired AWS region
cluster_name  = "module-eks-cluster"              # Name of your EKS cluster
instance_type = "t3a.small"                       # Node type
disk_size     = 15                                # Disk size in GB
s3_bucket     = "zz-asb-k8s-velero-backup-bucket" # S3 bucket for Terraform state
s3_key        = "eks/dev/terraform/module/stage/eks.tfstate"
environment   = "dev"                   # Environment name (e.g., dev, prod)
role_prefix   = "dev"                   # Prefix for roles (e.g., dev, prod)
vpc_id        = "vpc-0de6953a6686478e8" # Your VPC ID
