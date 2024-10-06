terraform {
  backend "s3" {
    bucket  = "zz-asb-k8s-velero-backup-bucket"            # Replace with your S3 bucket name
    key     = "eks/dev/terraform/module/stage/eks.tfstate" # Path to the state file in the bucket
    region  = "ap-southeast-2"                             # Replace with your desired AWS region
    encrypt = true
  }
}


