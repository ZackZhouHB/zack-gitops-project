# Deployment Strategy - Chat History Feature

## Current Infrastructure

### Existing Setup
- **Namespace 1:** `rag-system` - Original Weaviate RAG
- **Namespace 2:** `langchain` - LangChain RAG (current)
- **Node Group:** `langchain-nodes` (label: `node-group=langchain`)
- **IAM Role:** `eks-rag-weaviate-rag-backend-role`
- **S3 Bucket:** `eks-rag-langchain-docs-615299759525`
- **EFS:** Shared across namespaces

## ✅ RECOMMENDED: In-Place Update (Option 1)

**Deploy to existing `langchain` namespace with new image tags**

### Why This Approach?
- ✅ No new infrastructure needed
- ✅ Reuse existing IAM role and service account
- ✅ Same S3 bucket (different subdirectory)
- ✅ Same EFS mount (different subdirectory)
- ✅ Same node group
- ✅ Easy rollback (just change image tags back)
- ✅ Zero permission issues
- ✅ Minimal risk

### Deployment Steps

#### 1. Update Backend Deployment
```bash
# Just update the image tag
kubectl set image deployment/rag-backend-langchain \
  backend=615299759525.dkr.ecr.ap-southeast-2.amazonaws.com/rag-backend-langchain:v1.1-memory \
  -n langchain
```

#### 2. Update Frontend Deployment
```bash
kubectl set image deployment/rag-frontend-langchain \
  frontend=615299759525.dkr.ecr.ap-southeast-2.amazonaws.com/rag-frontend-langchain:v1.1-memory \
  -n langchain
```

#### 3. Update Environment Variables (Optional)
If you want separate S3/EFS paths:

```bash
kubectl set env deployment/rag-backend-langchain \
  S3_DOCUMENT_PREFIX=langchain-memory/ \
  EFS_HISTORY_PATH=/efs/langchain_memory_history/ \
  -n langchain
```

### Resource Sharing Strategy

#### S3 Bucket Structure
```
eks-rag-langchain-docs-615299759525/
├── documents/              # Current: v1.0-stable documents
├── langchain-memory/       # New: v1.1-memory documents (optional)
└── processed/              # Shared processed files
```

**Recommendation:** Use same `documents/` folder - no need to separate

#### EFS Structure
```
/efs/
├── langchain_chat_history/         # Current: global history
├── langchain_memory_history/       # New: memory version history (optional)
└── weaviate-data/                  # Shared Weaviate data
```

**Recommendation:** Use different history file path to avoid conflicts

### Configuration Changes Needed

**Backend Environment Variables:**
```yaml
env:
- name: GLOBAL_HISTORY_FILE
  value: "/efs/langchain_memory_history/global_history.json"  # Different from v1.0
```

**No other changes needed!** Everything else reuses existing resources.

### Rollback Plan
```bash
# Instant rollback to v1.0-stable
kubectl set image deployment/rag-backend-langchain \
  backend=615299759525.dkr.ecr.ap-southeast-2.amazonaws.com/rag-backend-langchain:v1.0-stable \
  -n langchain

kubectl set image deployment/rag-frontend-langchain \
  frontend=615299759525.dkr.ecr.ap-southeast-2.amazonaws.com/rag-frontend-langchain:v1.0-stable \
  -n langchain
```

---

## Alternative: Separate Namespace (Option 2)

**Only if you need complete isolation for testing**

### New Resources Needed

#### 1. New Namespace
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: langchain-memory
```

#### 2. Service Account (Reuse IAM Role)
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: rag-memory-service-account
  namespace: langchain-memory
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::615299759525:role/eks-rag-weaviate-rag-backend-role
```

**Note:** Same IAM role ARN - no new IAM role needed!

#### 3. Deployments with Same Node Group
```yaml
spec:
  template:
    spec:
      serviceAccountName: rag-memory-service-account
      nodeSelector:
        node-group: langchain  # Same node group!
```

### Why This Works Without New Node Group

**Node groups are just labels.** Multiple namespaces can share the same node group:
- `rag-system` namespace → uses nodes with `node-group=langchain`
- `langchain` namespace → uses nodes with `node-group=langchain`
- `langchain-memory` namespace → uses nodes with `node-group=langchain`

**Kubernetes scheduler handles the distribution automatically.**

### Resource Sharing

**S3 Bucket:** Same bucket, different prefix
```yaml
env:
- name: S3_BUCKET_NAME
  value: "eks-rag-langchain-docs-615299759525"
- name: S3_DOCUMENT_PREFIX
  value: "langchain-memory/"  # Different prefix
```

**EFS:** Same EFS, different mount path
```yaml
env:
- name: EFS_MOUNT_PATH
  value: "/efs"
- name: GLOBAL_HISTORY_FILE
  value: "/efs/langchain_memory_history/global_history.json"
```

**Weaviate:** Deploy new Weaviate instance OR share existing
```yaml
# Option A: Share existing Weaviate
env:
- name: WEAVIATE_HOST
  value: "weaviate-service.langchain.svc.cluster.local"
- name: WEAVIATE_CLASS_NAME
  value: "DocumentsMemory"  # Different class name

# Option B: New Weaviate instance
env:
- name: WEAVIATE_HOST
  value: "weaviate-service.langchain-memory.svc.cluster.local"
```

### Pros and Cons

**Pros:**
- ✅ Complete isolation for testing
- ✅ Can run both versions simultaneously
- ✅ No risk to existing deployment

**Cons:**
- ❌ More resources (duplicate Weaviate if not shared)
- ❌ More complex management
- ❌ Need to manage two namespaces
- ❌ Still need same IAM permissions

---

## 🎯 FINAL RECOMMENDATION

### Use Option 1: In-Place Update

**Reasons:**
1. **No Permission Issues:** Reuses existing service account and IAM role
2. **No New Infrastructure:** Same S3, EFS, node group
3. **Easy Rollback:** Just change image tags
4. **Minimal Risk:** Backward compatible changes
5. **Cost Effective:** No duplicate resources

### Implementation Plan

```bash
# 1. Build and push images
cd /mnt/f/zack-gitops-project/mlops/eks-rag/langchain-memory
docker build -t rag-backend-langchain:v1.1-memory backend/
docker build -t rag-frontend-langchain:v1.1-memory frontend/

# 2. Tag and push to ECR
aws ecr get-login-password --region ap-southeast-2 | \
  docker login --username AWS --password-stdin \
  615299759525.dkr.ecr.ap-southeast-2.amazonaws.com

docker tag rag-backend-langchain:v1.1-memory \
  615299759525.dkr.ecr.ap-southeast-2.amazonaws.com/rag-backend-langchain:v1.1-memory
docker push 615299759525.dkr.ecr.ap-southeast-2.amazonaws.com/rag-backend-langchain:v1.1-memory

docker tag rag-frontend-langchain:v1.1-memory \
  615299759525.dkr.ecr.ap-southeast-2.amazonaws.com/rag-frontend-langchain:v1.1-memory
docker push 615299759525.dkr.ecr.ap-southeast-2.amazonaws.com/rag-frontend-langchain:v1.1-memory

# 3. Update deployments (in-place)
kubectl set image deployment/rag-backend-langchain \
  backend=615299759525.dkr.ecr.ap-southeast-2.amazonaws.com/rag-backend-langchain:v1.1-memory \
  -n langchain

kubectl set image deployment/rag-frontend-langchain \
  frontend=615299759525.dkr.ecr.ap-southeast-2.amazonaws.com/rag-frontend-langchain:v1.1-memory \
  -n langchain

# 4. Wait for rollout
kubectl rollout status deployment/rag-backend-langchain -n langchain
kubectl rollout status deployment/rag-frontend-langchain -n langchain

# 5. Verify
kubectl get pods -n langchain
kubectl logs -f deployment/rag-backend-langchain -n langchain
```

### Configuration Update (Optional)

Only if you want separate history file:

```bash
# Update backend to use different history file path
kubectl set env deployment/rag-backend-langchain \
  GLOBAL_HISTORY_FILE=/efs/langchain_memory_history/global_history.json \
  -n langchain
```

**Note:** The code already uses `/efs/langchain_chat_history/global_history.json` by default, which is fine to keep.

---

## 📊 Resource Impact

### Current Resources (Unchanged)
- **Node Group:** `langchain-nodes` (1 node, t3.large)
- **IAM Role:** `eks-rag-weaviate-rag-backend-role`
- **S3 Bucket:** `eks-rag-langchain-docs-615299759525`
- **EFS:** Existing mount
- **Service Account:** `rag-service-account`

### New Resources (Option 1)
- **None!** Just new Docker images

### New Resources (Option 2 - If Separate Namespace)
- New namespace: `langchain-memory`
- New service account (reuses IAM role)
- New deployments (uses same node group)
- Optional: New Weaviate instance

---

## 🔒 Permission Considerations

### IAM Role Permissions (Already Exists)
The existing role `eks-rag-weaviate-rag-backend-role` already has:
- ✅ S3 read/write permissions
- ✅ Bedrock invoke permissions
- ✅ EFS access

**No new permissions needed!**

### Trust Relationship
The IAM role already trusts the service account:
```json
{
  "Effect": "Allow",
  "Principal": {
    "Federated": "arn:aws:iam::615299759525:oidc-provider/..."
  },
  "Action": "sts:AssumeRoleWithWebIdentity",
  "Condition": {
    "StringEquals": {
      "oidc.eks.ap-southeast-2.amazonaws.com/id/...:sub": 
        "system:serviceaccount:langchain:rag-service-account"
    }
  }
}
```

**If using Option 2 (separate namespace), add:**
```json
"system:serviceaccount:langchain-memory:rag-memory-service-account"
```

---

## ✅ Decision Matrix

| Criteria | Option 1: In-Place | Option 2: Separate NS |
|----------|-------------------|----------------------|
| New IAM Role | ❌ No | ❌ No |
| New Node Group | ❌ No | ❌ No |
| New S3 Bucket | ❌ No | ❌ No |
| New EFS | ❌ No | ❌ No |
| Permission Issues | ✅ None | ⚠️ Need trust update |
| Rollback Speed | ✅ Instant | ⚠️ Slower |
| Resource Cost | ✅ Zero | ⚠️ Higher |
| Complexity | ✅ Low | ⚠️ Medium |
| Risk Level | ✅ Low | ⚠️ Medium |

**Winner: Option 1 (In-Place Update)** 🏆
