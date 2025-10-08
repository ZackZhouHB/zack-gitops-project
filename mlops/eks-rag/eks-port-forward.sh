#!/bin/bash

# EKS Port-Forward Script
# This script forwards all services to localhost for easy access

echo "Starting port-forwarding for EKS services..."
echo "Press Ctrl+C to stop all port-forwards"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Stopping all port-forwards..."
    pkill -P $$
    exit 0
}

trap cleanup SIGINT SIGTERM

# Port-forward OpenWebUI
echo "✓ OpenWebUI: http://localhost:8080"
kubectl port-forward svc/openwebui-service -n openwebui 8080:80 > /dev/null 2>&1 &

# Port-forward RAG Frontend
echo "✓ RAG Frontend: http://localhost:8081"
kubectl port-forward svc/rag-frontend-service -n rag-system 8081:80 > /dev/null 2>&1 &

# Port-forward Kiali
echo "✓ Kiali Dashboard: http://localhost:20001/kiali/"
kubectl port-forward svc/kiali -n istio-system 20001:20001 > /dev/null 2>&1 &

# Port-forward Jaeger
echo "✓ Jaeger Tracing: http://localhost:16686"
kubectl port-forward svc/tracing -n istio-system 16686:80 > /dev/null 2>&1 &

# Port-forward Prometheus (optional)
echo "✓ Prometheus: http://localhost:9090"
kubectl port-forward svc/prometheus -n istio-system 9090:9090 > /dev/null 2>&1 &

# Port-forward Grafana
echo "✓ Grafana: http://localhost:3000"
kubectl port-forward svc/grafana -n istio-system 3000:3000 > /dev/null 2>&1 &

echo ""
echo "All services are now accessible locally!"
echo "Keep this terminal open. Press Ctrl+C to stop."
echo ""

# Wait indefinitely
wait
