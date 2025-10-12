# LangChain RAG with Conversation Memory

## Overview

This is an enhanced version of the LangChain RAG system with **ChatGPT-style consecutive conversation capability**. It builds upon the stable `langchain-way` implementation by adding:

- **Conversation Thread UI**: ChatGPT-style message bubbles showing full conversation history
- **Session Memory**: Maintains context across multiple questions in a conversation
- **New Chat Functionality**: Start fresh conversations while preserving history
- **Enhanced History**: Expandable conversation history showing all Q&A pairs

## Differences from langchain-way

### Backend Changes
- Added `SessionMemoryManager` for per-session memory management
- Updated to use `ConversationBufferWindowMemory(k=20)` to limit memory growth
- Added session-based query handling with cookie-based session IDs
- New endpoints: `/conversation/clear`, `/conversation/stats`, `/metrics/memory`

### Frontend Changes
- Reorganized 💬 MAKE A QUERY tab layout:
  - **TOP**: Current Conversation Thread (scrollable chat history)
  - **MIDDLE**: Ask Questions (with Ask + New Chat buttons)
  - **BOTTOM**: Shared Conversation History (expandable items)
- ChatGPT-style message bubbles (user right, bot left)
- Sources, confidence, and execution time displayed per message
- New Chat button to start fresh conversations
- Enhanced history items showing full Q&A threads when expanded

### Resource Requirements
- **Same as langchain-way**: 512Mi request, 1Gi limit
- Memory usage: ~50KB per conversation (20 turns max)
- Supports 1000+ concurrent long conversations

## Docker Images

**Backend:**
```
xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-backend-langchain:v1.1-memory
```

**Frontend:**
```
xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-frontend-langchain:v1.1-memory
```

**Stable Baseline (langchain-way):**
```
xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-backend-langchain:v1.0-stable
xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-frontend-langchain:v1.0-stable
```

## Quick Start

### 1. Build and Push Images

```bash
# Backend
cd backend
docker build -t rag-backend-langchain:v1.1-memory .
docker tag rag-backend-langchain:v1.1-memory \
  xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-backend-langchain:v1.1-memory
aws ecr get-login-password --region ap-southeast-2 --profile sandboxtest | \
  docker login --username AWS --password-stdin xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com
docker push xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-backend-langchain:v1.1-memory

# Frontend
cd ../frontend
docker build -t rag-frontend-langchain:v1.1-memory .
docker tag rag-frontend-langchain:v1.1-memory \
  xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-frontend-langchain:v1.1-memory
docker push xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-frontend-langchain:v1.1-memory
```

### 2. Deploy to Kubernetes

```bash
# Update backend
kubectl set image deployment/rag-backend-langchain \
  backend=xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-backend-langchain:v1.1-memory \
  -n langchain

# Update frontend
kubectl set image deployment/rag-frontend-langchain \
  frontend=xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-frontend-langchain:v1.1-memory \
  -n langchain

# Monitor rollout
kubectl rollout status deployment/rag-backend-langchain -n langchain
kubectl rollout status deployment/rag-frontend-langchain -n langchain
```

### 3. Rollback if Needed

```bash
# Rollback to stable langchain-way version
kubectl set image deployment/rag-backend-langchain \
  backend=xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-backend-langchain:v1.0-stable \
  -n langchain

kubectl set image deployment/rag-frontend-langchain \
  frontend=xx88accountid.dkr.ecr.ap-southeast-2.amazonaws.com/rag-frontend-langchain:v1.0-stable \
  -n langchain
```

## Features

### Conversation Thread
- Real-time chat interface with message bubbles
- User messages: blue, right-aligned
- Bot messages: white, left-aligned with sources
- Auto-scroll to latest message
- Shows confidence scores and execution time

### Session Management
- Cookie-based session tracking
- 20-turn conversation window
- 1-hour session timeout
- Automatic cleanup of old sessions

### New Chat Functionality
- Saves current conversation to history
- Clears thread for fresh start
- Stays in same tab (no navigation)
- Preserves all past conversations

### Enhanced History
- Collapsible conversation list
- Click to expand full Q&A thread
- Shows all questions and answers
- Displays sources and confidence per answer
- Stored in localStorage

## Testing

### Test Conversation Flow
1. Ask initial question → Verify appears in thread
2. Ask follow-up → Verify context awareness
3. Check sources and confidence displayed
4. Click New Chat → Verify thread clears
5. Check history → Verify conversation saved
6. Expand history item → Verify full Q&A visible

### Test Session Management
```bash
# Check session stats
curl http://localhost:8000/api/conversation/stats

# Check memory usage
curl http://localhost:8000/api/metrics/memory
```

## Implementation Details

See `CHAT_HISTORY_IMPLEMENTATION.md` for complete implementation details including:
- Backend session management
- Frontend UI components
- CSS styling
- JavaScript functions
- Testing procedures

## Known Limitations

- Maximum 20 turns per conversation (configurable)
- 1-hour session timeout (configurable)
- History stored in browser localStorage (not synced across devices)
- No user authentication (session-based only)

## Future Enhancements

- [ ] User authentication and cloud-synced history
- [ ] Conversation search and filtering
- [ ] Export conversations to PDF/text
- [ ] Conversation sharing via links
- [ ] Voice input support
- [ ] Streaming responses
- [ ] Multi-language support

## Support

For issues or questions:
1. Check `CHAT_HISTORY_IMPLEMENTATION.md` for detailed implementation
2. Review backend logs: `kubectl logs -n langchain <pod-name>`
3. Check browser console for frontend errors
4. Verify session cookies are enabled
5. Test memory metrics endpoint

## License

Same as parent project (eks-rag).
