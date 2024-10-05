provider "aws" {
  region = var.aws_region
}
# Security Groups module
module "security_groups" {
  source = "./modules/security_groups"
  vpc_id = var.vpc_id
}

# IAM Roles module
module "iam" {
  source = "./modules/iam"
}

# Task Definition module
module "task_definition" {
  source = "./modules/task_definition"

  family             = var.task_family
  container_image    = var.container_image
  cpu                = var.cpu
  memory             = var.memory
  execution_role_arn = module.iam.execution_role_arn
  task_role_arn      = module.iam.task_role_arn
}

# ALB module
module "alb" {
  source            = "./modules/alb"
  name              = "app-lb"
  internal          = false
  security_groups   = [module.security_groups.alb_sg]
  subnets           = var.subnets
  vpc_id            = var.vpc_id
  target_group_name = "app-target-group"
  target_group_port = 80
  listener_port     = 80
}

# ECS Service module
module "ecs_service" {
  source              = "./modules/ecs_service"
  service_name        = "app-service"
  cluster_arn         = module.ecs_cluster.ecs_cluster_arn
  task_definition_arn = module.task_definition.task_definition_arn
  subnets             = var.subnets
  security_groups     = [module.security_groups.ecs_sg]
  desired_count       = var.desired_count
  target_group_arn    = module.alb.target_group_arn
  container_name      = "app"
  container_port      = 80
  dependency          = module.alb.listener_arn
}

# ECS Cluster module
module "ecs_cluster" {
  source = "./modules/ecs_cluster"
  name   = var.ecs_cluster_name
}
