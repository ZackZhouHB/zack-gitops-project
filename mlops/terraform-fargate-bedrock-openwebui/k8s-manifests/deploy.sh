#!/bin/bash

echo "Deploying OpenWebUI to Minikube..."

# Apply manifests in order
kubectl apply -f aws-credentials-secret.yaml
kubectl apply -f persistent-volume-claim.yaml
kubectl apply -f openwebui-deployment.yaml
kubectl apply -f openwebui-service.yaml

echo "Deployment complete!"
echo ""
echo "To access the service:"
echo "minikube service openwebui-service --url"
echo ""
echo "Or open in browser:"
echo "minikube service openwebui-service"
echo ""
echo "To check status:"
echo "kubectl get pods"
echo "kubectl logs -f deployment/openwebui-deployment -c openwebui"
echo "kubectl logs -f deployment/openwebui-deployment -c bedrock-gateway"
