output "cluster_endpoint" {
  value = module.eks.cluster_endpoint
}

output "cluster_name" {
  value = module.eks.cluster_name
}

# Remove or comment out the kubeconfig output if it's not available
# output "kubeconfig" {
#   value = module.eks.kubeconfig
# }
