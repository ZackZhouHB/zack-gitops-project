# LangChain Backend Separation Checklist

## Required Infrastructure Separations

### ✅ 1. S3 Bucket (SEPARATE)
```bash
# Create new S3 bucket for LangChain backend
aws s3 mb s3://your-bucket-name-langchain --region ap-southeast-2
```

### ✅ 2. ECR Repository (SEPARATE)
```bash
# Create new ECR repository
aws ecr create-repository --repository-name rag-backend-langchain --region ap-southeast-2
```

### ✅ 3. EFS Structure (SEPARATE SUBDIRECTORY)
- **Original**: `/efs/chat_history/`
- **LangChain**: `/efs/langchain_chat_history/`
- Same EFS volume, different paths for isolation

### ✅ 4. Weaviate Schema (SEPARATE CLASS)
- **Original**: `Documents` class
- **LangChain**: `DocumentsLangChain` class
- Same Weaviate instance, different schemas

### ✅ 5. Kubernetes Resources (SEPARATE NAMES)
- **Deployment**: `rag-backend-langchain`
- **Service**: `rag-backend-langchain-service`
- **ConfigMap**: `rag-backend-langchain-config`

## Environment Variables for LangChain Backend

```yaml
env:
- name: S3_BUCKET_NAME
  value: "your-bucket-name-langchain"  # DIFFERENT BUCKET
- name: WEAVIATE_CLASS_NAME
  value: "DocumentsLangChain"          # DIFFERENT SCHEMA
- name: EFS_CHAT_SUBDIR
  value: "langchain_chat_history"      # DIFFERENT EFS PATH
- name: AWS_REGION
  value: "ap-southeast-2"
- name: WEAVIATE_HOST
  value: "weaviate-service.rag-system.svc.cluster.local"
- name: WEAVIATE_PORT
  value: "8080"
- name: BEDROCK_MODEL_ID
  value: "anthropic.claude-3-5-haiku-20241022-v1:0"
```

## Deployment Strategy

### Phase 1: Build and Push
```bash
# Build LangChain backend
cd backend-langchain
./build.sh

# Tag and push to ECR
aws ecr get-login-password --region ap-southeast-2 | docker login --username AWS --password-stdin <account>.dkr.ecr.ap-southeast-2.amazonaws.com
docker tag rag-backend-langchain:latest <account>.dkr.ecr.ap-southeast-2.amazonaws.com/rag-backend-langchain:latest
docker push <account>.dkr.ecr.ap-southeast-2.amazonaws.com/rag-backend-langchain:latest
```

### Phase 2: Deploy to Dedicated Node Group
```bash
# Create dedicated node group for LangChain backend
# Deploy with node selector to ensure separation
```

### Phase 3: Access Configuration
- **Original Backend**: `/api/*` routes
- **LangChain Backend**: `/api-lc/*` routes (or separate ALB)

## Shared Resources (OK to share)

### ✅ Same Weaviate Instance
- Different classes provide isolation
- Cost-effective resource sharing

### ✅ Same EFS Volume
- Different subdirectories provide isolation
- Maintains persistence capabilities

### ✅ Same AWS Services
- Bedrock, IAM roles can be shared
- No conflicts in usage

### ✅ Same Kubernetes Namespace
- Easier management and comparison
- Network policies can provide additional isolation if needed

## Testing Isolation

### Verify Separation
```bash
# Check different S3 buckets
aws s3 ls | grep rag

# Check different Weaviate classes
kubectl exec -it weaviate-0 -n rag-system -- curl http://localhost:8082/v1/schema

# Check different EFS paths
kubectl exec -it <backend-pod> -n rag-system -- ls -la /efs/

# Check different services
kubectl get svc -n rag-system | grep backend
```

### Test Independence
1. Upload document to original backend → should not appear in LangChain backend
2. Upload document to LangChain backend → should not appear in original backend
3. Chat history should be separate
4. Deleting documents should not affect the other backend

## Benefits of This Separation

- **Independent Testing**: Can test LangChain improvements without affecting production
- **Easy Rollback**: Original system remains untouched
- **Performance Comparison**: Can compare both systems side-by-side
- **Gradual Migration**: Can migrate users gradually from original to LangChain
- **Cost Optimization**: Shared infrastructure where safe, separate where needed
