# Weaviate RAG System Troubleshooting Guide

## 🔍 **Overview**

This guide covers troubleshooting the Weaviate-based RAG system deployed on EKS, including backend-to-Weaviate connectivity, client initialization, document indexing, and service configuration.

## 📊 **System Architecture**

### **Service Communication Flow**
```
Frontend → Backend Pods → Weaviate Service → Weaviate Pod
                                          ↓
                                    [Weaviate Container:8082] ← [Transformer Container:8080]
```

### **Port Configuration**
- **Weaviate Service**: Port 8080 → Target Port 8082
- **Weaviate Container**: Listens on port 8082
- **Transformer Container**: Listens on port 8080
- **Backend Connection**: Connects to `weaviate-service:8080`

## 🔧 **1. Backend to Weaviate Connectivity**

### **Check Service Connectivity**
```bash
# Test basic HTTP connectivity from backend pod
kubectl exec -n rag-system deployment/rag-backend -- python -c "
import urllib.request
try:
    response = urllib.request.urlopen('http://weaviate-service.rag-system.svc.cluster.local:8080/v1/.well-known/ready')
    print('✅ Weaviate connection successful')
except Exception as e:
    print(f'❌ Weaviate connection failed: {e}')
"
```

### **Check Service Configuration**
```bash
# Verify service endpoints
kubectl get endpoints weaviate-service -n rag-system

# Check service configuration
kubectl get svc weaviate-service -n rag-system -o yaml

# Expected output:
# ports:
# - name: http
#   port: 8080
#   targetPort: 8082
```

### **Validate DNS Resolution**
```bash
# Test DNS resolution from backend pod
kubectl exec -n rag-system deployment/rag-backend -- nslookup weaviate-service.rag-system.svc.cluster.local
```

## 🔧 **2. Weaviate Client Initialization**

### **Check Client Creation**
```bash
# Test Weaviate client initialization
kubectl exec -n rag-system deployment/rag-backend -- python -c "
from app.weaviate_service import WeaviateService
from app.config import Config
config = Config()
weaviate_service = WeaviateService(config)
print('✅ Weaviate client created successfully')
"
```

### **Check Backend Startup Logs**
```bash
# Check backend startup for Weaviate connection status
kubectl logs -n rag-system deployment/rag-backend --since=5m | grep -E "(weaviate|Weaviate|connection|client)"

# Look for these messages:
# ✅ "Weaviate connection test successful: 200"
# ✅ "Weaviate client created successfully"
# ❌ "Failed to connect to Weaviate"
```

### **Validate Service Status**
```bash
# Test service status endpoint
kubectl exec -n rag-system deployment/rag-frontend -- curl -s http://rag-backend-service:8000/ | jq '.service_status'

# Expected output:
# {
#   "weaviate": true,
#   "bedrock": true
# }
```

## 🔧 **3. Document Indexing Status**

### **Check Vector Statistics**
```bash
# Get current vector database stats
kubectl exec -n rag-system deployment/rag-backend -- python -c "
from app.weaviate_service import WeaviateService
from app.config import Config
config = Config()
weaviate_service = WeaviateService(config)
stats = weaviate_service.get_vector_stats()
print('📊 Vector Stats:', stats)
"
```

### **List Indexed Documents**
```bash
# Get list of indexed documents
kubectl exec -n rag-system deployment/rag-backend -- python -c "
from app.weaviate_service import WeaviateService
from app.config import Config
config = Config()
weaviate_service = WeaviateService(config)

try:
    client = weaviate_service.client
    result = client.query.get('Document', ['filename']).do()
    if 'data' in result and 'Get' in result['data'] and 'Document' in result['data']['Get']:
        docs = result['data']['Get']['Document']
        print(f'📄 Indexed Documents ({len(docs)}):')
        for i, doc in enumerate(docs):
            print(f'  {i+1}. {doc.get(\"filename\", \"N/A\")}')
    else:
        print('❌ No indexed documents found')
except Exception as e:
    print(f'❌ Error: {e}')
"
```

### **Compare S3 vs Indexed Documents**
```bash
# Compare S3 documents with indexed documents
kubectl exec -n rag-system deployment/rag-backend -- python -c "
from app.weaviate_service import WeaviateService
from app.document_service import DocumentService
from app.config import Config
config = Config()
weaviate_service = WeaviateService(config)
doc_service = DocumentService(config)

# Get S3 documents
s3_docs = doc_service.list_s3_documents()
print(f'📁 S3 Documents ({len(s3_docs)}):')
for doc in s3_docs:
    print(f'  - {doc[\"filename\"]}')

# Get indexed documents
try:
    client = weaviate_service.client
    result = client.query.get('Document', ['filename']).do()
    if 'data' in result and 'Get' in result['data'] and 'Document' in result['data']['Get']:
        indexed_docs = result['data']['Get']['Document']
        print(f'\\n📊 Indexed Documents ({len(indexed_docs)}):')
        for doc in indexed_docs:
            print(f'  - {doc.get(\"filename\", \"N/A\")}')
        
        # Find missing documents
        s3_filenames = {doc['filename'] for doc in s3_docs}
        indexed_filenames = {doc['filename'] for doc in indexed_docs}
        missing = s3_filenames - indexed_filenames
        
        print(f'\\n❌ Missing from index ({len(missing)}):')
        for filename in missing:
            print(f'  - {filename}')
    else:
        print('\\n❌ No indexed documents found')
except Exception as e:
    print(f'\\n❌ Error: {e}')
"
```

## 🔧 **4. Chunk Status and Search Results**

### **Test Document Search**
```bash
# Test search functionality
kubectl exec -n rag-system deployment/rag-backend -- python -c "
from app.weaviate_service import WeaviateService
from app.config import Config
config = Config()
weaviate_service = WeaviateService(config)

print('🔍 Testing search...')
results = weaviate_service.search_documents('test query', top_k=3)
print(f'✅ Search Results: {len(results)}')
for i, result in enumerate(results):
    print(f'{i+1}. Score: {result.get(\"score\", \"N/A\"):.4f}, File: {result.get(\"filename\", \"N/A\")}')
    print(f'   Content: {result.get(\"content\", \"N/A\")[:100]}...')
"
```

### **Test Query Endpoint**
```bash
# Test the full query endpoint
kubectl exec -n rag-system deployment/rag-frontend -- curl -s -X POST \
  http://rag-backend-service.rag-system.svc.cluster.local:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "test query", "top_k": 3}' | jq .
```

## 🔧 **5. Weaviate Pod Configuration**

### **Check Pod Status**
```bash
# Check Weaviate pod status
kubectl get pod weaviate-0 -n rag-system

# Expected: 2/2 Running (both containers)
```

### **Check Container Ports**
```bash
# Check what ports Weaviate is listening on
kubectl exec -n rag-system weaviate-0 -c weaviate -- netstat -tlnp | grep LISTEN

# Expected:
# tcp  0.0.0.0:8082  (Weaviate HTTP API)
# tcp  :::50051       (gRPC)
# tcp  :::6060        (Metrics)
```

### **Check Transformer Container**
```bash
# Check transformer container logs
kubectl logs weaviate-0 -n rag-system -c t2v-transformers --tail=10

# Expected: "Uvicorn running on http://0.0.0.0:8080"
```

### **Validate Container Communication**
```bash
# Check if Weaviate can reach transformer
kubectl logs weaviate-0 -n rag-system -c weaviate --tail=20 | grep -E "(transformer|ready)"

# Should NOT see: "transformer remote inference service not ready"
```

## 🔧 **6. ConfigMap and Environment Variables**

### **Check Backend Configuration**
```bash
# Check backend environment variables
kubectl exec -n rag-system deployment/rag-backend -- env | grep -i weaviate

# Expected:
# WEAVIATE_HOST=weaviate-service.rag-system.svc.cluster.local
# WEAVIATE_PORT=8080
```

### **Check ConfigMap**
```bash
# Check the rag-config ConfigMap
kubectl get configmap rag-config -n rag-system -o yaml

# Verify:
# WEAVIATE_HOST: weaviate-service.rag-system.svc.cluster.local
# WEAVIATE_PORT: "8080"
```

### **Check Weaviate Environment Variables**
```bash
# Check Weaviate StatefulSet environment
kubectl get statefulset weaviate -n rag-system -o jsonpath='{.spec.template.spec.containers[0].env}' | jq .

# Key variables:
# TRANSFORMERS_INFERENCE_API: "http://127.0.0.1:8080"
# CLUSTER_HOSTNAME: "node1"
```

## 🔧 **7. Auto-Indexing Process**

### **Check Auto-Indexing Logs**
```bash
# Check backend startup for auto-indexing
kubectl logs -n rag-system deployment/rag-backend --since=5m | grep -E "(indexing|indexed|Auto-indexed|unindexed)"

# Expected messages:
# "Found X unindexed documents, indexing..."
# "✅ Auto-indexed: filename.ext"
```

### **Trigger Manual Auto-Indexing**
```bash
# Restart backend to trigger auto-indexing
kubectl rollout restart deployment/rag-backend -n rag-system

# Wait and check logs
sleep 30
kubectl logs -n rag-system deployment/rag-backend --tail=20 | grep -E "(indexing|indexed)"
```

### **Manual Document Indexing**
```bash
# Manually index a specific document
kubectl exec -n rag-system deployment/rag-backend -- python -c "
from app.weaviate_service import WeaviateService
from app.document_service import DocumentService
from app.config import Config
import asyncio

async def manual_index():
    config = Config()
    weaviate_service = WeaviateService(config)
    doc_service = DocumentService(config)
    
    filename = 'your-document.pdf'  # Replace with actual filename
    print(f'🔍 Indexing: {filename}')
    
    try:
        content = await doc_service.get_document_content(filename)
        if content:
            print(f'✅ Content extracted: {len(content)} characters')
            success = weaviate_service.index_document(filename, content)
            print(f'📊 Indexing result: {success}')
        else:
            print('❌ Failed to extract content')
    except Exception as e:
        print(f'❌ Error: {e}')

asyncio.run(manual_index())
"
```

## 🔧 **8. Common Issues and Solutions**

### **Issue: Connection Refused**
```bash
# Symptoms: "Connection refused" errors
# Check: Service endpoints and pod status
kubectl get endpoints weaviate-service -n rag-system
kubectl get pod weaviate-0 -n rag-system

# Solution: Restart Weaviate pod
kubectl delete pod weaviate-0 -n rag-system
```

### **Issue: Transformer Not Ready**
```bash
# Symptoms: "transformer remote inference service not ready"
# Check: Container port conflicts
kubectl logs weaviate-0 -n rag-system -c weaviate | grep transformer
kubectl logs weaviate-0 -n rag-system -c t2v-transformers

# Solution: Verify port configuration in StatefulSet
kubectl get statefulset weaviate -n rag-system -o yaml | grep -A 5 -B 5 containerPort
```

### **Issue: Documents Not Indexing**
```bash
# Check: S3 vs indexed document comparison (see section 3)
# Check: Auto-indexing logs (see section 7)
# Solution: Manual indexing or backend restart
kubectl rollout restart deployment/rag-backend -n rag-system
```

### **Issue: Search Returns No Results**
```bash
# Check: Weaviate client status
# Test: Direct search function (see section 4)
# Solution: Restart backend to refresh client connection
kubectl rollout restart deployment/rag-backend -n rag-system
```

### **Issue: Service Status Shows Weaviate False**
```bash
# Check: Backend startup logs for connection errors
kubectl logs -n rag-system deployment/rag-backend --since=5m | grep -i weaviate

# Solution: Restart backend after ensuring Weaviate is healthy
kubectl rollout restart deployment/rag-backend -n rag-system
```

## 🔧 **9. Validation Test Suite**

### **Complete System Validation**
```bash
#!/bin/bash
# Complete validation script

echo "🔍 Starting Weaviate RAG System Validation..."

# 1. Check pod status
echo "1. Checking pod status..."
kubectl get pods -n rag-system

# 2. Test connectivity
echo "2. Testing Weaviate connectivity..."
kubectl exec -n rag-system deployment/rag-backend -- python -c "
import urllib.request
try:
    urllib.request.urlopen('http://weaviate-service.rag-system.svc.cluster.local:8080/v1/.well-known/ready')
    print('✅ Connectivity: PASS')
except:
    print('❌ Connectivity: FAIL')
"

# 3. Check vector stats
echo "3. Checking vector statistics..."
kubectl exec -n rag-system deployment/rag-backend -- python -c "
from app.weaviate_service import WeaviateService
from app.config import Config
config = Config()
weaviate_service = WeaviateService(config)
stats = weaviate_service.get_vector_stats()
print(f'📊 Vector Stats: {stats}')
"

# 4. Test search
echo "4. Testing search functionality..."
kubectl exec -n rag-system deployment/rag-backend -- python -c "
from app.weaviate_service import WeaviateService
from app.config import Config
config = Config()
weaviate_service = WeaviateService(config)
results = weaviate_service.search_documents('test', top_k=1)
print(f'🔍 Search Results: {len(results)} documents found')
"

# 5. Test query endpoint
echo "5. Testing query endpoint..."
kubectl exec -n rag-system deployment/rag-frontend -- curl -s -X POST \
  http://rag-backend-service.rag-system.svc.cluster.local:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "test", "top_k": 1}' | jq -r '.service_status | "Weaviate: \(.weaviate), Bedrock: \(.bedrock)"'

echo "✅ Validation complete!"
```

## 🔧 **10. Resource Requirements**

### **Current Resource Configuration**
```yaml
# Weaviate Container
resources:
  requests:
    memory: "1Gi"
    cpu: "100m"
  limits:
    memory: "2Gi"
    cpu: "300m"

# Transformer Container  
resources:
  requests:
    memory: "512Mi"
    cpu: "100m"
  limits:
    memory: "1Gi"
    cpu: "500m"
```

### **Check Resource Usage**
```bash
# Check current resource usage
kubectl top pod weaviate-0 -n rag-system --containers

# Check for OOMKilled events
kubectl describe pod weaviate-0 -n rag-system | grep -A 10 Events
```

## 📝 **Quick Reference Commands**

```bash
# Essential troubleshooting commands
kubectl get pods -n rag-system                                    # Check pod status
kubectl logs -n rag-system deployment/rag-backend --tail=20       # Backend logs
kubectl logs weaviate-0 -n rag-system -c weaviate --tail=20       # Weaviate logs
kubectl get endpoints weaviate-service -n rag-system              # Service endpoints
kubectl rollout restart deployment/rag-backend -n rag-system      # Restart backend
kubectl delete pod weaviate-0 -n rag-system                       # Restart Weaviate
```

This troubleshooting guide covers all the major components and common issues encountered with the Weaviate RAG system. Use the appropriate sections based on the specific symptoms you're experiencing.
