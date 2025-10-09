#!/bin/bash

# AWS Load Balancer Controller Deployment Script
# Deploys using Helm (official method)

set -e

CLUSTER_NAME="eks-rag-weaviate"
VPC_ID="vpc-0f2933cbe2cc4769e"
REGION="ap-southeast-2"
NAMESPACE="kube-system"

echo "=== AWS Load Balancer Controller Deployment ==="

# Cleanup function
cleanup_controller() {
    echo "=== Cleaning up existing controller ==="
    
    # Try Helm uninstall first
    if helm list -n kube-system | grep -q aws-load-balancer-controller; then
        echo "Uninstalling Helm release..."
        helm uninstall aws-load-balancer-controller -n kube-system
    fi
    
    # Clean up any remaining resources
    echo "Cleaning up remaining resources..."
    kubectl delete deployment aws-load-balancer-controller -n kube-system --ignore-not-found=true
    kubectl delete service aws-load-balancer-webhook-service -n kube-system --ignore-not-found=true
    
    # Wait for cleanup
    echo "Waiting for cleanup to complete..."
    sleep 30
}

# Deploy with Helm
deploy_with_helm() {
    echo "1. Adding EKS Helm repository..."
    helm repo add eks https://aws.github.io/eks-charts
    helm repo update
    
    echo "2. Installing AWS Load Balancer Controller via Helm..."
    helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
        -n kube-system \
        --set image.tag=v2.7.2 \
        --set serviceAccount.name=aws-load-balancer-controller \
        --set serviceAccount.create=false \
        --set region=$REGION \
        --set clusterName=$CLUSTER_NAME \
        --set vpcId=$VPC_ID
    
    echo "3. Waiting for deployment to be ready..."
    kubectl wait --for=condition=available --timeout=300s deployment/aws-load-balancer-controller -n kube-system
}

# Main deployment function
main() {
    # Cleanup existing installation
    cleanup_controller
    
    # Deploy with Helm
    deploy_with_helm
    
    echo "=== Verifying deployment ==="
    kubectl get pods -n kube-system -l app.kubernetes.io/name=aws-load-balancer-controller
    
    echo "=== Deployment completed successfully! ==="
}

# Run main function
main
