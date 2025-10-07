#!/bin/bash
# Import existing EKS addons to standalone resources

CLUSTER_NAME="eks-rag-cluster"

echo "Importing existing EKS addons..."

terraform import 'aws_eks_addon.this["vpc-cni"]' ${CLUSTER_NAME}:vpc-cni
terraform import 'aws_eks_addon.this["coredns"]' ${CLUSTER_NAME}:coredns  
terraform import 'aws_eks_addon.this["kube-proxy"]' ${CLUSTER_NAME}:kube-proxy
terraform import 'aws_eks_addon.this["aws-ebs-csi-driver"]' ${CLUSTER_NAME}:aws-ebs-csi-driver
terraform import 'aws_eks_addon.this["aws-efs-csi-driver"]' ${CLUSTER_NAME}:aws-efs-csi-driver

echo "Import complete!"
