provider "aws" {
  region = var.aws_region
}

terraform {
  backend "s3" {
    bucket  = "zz-asb-k8s-velero-backup-bucket" # Hardcoded here
    key     = "terraform/stage/ecs.tfstate"     # Hardcoded here
    region  = "ap-southeast-2"                  # Hardcoded here
    encrypt = true
  }
}
