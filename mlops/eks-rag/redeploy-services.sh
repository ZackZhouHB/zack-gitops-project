#!/bin/bash

# Service Redeployment Script
# This script redeploys LoadBalancer services to get proper custom names

set -e

echo "=== Redeploying LoadBalancer Services ==="

# Delete existing services
echo "1. Deleting existing LoadBalancer services..."
kubectl delete service openwebui-service -n openwebui --ignore-not-found=true
kubectl delete service rag-frontend-service -n rag-system --ignore-not-found=true

# Wait for load balancers to be deleted
echo "2. Waiting for AWS load balancers to be deleted..."
sleep 60

# Redeploy services
echo "3. Redeploying OpenWebUI service..."
kubectl apply -f openwebui-eks-deploy/04-service.yaml

echo "4. Redeploying RAG frontend service..."
kubectl apply -f rag-system-eks-deploy/frontend-deployment.yaml

# Wait for services to be ready
echo "5. Waiting for services to get external IPs..."
sleep 30

# Show results
echo "=== Service Status ==="
kubectl get svc -A | grep LoadBalancer

echo ""
echo "=== AWS Load Balancer Names ==="
aws elbv2 describe-load-balancers --region ap-southeast-2 --profile sandboxtest --query 'LoadBalancers[].{Name:LoadBalancerName,DNS:DNSName,State:State.Code}' --output table

echo "=== Redeployment completed! ==="
