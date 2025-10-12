# Quick Deployment Guide

## 🚀 Deploy in 5 Minutes

### Prerequisites
- AWS CLI configured
- kubectl configured for your EKS cluster
- Docker installed

### Step 1: Build Images (2 minutes)

```bash
cd /mnt/f/zack-gitops-project/mlops/eks-rag/langchain-memory

# Backend
cd backend
docker build -t rag-backend-langchain:v1.1-memory .

# Frontend
cd ../frontend
docker build -t rag-frontend-langchain:v1.1-memory .
```

### Step 2: Push to ECR (2 minutes)

```bash
# Login to ECR
aws ecr get-login-password --region ap-southeast-2 | \
  docker login --username AWS --password-stdin \
  xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com

# Tag and push backend
docker tag rag-backend-langchain:v1.1-memory \
  xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-backend-langchain:v1.1-memory
docker push xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-backend-langchain:v1.1-memory

# Tag and push frontend
docker tag rag-frontend-langchain:v1.1-memory \
  xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-frontend-langchain:v1.1-memory
docker push xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-frontend-langchain:v1.1-memory
```

### Step 3: Deploy to EKS (1 minute)

```bash
# Update backend
kubectl set image deployment/rag-backend-langchain \
  backend=xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-backend-langchain:v1.1-memory \
  -n langchain

# Update frontend
kubectl set image deployment/rag-frontend-langchain \
  frontend=xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-frontend-langchain:v1.1-memory \
  -n langchain

# Wait for rollout
kubectl rollout status deployment/rag-backend-langchain -n langchain
kubectl rollout status deployment/rag-frontend-langchain -n langchain
```

### Step 4: Verify (30 seconds)

```bash
# Check pods
kubectl get pods -n langchain

# Check logs
kubectl logs -f deployment/rag-backend-langchain -n langchain --tail=50
kubectl logs -f deployment/rag-frontend-langchain -n langchain --tail=50

# Get service URL
kubectl get svc -n langchain
```

## 🔄 Quick Rollback

If something goes wrong:

```bash
kubectl set image deployment/rag-backend-langchain \
  backend=xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-backend-langchain:v1.0-stable \
  -n langchain

kubectl set image deployment/rag-frontend-langchain \
  frontend=xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-frontend-langchain:v1.0-stable \
  -n langchain
```

## ✅ Quick Test

1. Open application in browser
2. Go to "💬 MAKE A QUERY" tab
3. Ask: "What is AWS EKS?"
4. Verify:
   - Question appears in blue bubble (right)
   - Loading indicator shows
   - Answer appears in white bubble (left)
   - Sources displayed with confidence scores
5. Ask follow-up: "What are its benefits?"
6. Verify conversation context maintained
7. Click "✨ New Chat"
8. Verify thread clears

## 📊 Quick Monitoring

```bash
# Watch pods
watch kubectl get pods -n langchain

# Stream logs
kubectl logs -f deployment/rag-backend-langchain -n langchain

# Check memory
kubectl top pods -n langchain

# Check session stats
curl http://your-app-url/api/conversation/stats

# Check memory metrics
curl http://your-app-url/api/metrics/memory
```

## 🐛 Quick Troubleshooting

### Pods not starting?
```bash
kubectl describe pod <pod-name> -n langchain
kubectl logs <pod-name> -n langchain
```

### Images not pulling?
```bash
# Check ECR login
aws ecr get-login-password --region ap-southeast-2

# Verify images exist
aws ecr describe-images --repository-name rag-backend-langchain --region ap-southeast-2
aws ecr describe-images --repository-name rag-frontend-langchain --region ap-southeast-2
```

### Frontend not loading?
```bash
# Check nginx config
kubectl exec -it <frontend-pod> -n langchain -- cat /etc/nginx/conf.d/default.conf

# Check frontend logs
kubectl logs <frontend-pod> -n langchain
```

### Backend errors?
```bash
# Check backend logs
kubectl logs <backend-pod> -n langchain --tail=100

# Check environment variables
kubectl exec -it <backend-pod> -n langchain -- env | grep -E "AWS|WEAVIATE|S3"
```

## 📝 Quick Checklist

Before deployment:
- [ ] Stable version tagged (v1.0-stable)
- [ ] Docker images built successfully
- [ ] Images pushed to ECR
- [ ] kubectl configured correctly
- [ ] Backup plan ready

After deployment:
- [ ] Pods running (2/2 ready)
- [ ] No errors in logs
- [ ] Application accessible
- [ ] Basic functionality works
- [ ] Session management works
- [ ] New Chat button works

## 🎯 One-Liner Deploy

```bash
cd /mnt/f/zack-gitops-project/mlops/eks-rag/langchain-memory && \
docker build -t rag-backend-langchain:v1.1-memory backend/ && \
docker build -t rag-frontend-langchain:v1.1-memory frontend/ && \
aws ecr get-login-password --region ap-southeast-2 | docker login --username AWS --password-stdin xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com && \
docker tag rag-backend-langchain:v1.1-memory xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-backend-langchain:v1.1-memory && \
docker push xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-backend-langchain:v1.1-memory && \
docker tag rag-frontend-langchain:v1.1-memory xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-frontend-langchain:v1.1-memory && \
docker push xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-frontend-langchain:v1.1-memory && \
kubectl set image deployment/rag-backend-langchain backend=xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-backend-langchain:v1.1-memory -n langchain && \
kubectl set image deployment/rag-frontend-langchain frontend=xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-frontend-langchain:v1.1-memory -n langchain && \
kubectl rollout status deployment/rag-backend-langchain -n langchain && \
kubectl rollout status deployment/rag-frontend-langchain -n langchain && \
echo "✅ Deployment complete!"
```

## 📞 Need Help?

- Check `TESTING_GUIDE.md` for detailed test cases
- Check `IMPLEMENTATION_STATUS.md` for complete status
- Check `CHAT_HISTORY_IMPLEMENTATION.md` for technical details
- Check logs: `kubectl logs -f deployment/rag-backend-langchain -n langchain`
