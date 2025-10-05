#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 EKS Service Communication Validation${NC}"
echo "=================================================="

# Check if kubectl is configured
if ! kubectl cluster-info > /dev/null 2>&1; then
    echo -e "${RED}❌ kubectl not configured or cluster not accessible${NC}"
    exit 1
fi

echo -e "${GREEN}✅ kubectl configured${NC}"

# Check namespace
echo -e "\n${YELLOW}📋 Checking namespace and resources...${NC}"
kubectl get namespace rag-system > /dev/null 2>&1 || {
    echo -e "${RED}❌ Namespace 'rag-system' not found${NC}"
    exit 1
}
echo -e "${GREEN}✅ Namespace 'rag-system' exists${NC}"

# Check services
echo -e "\n${YELLOW}🔍 Validating services...${NC}"
kubectl get svc -n rag-system

BACKEND_SVC=$(kubectl get svc rag-backend-service -n rag-system -o jsonpath='{.metadata.name}' 2>/dev/null || echo "")
FRONTEND_SVC=$(kubectl get svc rag-frontend-service -n rag-system -o jsonpath='{.metadata.name}' 2>/dev/null || echo "")

if [ -z "$BACKEND_SVC" ]; then
    echo -e "${RED}❌ Backend service 'rag-backend-service' not found${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Backend service exists${NC}"

if [ -z "$FRONTEND_SVC" ]; then
    echo -e "${RED}❌ Frontend service 'rag-frontend-service' not found${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Frontend service exists${NC}"

# Check pods
echo -e "\n${YELLOW}🔍 Checking pod status...${NC}"
kubectl get pods -n rag-system

# Wait for pods to be ready
echo -e "\n${YELLOW}⏳ Waiting for pods to be ready...${NC}"
kubectl wait --for=condition=ready pod -l app=rag-backend -n rag-system --timeout=300s
kubectl wait --for=condition=ready pod -l app=rag-frontend -n rag-system --timeout=300s

echo -e "${GREEN}✅ All pods are ready${NC}"

# Test DNS resolution from frontend to backend
echo -e "\n${YELLOW}🔍 Testing DNS resolution...${NC}"

# Get a frontend pod name
FRONTEND_POD=$(kubectl get pods -n rag-system -l app=rag-frontend -o jsonpath='{.items[0].metadata.name}')
BACKEND_POD=$(kubectl get pods -n rag-system -l app=rag-backend -o jsonpath='{.items[0].metadata.name}')

if [ -z "$FRONTEND_POD" ] || [ -z "$BACKEND_POD" ]; then
    echo -e "${RED}❌ Could not find frontend or backend pods${NC}"
    exit 1
fi

echo "Frontend Pod: $FRONTEND_POD"
echo "Backend Pod: $BACKEND_POD"

# Test DNS resolution from frontend pod
echo -e "\n${YELLOW}🔍 Testing DNS resolution from frontend to backend...${NC}"

# Test short name (same namespace)
kubectl exec $FRONTEND_POD -n rag-system -- nslookup rag-backend-service > /dev/null 2>&1 && {
    echo -e "${GREEN}✅ Short DNS name resolves: rag-backend-service${NC}"
} || {
    echo -e "${YELLOW}⚠️  Short DNS name failed, testing full name...${NC}"
}

# Test full DNS name
kubectl exec $FRONTEND_POD -n rag-system -- nslookup rag-backend-service.rag-system.svc.cluster.local > /dev/null 2>&1 && {
    echo -e "${GREEN}✅ Full DNS name resolves: rag-backend-service.rag-system.svc.cluster.local${NC}"
} || {
    echo -e "${RED}❌ Full DNS name resolution failed${NC}"
    exit 1
}

# Test HTTP connectivity from frontend to backend
echo -e "\n${YELLOW}🔍 Testing HTTP connectivity...${NC}"

# Test backend health endpoint directly
kubectl exec $FRONTEND_POD -n rag-system -- wget -q -O - http://rag-backend-service.rag-system.svc.cluster.local:8000/ > /dev/null 2>&1 && {
    echo -e "${GREEN}✅ HTTP connectivity successful (frontend → backend)${NC}"
} || {
    echo -e "${RED}❌ HTTP connectivity failed (frontend → backend)${NC}"
    echo "Checking backend pod logs..."
    kubectl logs $BACKEND_POD -n rag-system --tail=10
    exit 1
}

# Test backend API endpoint
echo -e "\n${YELLOW}🔍 Testing backend API endpoint...${NC}"
BACKEND_RESPONSE=$(kubectl exec $BACKEND_POD -n rag-system -- curl -s http://localhost:8000/ 2>/dev/null || echo "")

if echo "$BACKEND_RESPONSE" | grep -q "healthy"; then
    echo -e "${GREEN}✅ Backend API responding correctly${NC}"
    echo "Response: $BACKEND_RESPONSE"
else
    echo -e "${RED}❌ Backend API not responding correctly${NC}"
    echo "Response: $BACKEND_RESPONSE"
    exit 1
fi

# Test frontend nginx proxy configuration
echo -e "\n${YELLOW}🔍 Testing frontend nginx proxy...${NC}"

# Test if nginx can proxy to backend
PROXY_TEST=$(kubectl exec $FRONTEND_POD -n rag-system -- curl -s http://localhost/api/ 2>/dev/null || echo "")

if echo "$PROXY_TEST" | grep -q "healthy"; then
    echo -e "${GREEN}✅ Frontend nginx proxy working correctly${NC}"
else
    echo -e "${RED}❌ Frontend nginx proxy not working${NC}"
    echo "Proxy response: $PROXY_TEST"
    echo "Checking nginx configuration..."
    kubectl exec $FRONTEND_POD -n rag-system -- cat /etc/nginx/conf.d/default.conf
    exit 1
fi

# Test external access (if LoadBalancer is ready)
echo -e "\n${YELLOW}🔍 Testing external access...${NC}"

EXTERNAL_IP=$(kubectl get svc rag-frontend-service -n rag-system -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || \
              kubectl get svc rag-frontend-service -n rag-system -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")

if [ -n "$EXTERNAL_IP" ]; then
    echo "External endpoint: http://$EXTERNAL_IP"
    
    # Test external connectivity (with timeout)
    timeout 10 curl -s "http://$EXTERNAL_IP/api/" > /dev/null 2>&1 && {
        echo -e "${GREEN}✅ External access working${NC}"
    } || {
        echo -e "${YELLOW}⚠️  External access not ready yet (LoadBalancer provisioning)${NC}"
    }
else
    echo -e "${YELLOW}⚠️  LoadBalancer external IP not yet assigned${NC}"
fi

# Service endpoints summary
echo -e "\n${BLUE}📊 Service Communication Summary${NC}"
echo "=============================================="
echo -e "${GREEN}✅ DNS Resolution: Working${NC}"
echo -e "${GREEN}✅ Internal HTTP: Working${NC}"
echo -e "${GREEN}✅ Nginx Proxy: Working${NC}"
echo -e "${GREEN}✅ Backend API: Working${NC}"

# Show service details
echo -e "\n${YELLOW}📋 Service Details:${NC}"
kubectl get svc -n rag-system -o wide

echo -e "\n${YELLOW}📋 Endpoint Details:${NC}"
kubectl get endpoints -n rag-system

echo -e "\n${GREEN}🎉 All service communication tests passed!${NC}"
echo -e "${BLUE}Frontend can successfully communicate with backend via Kubernetes DNS${NC}"
