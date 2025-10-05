# EKS Service Communication Flow

## 🔄 **Complete Communication Architecture**

### **External User → Frontend → Backend Flow**
```
Internet User
    ↓ HTTP Request
AWS LoadBalancer (rag-frontend-service)
    ↓ Port 80
Frontend Pod (nginx)
    ↓ /api/* requests
    ↓ proxy_pass
Backend Pod (FastAPI)
    ↓ Port 8000
AWS Services (Kendra, S3, Bedrock, EFS)
```

## 🌐 **Kubernetes DNS Resolution**

### **Service Discovery Within EKS**
```
Frontend Pod → Backend Service DNS Resolution:

1. Short Name (same namespace):
   rag-backend-service
   ✅ Resolves to: rag-backend-service.rag-system.svc.cluster.local

2. Full DNS Name (explicit):
   rag-backend-service.rag-system.svc.cluster.local
   ✅ Resolves to backend pod IPs

3. Service Port Mapping:
   Service Port 8000 → Pod Port 8000
```

### **DNS Resolution Hierarchy**
```
Kubernetes DNS Search Path:
1. rag-system.svc.cluster.local    (same namespace)
2. svc.cluster.local               (cluster services)
3. cluster.local                   (cluster domain)
4. External DNS                    (if configured)
```

## 🔧 **Service Configuration Validation**

### **Backend Service (ClusterIP)**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: rag-backend-service
  namespace: rag-system
spec:
  selector:
    app: rag-backend          # Matches backend pods
  ports:
  - port: 8000               # Service port
    targetPort: 8000         # Pod port
    protocol: TCP
  type: ClusterIP            # Internal only
```

### **Frontend Service (LoadBalancer)**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: rag-frontend-service
  namespace: rag-system
spec:
  selector:
    app: rag-frontend         # Matches frontend pods
  ports:
  - port: 80                 # Service port
    targetPort: 80           # Pod port
    protocol: TCP
  type: LoadBalancer         # External access
```

## 🔀 **Nginx Proxy Configuration**

### **API Request Routing**
```nginx
# Frontend nginx.conf
location /api/ {
    # Full Kubernetes DNS name for reliability
    proxy_pass http://rag-backend-service.rag-system.svc.cluster.local:8000/;
    
    # Essential headers for proper proxying
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    # Timeout settings for long-running requests
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;
}
```

### **Request Flow Example**
```
User Request: http://loadbalancer/api/documents
    ↓
Nginx receives: /api/documents
    ↓
Proxy rewrite: http://rag-backend-service.rag-system.svc.cluster.local:8000/documents
    ↓
Backend receives: GET /documents
    ↓
Backend response: JSON document list
    ↓
Nginx forwards: Response to user
```

## 🔍 **Communication Testing**

### **Validation Commands**
```bash
# Run comprehensive validation
./validate-communication.sh

# Manual DNS testing
kubectl exec <frontend-pod> -n rag-system -- nslookup rag-backend-service

# Manual HTTP testing
kubectl exec <frontend-pod> -n rag-system -- curl http://rag-backend-service:8000/

# Check service endpoints
kubectl get endpoints -n rag-system

# Test proxy functionality
kubectl exec <frontend-pod> -n rag-system -- curl http://localhost/api/
```

### **Health Check Endpoints**
```bash
# Backend health (direct)
curl http://rag-backend-service:8000/

# Frontend health (via proxy)
curl http://rag-frontend-service/api/

# External health (via LoadBalancer)
curl http://<external-ip>/api/
```

## 🚨 **Common Issues & Solutions**

### **DNS Resolution Issues**
```bash
# Problem: "rag-backend-service: Name or service not known"
# Solution: Use full DNS name
proxy_pass http://rag-backend-service.rag-system.svc.cluster.local:8000/;

# Verify DNS resolution
kubectl exec <pod> -- nslookup rag-backend-service.rag-system.svc.cluster.local
```

### **Service Discovery Issues**
```bash
# Check service exists
kubectl get svc rag-backend-service -n rag-system

# Check service has endpoints
kubectl get endpoints rag-backend-service -n rag-system

# Check pod labels match service selector
kubectl get pods -n rag-system --show-labels
```

### **Proxy Configuration Issues**
```bash
# Check nginx configuration
kubectl exec <frontend-pod> -- cat /etc/nginx/conf.d/default.conf

# Test proxy without DNS
kubectl exec <frontend-pod> -- curl http://10.x.x.x:8000/  # Direct pod IP

# Check nginx error logs
kubectl exec <frontend-pod> -- cat /var/log/nginx/error.log
```

### **Port Mapping Issues**
```bash
# Verify backend is listening on correct port
kubectl exec <backend-pod> -- netstat -tlnp | grep 8000

# Check service port mapping
kubectl describe svc rag-backend-service -n rag-system

# Test port connectivity
kubectl exec <frontend-pod> -- telnet rag-backend-service 8000
```

## 📊 **Network Flow Diagram**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Internet      │    │   AWS LB        │    │  Frontend Pod   │
│   User          │───▶│   (External)    │───▶│  nginx:80       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                                        │ /api/* requests
                                                        ▼
                                               ┌─────────────────┐
                                               │  Backend Pod    │
                                               │  FastAPI:8000   │
                                               └─────────────────┘
                                                        │
                                                        │ AWS API calls
                                                        ▼
                                               ┌─────────────────┐
                                               │  AWS Services   │
                                               │  S3/Kendra/etc  │
                                               └─────────────────┘
```

## ✅ **Validation Checklist**

- [ ] **Namespace exists**: `kubectl get ns rag-system`
- [ ] **Services exist**: `kubectl get svc -n rag-system`
- [ ] **Pods are ready**: `kubectl get pods -n rag-system`
- [ ] **DNS resolves**: `nslookup rag-backend-service.rag-system.svc.cluster.local`
- [ ] **HTTP connectivity**: `curl http://rag-backend-service:8000/`
- [ ] **Proxy works**: `curl http://localhost/api/` (from frontend pod)
- [ ] **External access**: `curl http://<external-ip>/api/`
- [ ] **Endpoints populated**: `kubectl get endpoints -n rag-system`

## 🔧 **Troubleshooting Commands**

```bash
# Complete validation
./validate-communication.sh

# Service debugging
kubectl describe svc rag-backend-service -n rag-system
kubectl describe svc rag-frontend-service -n rag-system

# Pod debugging
kubectl describe pod <pod-name> -n rag-system
kubectl logs <pod-name> -n rag-system

# Network debugging
kubectl exec <frontend-pod> -n rag-system -- ping rag-backend-service
kubectl exec <frontend-pod> -n rag-system -- telnet rag-backend-service 8000

# DNS debugging
kubectl exec <frontend-pod> -n rag-system -- cat /etc/resolv.conf
kubectl exec <frontend-pod> -n rag-system -- nslookup kubernetes.default
```

This communication flow ensures reliable service discovery and HTTP connectivity between frontend and backend pods within the EKS cluster.
