# Chat History Feature - Testing Guide

## Quick Start Testing

### 1. Build Docker Images

```bash
cd /mnt/f/zack-gitops-project/mlops/eks-rag/langchain-memory

# Backend
cd backend
docker build -t rag-backend-langchain:v1.1-memory .

# Frontend
cd ../frontend
docker build -t rag-frontend-langchain:v1.1-memory .
```

### 2. Test Locally (Optional)

If you want to test locally before deploying to EKS:

```bash
# Run backend
docker run -p 8000:8000 \
  -e AWS_REGION=ap-southeast-2 \
  -e WEAVIATE_URL=http://your-weaviate:8080 \
  -e S3_BUCKET=your-bucket \
  rag-backend-langchain:v1.1-memory

# Run frontend
docker run -p 80:80 rag-frontend-langchain:v1.1-memory
```

### 3. Deploy to EKS

```bash
# Tag and push to ECR
aws ecr get-login-password --region ap-southeast-2 | docker login --username AWS --password-stdin xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com

# Backend
docker tag rag-backend-langchain:v1.1-memory xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-backend-langchain:v1.1-memory
docker push xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-backend-langchain:v1.1-memory

# Frontend
docker tag rag-frontend-langchain:v1.1-memory xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-frontend-langchain:v1.1-memory
docker push xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-frontend-langchain:v1.1-memory

# Update deployments
kubectl set image deployment/rag-backend-langchain \
  backend=xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-backend-langchain:v1.1-memory \
  -n langchain

kubectl set image deployment/rag-frontend-langchain \
  frontend=xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-frontend-langchain:v1.1-memory \
  -n langchain

# Wait for rollout
kubectl rollout status deployment/rag-backend-langchain -n langchain
kubectl rollout status deployment/rag-frontend-langchain -n langchain
```

## Functional Test Cases

### Test 1: Basic Conversation Flow

**Steps:**
1. Open the application in browser
2. Navigate to "💬 MAKE A QUERY" tab
3. Type a question: "What is AWS EKS?"
4. Click "🔍 Ask" button
5. Wait for response

**Expected Results:**
- ✅ Question appears in blue bubble on the right
- ✅ Loading indicator shows "Thinking..." with animated dots
- ✅ Answer appears in white bubble on the left
- ✅ Sources displayed below answer with confidence scores
- ✅ Execution time shown at bottom of answer
- ✅ Conversation thread scrolls to show latest message

### Test 2: Consecutive Questions

**Steps:**
1. Ask first question: "What is AWS EKS?"
2. Wait for answer
3. Ask follow-up: "What are its benefits?"
4. Wait for answer
5. Ask another: "How much does it cost?"

**Expected Results:**
- ✅ All Q&A pairs visible in conversation thread
- ✅ Thread maintains scroll position at bottom
- ✅ Each answer references previous context
- ✅ Session cookie maintained across requests

### Test 3: New Chat Functionality

**Steps:**
1. Have an active conversation with 2-3 Q&A pairs
2. Click "✨ New Chat" button
3. Verify conversation thread clears
4. Ask a new question

**Expected Results:**
- ✅ Conversation thread shows empty state message
- ✅ Previous conversation saved (check browser console)
- ✅ New session ID generated
- ✅ New question starts fresh conversation (no context from previous)

### Test 4: Enter Key Support

**Steps:**
1. Type a question in the textarea
2. Press Enter key (without Shift)

**Expected Results:**
- ✅ Question submitted automatically
- ✅ Same behavior as clicking "Ask" button

### Test 5: Shift+Enter for New Line

**Steps:**
1. Type a question
2. Press Shift+Enter
3. Type more text on new line

**Expected Results:**
- ✅ New line added in textarea
- ✅ Question NOT submitted
- ✅ Can continue typing multi-line question

### Test 6: Loading States

**Steps:**
1. Ask a question
2. Observe loading indicator
3. Try clicking "Ask" button again while loading

**Expected Results:**
- ✅ Loading indicator appears immediately
- ✅ Animated typing dots visible
- ✅ "Ask" button disabled during processing
- ✅ "New Chat" button disabled during processing
- ✅ Input textarea disabled during processing
- ✅ Loading indicator removed when answer arrives

### Test 7: Error Handling

**Steps:**
1. Stop backend service temporarily
2. Ask a question
3. Observe error handling

**Expected Results:**
- ✅ Error message appears in conversation thread
- ✅ Status message shows error details
- ✅ Buttons re-enabled after error
- ✅ Can retry question

### Test 8: Source Display

**Steps:**
1. Ask a question that has document sources
2. Examine the answer

**Expected Results:**
- ✅ Sources section visible below answer
- ✅ Each source shows document name
- ✅ Confidence score displayed as percentage
- ✅ Sources formatted with icons and badges

### Test 9: Mobile Responsiveness

**Steps:**
1. Open application on mobile device or resize browser to mobile width
2. Navigate to Query tab
3. Test all functionality

**Expected Results:**
- ✅ Layout adapts to mobile screen
- ✅ Message bubbles resize appropriately
- ✅ Buttons stack vertically if needed
- ✅ All features work on mobile

### Test 10: Session Persistence

**Steps:**
1. Ask 2-3 questions
2. Refresh the browser page
3. Ask another question

**Expected Results:**
- ✅ Session ID persists (check sessionStorage)
- ✅ Conversation context maintained
- ✅ Follow-up question uses previous context

## API Endpoint Testing

### Test Session Management Endpoints

```bash
# Get session statistics
curl http://your-app-url/api/conversation/stats

# Expected response:
{
  "active_sessions": 5,
  "oldest_session_age_minutes": 15.5,
  "total_memory_mb": 0.25
}

# Get memory metrics
curl http://your-app-url/api/metrics/memory

# Expected response:
{
  "memory_used_mb": 245.67,
  "memory_percent": 24.5,
  "session_stats": {
    "active_sessions": 5,
    "oldest_session_age_minutes": 15.5,
    "total_memory_mb": 0.25
  }
}

# Clear a specific session
curl -X DELETE http://your-app-url/api/conversation/{session_id}

# Expected response:
{
  "message": "Conversation cleared",
  "session_id": "session_1234567890_abc123"
}
```

## Performance Testing

### Memory Usage Test

**Steps:**
1. Monitor memory metrics endpoint
2. Create 10 concurrent sessions
3. Each session: ask 20 questions
4. Check memory usage

**Expected Results:**
- ✅ Memory usage < 1MB for 10 sessions
- ✅ No memory leaks
- ✅ Old sessions cleaned up after 60 minutes

### Load Test

```bash
# Simple load test with curl
for i in {1..50}; do
  curl -X POST http://your-app-url/api/query \
    -H "Content-Type: application/json" \
    -d '{"question": "What is AWS?", "top_k": 5}' &
done
wait

# Check if all requests succeeded
```

## Rollback Testing

### Test Rollback Procedure

```bash
# Rollback to stable version
kubectl set image deployment/rag-backend-langchain \
  backend=xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-backend-langchain:v1.0-stable \
  -n langchain

kubectl set image deployment/rag-frontend-langchain \
  frontend=xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-frontend-langchain:v1.0-stable \
  -n langchain

# Verify rollback
kubectl rollout status deployment/rag-backend-langchain -n langchain
kubectl rollout status deployment/rag-frontend-langchain -n langchain

# Test application still works
# Then roll forward again to v1.1-memory
```

## Troubleshooting

### Issue: Conversation thread not showing messages

**Check:**
- Browser console for JavaScript errors
- Verify `current-conversation-thread` element exists in HTML
- Check CSS is loaded properly

### Issue: Session not persisting

**Check:**
- Browser cookies enabled
- sessionStorage working
- Backend returning session cookie in response

### Issue: Loading indicator stuck

**Check:**
- Backend logs for errors
- Network tab for failed requests
- JavaScript console for errors in removeLoadingMessage()

### Issue: New Chat button not working

**Check:**
- JavaScript console for errors
- Verify startNewChat() function exists
- Check sessionStorage for session ID updates

## Success Criteria Checklist

- [ ] All 10 functional tests pass
- [ ] API endpoints return expected responses
- [ ] Memory usage within acceptable limits
- [ ] No JavaScript errors in console
- [ ] No backend errors in logs
- [ ] Mobile responsive layout works
- [ ] Session management works correctly
- [ ] Rollback procedure tested successfully
- [ ] Performance acceptable under load
- [ ] User experience smooth and intuitive

## Next Steps After Testing

1. Document any issues found
2. Fix critical bugs
3. Re-test after fixes
4. Get user acceptance testing
5. Plan production deployment
6. Update documentation with lessons learned
