terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.11"
    }
    kubectl = {
      source  = "gavinbunney/kubectl"
      version = "~> 1.14"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.1"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.1"
    }
  }
}

data "aws_caller_identity" "current" {}

provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile
}

# Use existing EKS cluster
data "aws_eks_cluster" "existing" {
  name = "eks-rag-weaviate"  # Use existing cluster
}

data "aws_eks_cluster_auth" "existing" {
  name = "eks-rag-weaviate"
}

provider "kubernetes" {
  host                   = data.aws_eks_cluster.existing.endpoint
  cluster_ca_certificate = base64decode(data.aws_eks_cluster.existing.certificate_authority[0].data)
  token                  = data.aws_eks_cluster_auth.existing.token
}

provider "helm" {
  kubernetes {
    host                   = data.aws_eks_cluster.existing.endpoint
    cluster_ca_certificate = base64decode(data.aws_eks_cluster.existing.certificate_authority[0].data)
    token                  = data.aws_eks_cluster_auth.existing.token
  }
}

locals {
  cluster_name = "eks-rag-weaviate"  # Use existing cluster name
  common_tags = {
    Environment = "development"
    Project     = "aws-eks-rag-langchain"
    ManagedBy   = "terraform"
  }
}
