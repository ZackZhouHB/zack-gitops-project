locals {
  name = "${var.project_name}-${var.environment}"
}

# VPC
module "vpc" {
  source = "./modules/vpc"

  name               = local.name
  vpc_cidr           = var.vpc_cidr
  availability_zones = var.availability_zones
}

# EKS
module "eks" {
  source = "./modules/eks"

  name                = local.name
  cluster_version     = var.eks_cluster_version
  vpc_id              = module.vpc.vpc_id
  private_subnet_ids  = module.vpc.private_subnet_ids
  node_instance_types = var.eks_node_instance_types
  node_desired_size   = var.eks_node_desired_size
  node_min_size       = var.eks_node_min_size
  node_max_size       = var.eks_node_max_size
}

# ECR
module "ecr" {
  source = "./modules/ecr"

  name = local.name
}

# S3
module "s3" {
  source = "./modules/s3"

  name = local.name
}

# SQS
module "sqs" {
  source = "./modules/sqs"

  name = local.name
}

# DynamoDB
module "dynamodb" {
  source = "./modules/dynamodb"

  name = local.name
}

# OpenSearch Serverless
module "opensearch" {
  source = "./modules/opensearch"

  name            = local.name
  collection_name = var.opensearch_collection_name
  vpc_id          = module.vpc.vpc_id
  subnet_ids      = module.vpc.private_subnet_ids
}

# Cognito
module "cognito" {
  source = "./modules/cognito"

  name = local.name
}
