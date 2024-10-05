aws_region       = "ap-southeast-2"
ecs_cluster_name = "module-prod-ecs-cluster"
subnets          = ["subnet-080880543de1ce69a", "subnet-073a3529e120d46db"]
vpc_id           = "vpc-0de6953a6686478e8"
desired_count    = 2
s3_bucket        = "zz-asb-k8s-velero-backup-bucket"
s3_key           = "terraform/module/prod/ecs.tfstate"
task_family      = "my-app-task-family"
container_image  = "zackz001/jenkins:latest"
cpu              = 256 # Changed to number
memory           = 512 # Changed to number


environment      = "blue" # Set to "green" to deploy green version