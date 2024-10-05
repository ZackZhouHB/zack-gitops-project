terraform {
  backend "s3" {
    bucket = "zz-asb-k8s-velero-backup-bucket"
    key    = "prod/terraform/module/prod/ecs.tfstate"
    region = "ap-southeast-2"
  }
}
