# terraform.tfvars
subnets                     = ["subnet-080880543de1ce69a", "subnet-073a3529e120d46db"] # Replace with your subnet IDs
node_group_instance_type    = "t3a.small"
desired_capacity            = 2
max_capacity                = 3
min_capacity                = 1
region                      = "ap-southeast-2"                  # Your desired AWS region
cluster_name                = "module-eks-cluster"               # Name of your EKS cluster
instance_type               = "t3a.small"                        # Node type
disk_size                   = 15                                   # Disk size in GB
s3_bucket                   = "zz-asb-k8s-velero-backup-bucket"  # S3 bucket for Terraform state
environment                 = "dev"                               # Environment name (e.g., dev, prod)
role_prefix                 = "dev"                               # Prefix for roles (e.g., dev, prod)
vpc_id                      = "vpc-0de6953a6686478e8"            # Your VPC ID
