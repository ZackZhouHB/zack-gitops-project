terraform {
  backend "s3" {
    bucket  = "zz-asb-k8s-velero-backup-bucket"                   # Replace with S3 bucket name
    key     = "eks-module-env/stage/terraform/module/eks.tfstate" # Path to the state file in the bucket
    region  = "ap-southeast-2"                                    # Replace with desired AWS region
    encrypt = true
  }
}
