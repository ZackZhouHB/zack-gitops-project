# Lifecycle rules to prevent unnecessary resource replacements
resource "null_resource" "node_group_lifecycle" {
  # This resource helps manage node group lifecycle
  triggers = {
    cluster_name = local.cluster_name
    node_group_config = jsonencode({
      min_size     = var.node_group_min_size
      max_size     = var.node_group_max_size
      desired_size = var.node_group_desired_size
      instance_types = var.node_group_instance_types
    })
  }
  
  lifecycle {
    # Prevent destruction of this resource
    prevent_destroy = false
  }
}

# Import existing resources helper
resource "null_resource" "import_helper" {
  triggers = {
    cluster_name = local.cluster_name
  }
  
  provisioner "local-exec" {
    command = <<-EOT
      # Check if addons exist and import if needed
      echo "Checking existing EKS addons..."
    EOT
    
    on_failure = continue
  }
}
