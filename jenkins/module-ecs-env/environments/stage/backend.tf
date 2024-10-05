terraform {
  backend "s3" {
    bucket = "zz-asb-k8s-velero-backup-bucket"
    key    = "staging/ecs/terraform.tfstate"
    region = "ap-southeast-2"
  }
}
