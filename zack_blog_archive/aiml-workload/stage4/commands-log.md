# Stage 4 Commands Log

> **Purpose:** Document all commands for RAG enhancement  
> **Last Updated:** 2026-02-01 10:55 AEDT

---

## Session: 2026-02-01 (Sunday)

### Objective
Enhance RAG with advanced techniques from rag-v1 + new methods

---

## Phase 4.1: Setup

### 1. Verify Stage 3 RAG is Running

**Command:**
```bash
ssh -p 2222 root@192.168.50.61 "kubectl get pods -n ai-platform"
```

**Expected:**
```
ai-gateway-xxx      1/1     Running
rag-backend-xxx     1/1     Running
vllm-xxx            1/1     Running
weaviate-xxx        1/1     Running
```

---

## Phase 4.2: Advanced Chunking

### 2. Test Current Chunking (Baseline)

**Command:**
```bash
# Upload a longer document
cat > /tmp/test-doc.md << 'EOF'
# Kubernetes Overview

Kubernetes is an open-source container orchestration platform.

## Key Concepts

### Pods
Pods are the smallest deployable units in Kubernetes. A pod can contain one or more containers.

### Services
Services provide stable networking for pods. They abstract away pod IP addresses.

### Deployments
Deployments manage the desired state of pods. They handle rolling updates and rollbacks.

## Architecture

The Kubernetes architecture consists of:
- Control Plane (API server, scheduler, controller manager, etcd)
- Worker Nodes (kubelet, kube-proxy, container runtime)

## Best Practices

1. Use namespaces for isolation
2. Set resource limits
3. Use health checks
4. Implement RBAC
EOF

curl -X POST http://localhost:8080/v1/rag/upload -F "file=@/tmp/test-doc.md"
```

**Check chunks created:**
```bash
curl http://localhost:8080/v1/rag/documents
```

---

## Phase 4.3: Hybrid Search

### 3. Test Vector Search (Baseline)

**Command:**
```bash
curl -X POST http://localhost:8080/v1/rag/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What are pods in Kubernetes?"}'
```

### 4. Test Keyword Search

**Command:**
```bash
curl -X POST http://localhost:8080/v1/rag/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What are pods?", "search_type": "keyword"}'
```

### 5. Test Hybrid Search

**Command:**
```bash
curl -X POST http://localhost:8080/v1/rag/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What are pods?", "search_type": "hybrid", "alpha": 0.5}'
```

---

## Phase 4.4: Reranking

### 6. Test with Reranking

**Command:**
```bash
curl -X POST http://localhost:8080/v1/rag/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What are pods?", "use_rerank": true}'
```

---

## Phase 4.5: Evaluation

### 7. Run Evaluation

**Command:**
```bash
curl -X POST http://localhost:8080/v1/rag/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "test_cases": [
      {"question": "What are pods?", "expected_keywords": ["smallest", "deployable", "containers"]},
      {"question": "What is a Service?", "expected_keywords": ["networking", "stable", "abstract"]},
      {"question": "How does Kubernetes architecture work?", "expected_keywords": ["control plane", "worker nodes"]}
    ]
  }'
```

---

## Troubleshooting

### LangChain Import Error
```bash
# Check if langchain is installed
kubectl exec -n ai-platform deploy/rag-backend -- pip list | grep langchain
```

### Weaviate BM25 Not Working
```bash
# Check Weaviate version (needs 1.18+ for BM25)
kubectl exec -n ai-platform deploy/weaviate -- curl -s localhost:8080/v1/meta | jq '.version'
```
