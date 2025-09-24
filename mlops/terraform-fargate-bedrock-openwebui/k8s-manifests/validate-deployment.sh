#!/bin/bash

echo "=== OpenWebUI Deployment Validation ==="
echo ""

echo "1. Checking Pods Status:"
kubectl get pods -l app=openwebui
echo ""

echo "2. Checking Services:"
kubectl get svc openwebui-service
echo ""

echo "3. Checking PVC Status:"
kubectl get pvc openwebui-data
echo ""

echo "4. Checking Secret:"
kubectl get secret aws-credentials
echo ""

echo "5. Recent Events:"
kubectl get events --sort-by=.metadata.creationTimestamp --field-selector type!=Normal | tail -10
echo ""

echo "6. Pod Details (if issues found):"
POD_NAME=$(kubectl get pods -l app=openwebui -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ ! -z "$POD_NAME" ]; then
    echo "Pod: $POD_NAME"
    kubectl get pod $POD_NAME -o wide
    echo ""
    
    # Check if pod is not running
    STATUS=$(kubectl get pod $POD_NAME -o jsonpath='{.status.phase}')
    if [ "$STATUS" != "Running" ]; then
        echo "7. Pod Events (Troubleshooting):"
        kubectl describe pod $POD_NAME | grep -A 20 "Events:"
        echo ""
        
        echo "8. Container Status:"
        kubectl get pod $POD_NAME -o jsonpath='{.status.containerStatuses[*].state}' | jq .
    else
        echo "✅ Pod is Running!"
        echo ""
        echo "9. Service URL:"
        minikube service openwebui-service --url
    fi
else
    echo "❌ No pods found with label app=openwebui"
fi
