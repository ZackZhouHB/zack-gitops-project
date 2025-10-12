#!/bin/bash

echo "🔍 Monitoring Weaviate LangChain Deployment"
echo "=========================================="

while true; do
    echo "$(date): Checking Weaviate status..."
    
    # Get pod status
    POD_STATUS=$(kubectl get pods -n langchain -l app=weaviate-langchain --no-headers | awk '{print $3}')
    POD_READY=$(kubectl get pods -n langchain -l app=weaviate-langchain --no-headers | awk '{print $2}')
    
    echo "Pod Status: $POD_STATUS"
    echo "Ready: $POD_READY"
    
    # Check if ready
    if [[ "$POD_STATUS" == "Running" && "$POD_READY" == "2/2" ]]; then
        echo ""
        echo "🎉 Weaviate is ready!"
        echo ""
        kubectl get pods -n langchain -o wide
        echo ""
        echo "✅ Ready to deploy backend and frontend"
        break
    fi
    
    # Show events if there are issues
    if [[ "$POD_STATUS" == "ImagePullBackOff" || "$POD_STATUS" == "ErrImagePull" || "$POD_STATUS" == "CrashLoopBackOff" ]]; then
        echo ""
        echo "⚠️  Issue detected. Recent events:"
        kubectl get events -n langchain --sort-by='.lastTimestamp' | tail -5
        echo ""
    fi
    
    echo "Waiting 30 seconds..."
    sleep 30
    echo ""
done
