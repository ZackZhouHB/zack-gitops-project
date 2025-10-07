# Addon management with import capability
# Use lifecycle rules to handle existing addons gracefully

# Temporarily disabled - let EKS module manage addons
# locals {
#   # Define all desired addons
#   desired_addons = {
#     "vpc-cni" = {
#       most_recent = true
#     }
#     "coredns" = {
#       most_recent = true
#     }
#     "kube-proxy" = {
#       most_recent = true
#     }
#     "aws-ebs-csi-driver" = {
#       most_recent = true
#     }
#     "aws-efs-csi-driver" = {
#       most_recent = true
#     }
#   }
# }

# # Data source for addon versions
# data "aws_eks_addon_version" "this" {
#   for_each           = local.desired_addons
#   addon_name         = each.key
#   kubernetes_version = module.eks.cluster_version
#   most_recent        = true
  
#   depends_on = [module.eks]
# }

# # Manage addons with lifecycle rules to prevent conflicts
# resource "aws_eks_addon" "this" {
#   for_each = local.desired_addons
  
#   cluster_name                = module.eks.cluster_name
#   addon_name                 = each.key
#   addon_version              = data.aws_eks_addon_version.this[each.key].version
#   resolve_conflicts_on_create = "OVERWRITE"
#   resolve_conflicts_on_update = "OVERWRITE"
  
#   tags = local.common_tags
  
#   depends_on = [
#     module.eks.cluster_name,
#     module.eks.eks_managed_node_groups
#   ]
  
#   lifecycle {
#     ignore_changes = [addon_version]
#     create_before_destroy = true
#   }
# }
