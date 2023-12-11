variable "region" {
  description = "AWS region"
  type        = string
  default     = "ap-southeast-2"
}

variable "clusterName" {
  description = "Name of the EKS cluster"
  type        = string
  default     = "zack-gitops-eks-prod"
}
