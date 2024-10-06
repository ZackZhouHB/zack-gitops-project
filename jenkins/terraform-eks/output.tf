output "node_group_id" {
  description = "The ID of the EKS node group."
  value       = aws_eks_node_group.example.id
}

output "cluster_name" {
  description = "The name of the EKS cluster."
  value       = aws_eks_cluster.example.name
}


output "cluster_role_arn" {
  description = "The ARN of the EKS cluster IAM role."
  value       = aws_iam_role.eks_cluster_role.arn  # This line is not needed
}

output "node_role_arn" {
  description = "The ARN of the node IAM role."
  value       = aws_iam_role.eks_node_role.arn  # This line is not needed
}