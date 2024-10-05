provider "aws" {
  region = var.aws_region
}

module "security_groups" {
  source = "../../modules/security_groups"
  vpc_id = var.vpc_id
  sg_prefix = "staging"  # Add unique prefix for staging
}

module "iam" {
  source = "../../modules/iam"
  role_prefix = "staging"  # Add unique prefix for staging
}

module "task_definition" {
  source             = "../../modules/task_definition"
  family             = var.task_family
  container_image    = var.container_image
  container_name     = var.container_name
  cpu                = var.cpu
  memory             = var.memory
  execution_role_arn = module.iam.execution_role_arn
  task_role_arn      = module.iam.task_role_arn
}

module "alb" {
  source            = "../../modules/alb"
  name              = var.alb_name
  internal          = var.alb_internal
  security_groups   = [module.security_groups.alb_sg]
  subnets           = var.subnets
  vpc_id            = var.vpc_id
  target_group_name = var.target_group_name
  target_group_port = var.target_group_port
  listener_port     = var.listener_port
}

module "ecs_service" {
  source              = "../../modules/ecs_service"
  service_name        = var.service_name
  cluster_arn         = module.ecs_cluster.ecs_cluster_arn
  task_definition_arn = module.task_definition.task_definition_arn
  subnets             = var.subnets
  security_groups     = [module.security_groups.ecs_sg]
  desired_count       = var.desired_count
  target_group_arn    = module.alb.target_group_arn
  container_name      = var.container_name
  container_port      = var.container_port
  dependency          = module.alb.listener_arn
}

module "ecs_cluster" {
  source = "../../modules/ecs_cluster"
  name   = var.ecs_cluster_name
}
