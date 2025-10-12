output "cluster_endpoint" {
  description = "Endpoint for EKS control plane"
  value       = data.aws_eks_cluster.existing.endpoint
}

output "cluster_name" {
  description = "Kubernetes Cluster Name"
  value       = data.aws_eks_cluster.existing.name
}

output "cluster_arn" {
  description = "The Amazon Resource Name (ARN) of the cluster"
  value       = data.aws_eks_cluster.existing.arn
}

# Configuration for kubectl
output "configure_kubectl" {
  description = "Configure kubectl: make sure you're logged in with the correct AWS profile and run the following command to update your kubeconfig"
  value       = "aws eks --region ${var.aws_region} --profile ${var.aws_profile} update-kubeconfig --name ${data.aws_eks_cluster.existing.name}"
}
