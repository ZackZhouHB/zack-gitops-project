terraform {
  backend "s3" {
    bucket = var.s3_bucket
    key    = var.s3_key
    region = var.aws_region
  }
}

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
  source             = "./modules/task_definition"
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
  health_check_path = "/"
}

# ECS Cluster module
module "ecs_cluster" {
  source = "./modules/ecs_cluster"
  name   = var.ecs_cluster_name
}

# Determine active target group ARN for blue-green deployment
locals {
  active_target_group_arn = var.environment == "blue" ? module.alb.blue_target_group_arn : module.alb.green_target_group_arn
}

# ECS Service module
# ECS Service module
module "ecs_service" {
  source                 = "./modules/ecs_service"
  service_name           = "app-service"
  cluster_arn            = module.ecs_cluster.ecs_cluster_arn
  task_definition_arn    = var.environment == "blue" ? module.task_definition.blue_task_definition_arn : module.task_definition.green_task_definition_arn
  subnets                = var.subnets
  security_groups        = [module.security_groups.ecs_sg]
  desired_count          = var.desired_count
  target_group_arn       = local.active_target_group_arn # Corrected to match module variable name
  container_name         = "app"
  container_port         = 80
  dependency             = module.alb.listener_arn
}
