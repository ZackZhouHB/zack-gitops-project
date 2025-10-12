# Getting Started with langchain-memory Implementation

## Step-by-Step Implementation Guide

This guide walks you through implementing the conversation memory feature in the isolated `langchain-memory` folder.

## Prerequisites

- Current `langchain-way` is working and stable
- Docker installed and configured
- kubectl access to EKS cluster
- AWS CLI configured with ECR access

## Implementation Steps

### Step 1: Backup Current Stable Version

```bash
# Tag current langchain-way images as stable
docker pull xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-backend-langchain:latest
docker tag xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-backend-langchain:latest \
           xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-backend-langchain:v1.0-stable
docker push xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-backend-langchain:v1.0-stable

docker pull xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-frontend-langchain:latest
docker tag xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-frontend-langchain:latest \
           xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-frontend-langchain:v1.0-stable
docker push xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-frontend-langchain:v1.0-stable
```

### Step 2: Backend Changes

#### 2.1 Create SessionMemoryManager

Create `backend/app/session_manager.py`:

```bash
cd /mnt/f/zack-gitops-project/mlops/eks-rag/langchain-memory/backend/app
```

Copy the SessionMemoryManager code from `CHAT_HISTORY_IMPLEMENTATION.md` Phase 1, Section 1.2.

#### 2.2 Update langchain_rag_service.py

Add session management to the RAG service:
- Import SessionMemoryManager
- Initialize in __init__
- Update query method to accept session_id
- Use session-specific memory

See `CHAT_HISTORY_IMPLEMENTATION.md` Phase 1, Section 1.3 for details.

#### 2.3 Update main.py

Add new endpoints:
- Update `/query` to handle sessions
- Add `DELETE /conversation/{session_id}`
- Add `GET /conversation/stats`
- Add `GET /metrics/memory`

See `CHAT_HISTORY_IMPLEMENTATION.md` Phase 1, Section 1.4 for details.

#### 2.4 Update requirements.txt

Add:
```
psutil==5.9.8
```

### Step 3: Frontend Changes

#### 3.1 Update index.html

Replace the Query Tab section with the new layout from `CHAT_HISTORY_IMPLEMENTATION.md` Phase 2, Section 2.2.

Key changes:
- Add conversation thread container at top
- Keep Ask Questions in middle
- Add New Chat button
- Keep Shared Conversation History at bottom

#### 3.2 Update style.css

Add all new CSS from `CHAT_HISTORY_IMPLEMENTATION.md` Phase 2, Section 2.3:
- Conversation thread styles
- Message bubble styles
- History item styles
- Button styles
- Loading animations

#### 3.3 Update script.js

Add all new JavaScript functions from `CHAT_HISTORY_IMPLEMENTATION.md` Phase 2, Section 2.4:
- Session management
- Message rendering
- Conversation saving/loading
- History expansion
- Update initializeApp()

### Step 4: Build and Test Locally

```bash
# Build backend
cd /mnt/f/zack-gitops-project/mlops/eks-rag/langchain-memory/backend
docker build -t rag-backend-langchain:v1.1-memory .

# Build frontend
cd ../frontend
docker build -t rag-frontend-langchain:v1.1-memory .

# Test locally (optional - requires docker-compose setup)
# docker-compose up
```

### Step 5: Push to ECR

```bash
# Login to ECR
aws ecr get-login-password --region ap-southeast-2 --profile sandboxtest | \
  docker login --username AWS --password-stdin xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com

# Tag and push backend
docker tag rag-backend-langchain:v1.1-memory \
  xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-backend-langchain:v1.1-memory
docker push xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-backend-langchain:v1.1-memory

# Tag and push frontend
docker tag rag-frontend-langchain:v1.1-memory \
  xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-frontend-langchain:v1.1-memory
docker push xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-frontend-langchain:v1.1-memory
```

### Step 6: Deploy to Kubernetes

```bash
# Update backend deployment
kubectl set image deployment/rag-backend-langchain \
  backend=xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-backend-langchain:v1.1-memory \
  -n langchain

# Wait for backend rollout
kubectl rollout status deployment/rag-backend-langchain -n langchain

# Update frontend deployment
kubectl set image deployment/rag-frontend-langchain \
  frontend=xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-frontend-langchain:v1.1-memory \
  -n langchain

# Wait for frontend rollout
kubectl rollout status deployment/rag-frontend-langchain -n langchain
```

### Step 7: Verify Deployment

```bash
# Check pods are running
kubectl get pods -n langchain

# Check backend logs
kubectl logs -n langchain $(kubectl get pods -n langchain -l app=rag-backend-langchain -o jsonpath='{.items[0].metadata.name}') --tail=50

# Check frontend logs
kubectl logs -n langchain $(kubectl get pods -n langchain -l app=rag-frontend-langchain -o jsonpath='{.items[0].metadata.name}') --tail=50

# Get LoadBalancer URL
kubectl get svc rag-frontend-service -n langchain
```

### Step 8: Test Functionality

#### 8.1 Test Conversation Flow

1. Open the frontend URL in browser
2. Navigate to 💬 MAKE A QUERY tab
3. Ask a question: "What is Amazon S3?"
4. Verify:
   - Question appears in thread (right side, blue)
   - Answer appears in thread (left side, white)
   - Sources displayed with confidence
   - Execution time shown
5. Ask follow-up: "How do I secure it?"
6. Verify:
   - Context awareness (understands "it" = S3)
   - Both Q&A pairs visible in thread
7. Click **New Chat** button
8. Verify:
   - Thread clears
   - Previous conversation in history
   - Ready for new question

#### 8.2 Test History Expansion

1. Scroll to 📚 Shared Conversation History
2. Click to expand list
3. Click on a conversation item
4. Verify:
   - Shows all Q&A pairs
   - Sources and confidence visible
   - Execution time displayed

#### 8.3 Test Backend Endpoints

```bash
# Port forward to backend
kubectl port-forward -n langchain svc/rag-backend-service 8000:8000

# In another terminal:

# Test session stats
curl http://localhost:8000/api/conversation/stats

# Test memory metrics
curl http://localhost:8000/api/metrics/memory

# Test query with session
curl -c cookies.txt -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is S3?"}'

# Test follow-up (uses session cookie)
curl -b cookies.txt -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "How do I secure it?"}'
```

### Step 9: Monitor Performance

```bash
# Watch memory usage
watch -n 5 'kubectl top pods -n langchain'

# Check session stats
kubectl port-forward -n langchain svc/rag-backend-service 8000:8000
watch -n 10 'curl -s http://localhost:8000/api/metrics/memory | jq'

# Check logs for errors
kubectl logs -n langchain -l app=rag-backend-langchain --tail=100 -f
```

## Rollback Procedure

If issues occur:

```bash
# Rollback backend
kubectl set image deployment/rag-backend-langchain \
  backend=xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-backend-langchain:v1.0-stable \
  -n langchain

# Rollback frontend
kubectl set image deployment/rag-frontend-langchain \
  frontend=xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-frontend-langchain:v1.0-stable \
  -n langchain

# Verify rollback
kubectl rollout status deployment/rag-backend-langchain -n langchain
kubectl rollout status deployment/rag-frontend-langchain -n langchain
```

## Troubleshooting

### Issue: Sources showing "Unknown"

**Check:** Weaviate schema has correct properties
```bash
kubectl exec -n langchain $(kubectl get pods -n langchain -l app=rag-backend-langchain -o jsonpath='{.items[0].metadata.name}') -- python3 -c "
import weaviate
client = weaviate.Client('http://weaviate-service.langchain.svc.cluster.local:8080')
schema = client.schema.get('DocumentsLangChain')
print([p['name'] for p in schema.get('properties', [])])"
```

### Issue: Session not persisting

**Check:** Cookies are enabled in browser
**Check:** Backend logs for session creation
```bash
kubectl logs -n langchain -l app=rag-backend-langchain --tail=100 | grep -i session
```

### Issue: Memory usage high

**Check:** Active sessions count
```bash
curl http://localhost:8000/api/conversation/stats
```

**Check:** Memory metrics
```bash
curl http://localhost:8000/api/metrics/memory
```

### Issue: Conversation history not loading

**Check:** Browser localStorage
- Open browser DevTools → Application → Local Storage
- Look for `conversationHistory` key

**Check:** JavaScript console for errors
- Open browser DevTools → Console

## Next Steps

After successful deployment:

1. Monitor for 24 hours
2. Gather user feedback
3. Check memory usage patterns
4. Review session statistics
5. Consider additional features:
   - Conversation search
   - Export functionality
   - User authentication
   - Cloud-synced history

## Files Modified

**Backend:**
- `app/session_manager.py` (NEW)
- `app/langchain_rag_service.py` (MODIFIED)
- `app/main.py` (MODIFIED)
- `requirements.txt` (MODIFIED)

**Frontend:**
- `index.html` (MODIFIED - Query Tab section)
- `style.css` (MODIFIED - Added new styles)
- `script.js` (MODIFIED - Added new functions)

## Reference Documents

- `CHAT_HISTORY_IMPLEMENTATION.md` - Complete implementation details
- `README.md` - Overview and features
- `../langchain-way/README.md` - Original implementation
- `../langchain-way/DEPLOYMENT.md` - Deployment procedures
