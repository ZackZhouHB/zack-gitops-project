#!/bin/bash

# Import existing EKS addons to prevent conflicts
CLUSTER_NAME="eks-rag-cluster"
REGION="ap-southeast-2"
PROFILE="sandboxtest"

echo "Checking for existing EKS addons..."

# Get list of existing addons
EXISTING_ADDONS=$(aws eks list-addons --cluster-name $CLUSTER_NAME --region $REGION --profile $PROFILE --output text --query 'addons[]')

# Import each existing addon
for addon in $EXISTING_ADDONS; do
    echo "Importing addon: $addon"
    terraform import "aws_eks_addon.this[\"$addon\"]" "$CLUSTER_NAME:$addon" || echo "Failed to import $addon (may already be imported)"
done

echo "Import process completed."
