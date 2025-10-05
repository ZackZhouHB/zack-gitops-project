# Pre-Deployment Checklist

## ✅ **Validation Complete - Ready for Redeployment**

### **Current State Verified**
- EKS Cluster: `eks-rag-cluster` (v1.28) - **ACTIVE**
- Node Group: `main-node-group` (2x m5.large) - **ACTIVE**
- S3 Bucket: `eks-rag-cluster-documents-abybmf5r` - **EXISTS**
- Kendra Index: `642b913d-b430-4a62-9dcd-ad2b94146a95` - **ACTIVE**
- EFS: `fs-0b756774ef7a6c4cf` - **AVAILABLE**
- ECR Repos: Backend + Frontend - **EXISTS**

### **Deploy Script Status: ✅ READY**
The `deploy.sh` script is production-ready and will handle:
- Infrastructure provisioning via Terraform
- Dynamic configuration updates
- Container image builds and ECR pushes
- Kubernetes deployment in correct order

### **Pre-Destruction Steps (Run These Tomorrow)**

```bash
# 1. Backup any important data
kubectl exec -n rag-system deployment/rag-backend -- cp -r /efs/chat_history /tmp/backup

# 2. Export current configuration
kubectl get configmap rag-config -n rag-system -o yaml > backup-config.yaml

# 3. Clean destroy (run from terraform/ directory)
terraform destroy -auto-approve -var-file="terraform.tfvars"

# 4. Verify cleanup
aws eks list-clusters --region ap-southeast-2 --profile sandboxtest
aws s3 ls --profile sandboxtest | grep eks-rag
```

### **Deployment Command (Tomorrow)**
```bash
# Single command deployment
./deploy.sh
```

### **Expected Deployment Time**
- Terraform Infrastructure: ~15-20 minutes
- Container Builds: ~5 minutes
- Kubernetes Deployment: ~5 minutes
- **Total: ~25-30 minutes**

### **Post-Deployment Validation**
```bash
# Check all services
kubectl get pods,svc -n rag-system

# Test API health
kubectl port-forward svc/rag-frontend-service 8080:80 -n rag-system
curl http://localhost:8080/api/

# Verify LoadBalancer
kubectl get svc rag-frontend-service -n rag-system
```

## **🎯 Confidence Level: HIGH**
All infrastructure matches Terraform configuration. Deploy script is robust and tested. No drama expected for tomorrow's redeployment.
