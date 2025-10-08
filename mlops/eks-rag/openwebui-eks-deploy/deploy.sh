#!/bin/bash

echo "Deploying OpenWebUI to EKS cluster..."

# Apply manifests in order
kubectl apply -f 01-persistent-volume.yaml
kubectl apply -f 02-persistent-volume-claim.yaml
kubectl apply -f 03-deployment.yaml
kubectl apply -f 04-service.yaml

echo "Waiting for deployment to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/openwebui-deployment

echo "Getting service endpoint..."
kubectl get service openwebui-service

echo "Deployment complete!"
echo "To check status: kubectl get pods,svc"
echo "To get logs: kubectl logs -l app=openwebui -c openwebui"
