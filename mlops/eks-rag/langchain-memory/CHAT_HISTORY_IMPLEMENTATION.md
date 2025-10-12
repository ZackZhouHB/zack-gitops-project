# Chat History Feature Implementation Plan

## Overview

This document outlines the implementation plan for adding ChatGPT-style consecutive conversation capability to the LangChain RAG system. The backend already supports conversation memory through `ConversationalRetrievalChain` - we just need to expose it properly in the frontend UI.

## Current State Backup

### Working Version (Before Changes)

**Backend Image (Current Working Version):**
```
615299759525.dkr.ecr.ap-southeast-2.amazonaws.com/rag-backend-langchain:v1.0-stable
```

**Frontend Image (Current Working Version):**
```
615299759525.dkr.ecr.ap-southeast-2.amazonaws.com/rag-frontend-langchain:v1.0-stable
```

**Action Required:** Tag and push current working images before making changes:

```bash
# Backend
docker pull 615299759525.dkr.ecr.ap-southeast-2.amazonaws.com/rag-backend-langchain:latest
docker tag 615299759525.dkr.ecr.ap-southeast-2.amazonaws.com/rag-backend-langchain:latest \
           615299759525.dkr.ecr.ap-southeast-2.amazonaws.com/rag-backend-langchain:v1.0-stable
docker push 615299759525.dkr.ecr.ap-southeast-2.amazonaws.com/rag-backend-langchain:v1.0-stable

# Frontend
docker pull 615299759525.dkr.ecr.ap-southeast-2.amazonaws.com/rag-frontend-langchain:latest
docker tag 615299759525.dkr.ecr.ap-southeast-2.amazonaws.com/rag-frontend-langchain:latest \
           615299759525.dkr.ecr.ap-southeast-2.amazonaws.com/rag-frontend-langchain:v1.0-stable
docker push 615299759525.dkr.ecr.ap-southeast-2.amazonaws.com/rag-frontend-langchain:v1.0-stable
```

## Recommended Approach: In-Place Updates

**Recommendation:** Update the existing codebase rather than creating a separate folder.

**Reasons:**
1. Backend changes are minimal (mostly configuration)
2. Frontend changes are UI-only (no breaking changes)
3. Easy rollback using Docker image tags
4. Maintains single source of truth
5. Simpler deployment and maintenance

**Rollback Strategy:**
```bash
# If issues occur, rollback to stable version:
kubectl set image deployment/rag-backend-langchain \
  backend=615299759525.dkr.ecr.ap-southeast-2.amazonaws.com/rag-backend-langchain:v1.0-stable \
  -n langchain

kubectl set image deployment/rag-frontend-langchain \
  frontend=615299759525.dkr.ecr.ap-southeast-2.amazonaws.com/rag-frontend-langchain:v1.0-stable \
  -n langchain
```

## Implementation Changes

### Phase 1: Backend Changes (Memory Management)

#### 1.1 Update Memory Configuration

**File:** `backend/app/langchain_rag_service.py`

**Current:**
```python
self.memory = ConversationBufferMemory(
    memory_key="chat_history",
    return_messages=True,
    output_key="answer"
)
```

**Change to:**
```python
from langchain.memory import ConversationBufferWindowMemory

self.memory = ConversationBufferWindowMemory(
    k=20,  # Keep last 20 conversation turns
    memory_key="chat_history",
    return_messages=True,
    output_key="answer"
)
```

**Rationale:** Prevents unlimited memory growth, keeps last 20 turns (sufficient for most conversations)

#### 1.2 Add Session Management

**File:** `backend/app/session_manager.py` (NEW FILE)

```python
from datetime import datetime, timedelta
from typing import Dict, Tuple
from langchain.memory import ConversationBufferWindowMemory
import logging

logger = logging.getLogger(__name__)

class SessionMemoryManager:
    """Manages conversation memory per session with automatic cleanup"""
    
    def __init__(self, session_timeout_minutes: int = 60, max_turns: int = 20):
        self.sessions: Dict[str, Tuple[ConversationBufferWindowMemory, datetime]] = {}
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
        self.max_turns = max_turns
    
    def get_memory(self, session_id: str) -> ConversationBufferWindowMemory:
        """Get or create memory for a session"""
        self._cleanup_old_sessions()
        
        if session_id not in self.sessions:
            logger.info(f"Creating new session: {session_id}")
            memory = ConversationBufferWindowMemory(
                k=self.max_turns,
                memory_key="chat_history",
                return_messages=True,
                output_key="answer"
            )
            self.sessions[session_id] = (memory, datetime.now())
        else:
            memory, _ = self.sessions[session_id]
            # Update last access time
            self.sessions[session_id] = (memory, datetime.now())
        
        return memory
    
    def clear_session(self, session_id: str):
        """Clear a specific session"""
        if session_id in self.sessions:
            logger.info(f"Clearing session: {session_id}")
            del self.sessions[session_id]
    
    def _cleanup_old_sessions(self):
        """Remove sessions older than timeout"""
        cutoff = datetime.now() - self.session_timeout
        old_sessions = [
            sid for sid, (_, last_access) in self.sessions.items() 
            if last_access < cutoff
        ]
        
        for sid in old_sessions:
            logger.info(f"Cleaning up expired session: {sid}")
            del self.sessions[sid]
    
    def get_stats(self) -> dict:
        """Get session statistics"""
        return {
            "active_sessions": len(self.sessions),
            "oldest_session_age_minutes": self._get_oldest_session_age(),
            "total_memory_mb": self._estimate_memory_usage()
        }
    
    def _get_oldest_session_age(self) -> float:
        """Get age of oldest session in minutes"""
        if not self.sessions:
            return 0
        oldest = min(last_access for _, last_access in self.sessions.values())
        return (datetime.now() - oldest).total_seconds() / 60
    
    def _estimate_memory_usage(self) -> float:
        """Estimate total memory usage in MB"""
        # Rough estimate: 50KB per session
        return len(self.sessions) * 0.05
```

#### 1.3 Update RAG Service to Use Session Manager

**File:** `backend/app/langchain_rag_service.py`

**Add at class level:**
```python
from .session_manager import SessionMemoryManager

class LangChainRAGService:
    def __init__(self, config):
        self.config = config
        # ... existing initialization ...
        
        # Session management
        self.session_manager = SessionMemoryManager(
            session_timeout_minutes=60,
            max_turns=20
        )
```

**Update query method:**
```python
async def query(self, question: str, session_id: str, top_k: int = 5) -> Dict[str, Any]:
    """Query documents using LangChain RAG chain with session memory"""
    try:
        import time
        start_time = time.time()
        
        # Get session-specific memory
        session_memory = self.session_manager.get_memory(session_id)
        
        # Create chain with session memory
        chain = ConversationalRetrievalChain.from_llm(
            llm=self.llm,
            retriever=self.vectorstore.as_retriever(search_kwargs={"k": top_k}),
            memory=session_memory,
            return_source_documents=True
        )
        
        # Query with session context
        result = chain({"question": question})
        
        # ... rest of existing code ...
```

#### 1.4 Add New API Endpoints

**File:** `backend/app/main.py`

**Add endpoints:**
```python
@app.post("/query")
async def query_documents(request: QueryRequest, req: Request):
    """Query documents with session-based conversation memory"""
    try:
        # Get or create session ID
        session_id = req.cookies.get("session_id")
        if not session_id:
            session_id = str(uuid.uuid4())
        
        result = await rag_service.query(
            request.question, 
            session_id=session_id,
            top_k=request.top_k
        )
        
        # Set session cookie
        response = JSONResponse(content=result)
        response.set_cookie(
            key="session_id",
            value=session_id,
            max_age=3600,  # 1 hour
            httponly=True
        )
        
        return response
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/conversation/{session_id}")
async def clear_conversation(session_id: str):
    """Clear conversation history for a session"""
    try:
        rag_service.session_manager.clear_session(session_id)
        return {"message": "Conversation cleared", "session_id": session_id}
    except Exception as e:
        logger.error(f"Failed to clear conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/conversation/stats")
async def get_conversation_stats():
    """Get conversation session statistics"""
    try:
        return rag_service.session_manager.get_stats()
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics/memory")
async def memory_metrics():
    """Get memory usage metrics"""
    try:
        import psutil
        process = psutil.Process()
        
        return {
            "memory_used_mb": round(process.memory_info().rss / 1024 / 1024, 2),
            "memory_percent": round(process.memory_percent(), 2),
            "session_stats": rag_service.session_manager.get_stats()
        }
    except Exception as e:
        logger.error(f"Failed to get memory metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

#### 1.5 Update Requirements

**File:** `backend/requirements.txt`

**Add:**
```
psutil==5.9.8  # For memory monitoring
```

### Phase 2: Frontend Changes (Chat UI)

#### 2.1 Update Main Component Structure

**File:** `frontend/index.html` - Query Tab Section

**Current Layout (💬 MAKE A QUERY tab):**
```
1. 💬 Ask Questions (textarea + Ask button)
2. 💡 Answer (single answer display)
3. 📚 Shared Conversation History (collapsible list)
```

**New Layout (💬 MAKE A QUERY tab):**
```
1. 💬 Current Conversation Thread (TOP - scrollable chat history)
   - Shows all Q&A pairs in current session
   - Each answer includes: sources, confidence, execution time
   - Auto-scrolls to latest message
   
2. 💬 Ask Questions (MIDDLE - input area)
   - Textarea for question
   - [Ask] button - continues current conversation
   - [New Chat] button - starts fresh conversation
   
3. 📚 Shared Conversation History (BOTTOM - collapsible)
   - Shows list of past conversations (sessions)
   - Each item expandable to show full Q&A thread
   - Clicking expands to show all questions/answers in that session
```

**Key UI Behaviors:**
- **Ask button**: Adds Q&A to current thread, stays in same tab
- **New Chat button**: 
  - Saves current conversation to history
  - Clears current thread
  - Stays in 💬 MAKE A QUERY tab
  - Ready for fresh question
- **Conversation History items**: 
  - Click to expand/collapse
  - Shows all Q&A pairs when expanded
  - Displays timestamp, question count

#### 2.2 Update HTML Structure

**File:** `frontend/index.html` - Replace Query Tab Content

**New Query Tab HTML:**
```html
<!-- Query Tab -->
<div id="query-tab" class="tab-content">
    
    <!-- Section 1: Current Conversation Thread (TOP) -->
    <div class="section">
        <h3 style="margin-bottom: 15px;">💬 Current Conversation</h3>
        <div id="current-conversation-thread" class="conversation-thread">
            <div class="empty-state" id="empty-conversation-state">
                <p style="text-align: center; color: #999; padding: 40px;">
                    No messages yet. Ask a question to start a conversation!
                </p>
            </div>
            <!-- Messages will be dynamically added here -->
        </div>
    </div>

    <!-- Section 2: Ask Questions (MIDDLE) -->
    <div class="section">
        <h3 style="margin-bottom: 15px;">💬 Ask Questions</h3>
        <div class="query-form">
            <div style="display: flex; gap: 15px; align-items: flex-start;">
                <div style="flex: 8;">
                    <textarea 
                        id="question-input" 
                        placeholder="Ask a question about your documents..." 
                        rows="4"
                        onkeydown="handleQuestionKeyPress(event)">
                    </textarea>
                </div>
                <div style="flex: 2; display: flex; flex-direction: column; gap: 10px;">
                    <button 
                        onclick="askQuestion()" 
                        id="ask-button"
                        style="width: 100%; height: 50%; min-height: 45px; font-size: 1.1em; font-weight: 600;">
                        🔍 Ask
                    </button>
                    <button 
                        onclick="startNewChat()" 
                        id="new-chat-button"
                        class="secondary-btn"
                        style="width: 100%; height: 50%; min-height: 45px; font-size: 1.0em; font-weight: 600;">
                        ✨ New Chat
                    </button>
                </div>
            </div>
            <div id="query-status" class="help-text" style="margin-top: 10px; min-height: 1.5em;">
                <!-- Status messages appear here -->
            </div>
        </div>
    </div>

    <!-- Section 3: Shared Conversation History (BOTTOM) -->
    <div class="section">
        <h3 id="history-main-header">📚 Shared Conversation History</h3>
        <div class="collapsible-section">
            <button onclick="toggleHistory(this)" class="collapsible-trigger">
                ▶ CLICK TO LIST CHAT HISTORY
            </button>
            <div id="conversation-history" class="conversation-history" style="display: none;">
                <!-- Past conversations will be loaded here -->
                <div id="history-list">
                    <!-- Dynamically populated -->
                </div>
            </div>
        </div>
    </div>
</div>
```

#### 2.3 Add CSS Styles

**File:** `frontend/style.css` - Add New Styles

```css
/* ===== Current Conversation Thread Styles ===== */
.conversation-thread {
    max-height: 500px;
    overflow-y: auto;
    padding: 20px;
    background: #f8f9fa;
    border-radius: 8px;
    border: 1px solid #dee2e6;
    scroll-behavior: smooth;
}

.conversation-thread::-webkit-scrollbar {
    width: 8px;
}

.conversation-thread::-webkit-scrollbar-track {
    background: #f1f1f1;
    border-radius: 4px;
}

.conversation-thread::-webkit-scrollbar-thumb {
    background: #888;
    border-radius: 4px;
}

.conversation-thread::-webkit-scrollbar-thumb:hover {
    background: #555;
}

.empty-state {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 200px;
}

/* ===== Message Bubble Styles ===== */
.message-bubble {
    margin-bottom: 20px;
    animation: fadeInUp 0.3s ease-out;
}

@keyframes fadeInUp {
    from {
        opacity: 0;
        transform: translateY(10px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.user-message {
    display: flex;
    justify-content: flex-end;
    margin-bottom: 8px;
}

.user-message .message-content {
    background: #007bff;
    color: white;
    padding: 12px 16px;
    border-radius: 18px 18px 4px 18px;
    max-width: 70%;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.user-message .message-icon {
    font-size: 18px;
    margin-left: 8px;
}

.bot-message {
    display: flex;
    justify-content: flex-start;
    margin-bottom: 8px;
}

.bot-message .message-content {
    background: white;
    color: #333;
    padding: 16px;
    border-radius: 18px 18px 18px 4px;
    max-width: 85%;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    border: 1px solid #e9ecef;
}

.bot-message .message-icon {
    font-size: 18px;
    margin-right: 8px;
}

.message-text {
    line-height: 1.6;
    white-space: pre-wrap;
    word-wrap: break-word;
}

.message-timestamp {
    font-size: 0.75em;
    color: #6c757d;
    margin-top: 4px;
    text-align: right;
}

/* ===== Sources Display in Messages ===== */
.message-sources {
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid #e9ecef;
}

.message-sources h4 {
    font-size: 0.9em;
    color: #495057;
    margin-bottom: 8px;
    font-weight: 600;
}

.source-item {
    padding: 6px 0;
    font-size: 0.85em;
    color: #6c757d;
    display: flex;
    align-items: center;
    gap: 8px;
}

.source-item .source-icon {
    font-size: 14px;
}

.source-confidence {
    background: #e7f3ff;
    color: #0066cc;
    padding: 2px 8px;
    border-radius: 12px;
    font-weight: 600;
    font-size: 0.85em;
}

.message-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 8px;
    font-size: 0.8em;
    color: #6c757d;
}

.execution-time {
    display: flex;
    align-items: center;
    gap: 4px;
}

/* ===== Conversation History Item Styles ===== */
.history-item {
    background: white;
    border: 1px solid #dee2e6;
    border-radius: 8px;
    margin-bottom: 12px;
    overflow: hidden;
    transition: all 0.2s ease;
}

.history-item:hover {
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.history-item-header {
    padding: 16px;
    cursor: pointer;
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: #f8f9fa;
    border-bottom: 1px solid #dee2e6;
}

.history-item-header:hover {
    background: #e9ecef;
}

.history-item-title {
    display: flex;
    align-items: center;
    gap: 12px;
    flex: 1;
}

.history-item-icon {
    font-size: 20px;
}

.history-item-info {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.history-item-preview {
    font-size: 0.95em;
    color: #333;
    font-weight: 500;
}

.history-item-meta {
    font-size: 0.8em;
    color: #6c757d;
    display: flex;
    gap: 12px;
}

.history-item-expand {
    font-size: 1.2em;
    color: #6c757d;
    transition: transform 0.2s ease;
}

.history-item.expanded .history-item-expand {
    transform: rotate(90deg);
}

.history-item-content {
    display: none;
    padding: 16px;
    background: white;
}

.history-item.expanded .history-item-content {
    display: block;
}

.history-qa-pair {
    margin-bottom: 20px;
    padding-bottom: 20px;
    border-bottom: 1px solid #e9ecef;
}

.history-qa-pair:last-child {
    border-bottom: none;
    margin-bottom: 0;
    padding-bottom: 0;
}

.history-question {
    background: #e7f3ff;
    padding: 12px;
    border-radius: 8px;
    margin-bottom: 12px;
    border-left: 4px solid #007bff;
}

.history-question-label {
    font-size: 0.8em;
    color: #0066cc;
    font-weight: 600;
    margin-bottom: 4px;
}

.history-question-text {
    color: #333;
    line-height: 1.5;
}

.history-answer {
    background: #f8f9fa;
    padding: 12px;
    border-radius: 8px;
    border-left: 4px solid #28a745;
}

.history-answer-label {
    font-size: 0.8em;
    color: #28a745;
    font-weight: 600;
    margin-bottom: 4px;
}

.history-answer-text {
    color: #333;
    line-height: 1.6;
    white-space: pre-wrap;
}

/* ===== Button Styles ===== */
#new-chat-button {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border: none;
    transition: all 0.3s ease;
}

#new-chat-button:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

#new-chat-button:disabled {
    background: #6c757d;
    cursor: not-allowed;
    transform: none;
}

/* ===== Loading State ===== */
.message-loading {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px;
    background: white;
    border-radius: 18px;
    max-width: 200px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.typing-indicator {
    display: flex;
    gap: 4px;
}

.typing-dot {
    width: 8px;
    height: 8px;
    background: #6c757d;
    border-radius: 50%;
    animation: typing 1.4s infinite;
}

.typing-dot:nth-child(2) {
    animation-delay: 0.2s;
}

.typing-dot:nth-child(3) {
    animation-delay: 0.4s;
}

@keyframes typing {
    0%, 60%, 100% {
        transform: translateY(0);
        opacity: 0.7;
    }
    30% {
        transform: translateY(-10px);
        opacity: 1;
    }
}

/* ===== Responsive Design ===== */
@media (max-width: 768px) {
    .conversation-thread {
        max-height: 400px;
    }
    
    .user-message .message-content,
    .bot-message .message-content {
        max-width: 90%;
    }
    
    .query-form > div {
        flex-direction: column !important;
    }
    
    .query-form > div > div {
        flex: 1 !important;
        width: 100% !important;
    }
    
    #ask-button,
    #new-chat-button {
        min-height: 50px !important;
    }
}
```

#### 2.4 Add JavaScript Functions

**File:** `frontend/script.js` - Add New Functions

```javascript
// ===== Global State Management =====
let currentConversation = [];  // Current active conversation thread
let conversationHistory = [];  // All past conversations
let currentSessionId = null;   // Current session ID

// ===== Initialize Session =====
function initializeSession() {
    // Get or create session ID
    currentSessionId = sessionStorage.getItem('currentSessionId');
    if (!currentSessionId) {
        currentSessionId = generateSessionId();
        sessionStorage.setItem('currentSessionId', currentSessionId);
    }
    
    // Load conversation history
    loadConversationHistory();
}

function generateSessionId() {
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

// ===== Ask Question Function (Updated) =====
async function askQuestion() {
    const questionInput = document.getElementById('question-input');
    const question = questionInput.value.trim();
    
    if (!question) {
        showQueryStatus('Please enter a question', 'error');
        return;
    }
    
    // Disable input during processing
    questionInput.disabled = true;
    document.getElementById('ask-button').disabled = true;
    document.getElementById('new-chat-button').disabled = true;
    
    // Hide empty state if visible
    const emptyState = document.getElementById('empty-conversation-state');
    if (emptyState) {
        emptyState.style.display = 'none';
    }
    
    // Add user message to thread
    addMessageToThread({
        type: 'user',
        text: question,
        timestamp: new Date().toISOString()
    });
    
    // Clear input
    questionInput.value = '';
    
    // Show loading indicator
    const loadingId = addLoadingMessage();
    
    try {
        const response = await fetch(`${API_BASE_URL}/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',  // Important for session cookies
            body: JSON.stringify({
                question: question,
                top_k: 5
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Remove loading indicator
        removeLoadingMessage(loadingId);
        
        // Add bot response to thread
        addMessageToThread({
            type: 'bot',
            text: data.answer,
            sources: data.sources || [],
            executionTime: data.processing_time,
            timestamp: new Date().toISOString()
        });
        
        // Save to current conversation
        currentConversation.push({
            question: question,
            answer: data.answer,
            sources: data.sources || [],
            executionTime: data.processing_time,
            timestamp: new Date().toISOString()
        });
        
        showQueryStatus('Question answered successfully!', 'success');
        
    } catch (error) {
        console.error('Query error:', error);
        removeLoadingMessage(loadingId);
        showQueryStatus('Error: ' + error.message, 'error');
        
        // Add error message to thread
        addMessageToThread({
            type: 'bot',
            text: 'Sorry, I encountered an error processing your question. Please try again.',
            timestamp: new Date().toISOString(),
            isError: true
        });
    } finally {
        // Re-enable input
        questionInput.disabled = false;
        document.getElementById('ask-button').disabled = false;
        document.getElementById('new-chat-button').disabled = false;
        questionInput.focus();
    }
}

// ===== Add Message to Thread =====
function addMessageToThread(message) {
    const thread = document.getElementById('current-conversation-thread');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message-bubble';
    
    if (message.type === 'user') {
        messageDiv.innerHTML = `
            <div class="user-message">
                <div class="message-content">
                    <div class="message-text">${escapeHtml(message.text)}</div>
                    <div class="message-timestamp">${formatTime(message.timestamp)}</div>
                </div>
                <span class="message-icon">👤</span>
            </div>
        `;
    } else {
        const sourcesHtml = message.sources && message.sources.length > 0 ? `
            <div class="message-sources">
                <h4>📚 Sources:</h4>
                ${message.sources.map(source => `
                    <div class="source-item">
                        <span class="source-icon">📄</span>
                        <span>${escapeHtml(source.title)}</span>
                        <span class="source-confidence">${(source.score * 100).toFixed(1)}%</span>
                    </div>
                `).join('')}
            </div>
        ` : '';
        
        const footerHtml = message.executionTime ? `
            <div class="message-footer">
                <div class="execution-time">
                    <span>⏱️</span>
                    <span>${message.executionTime.toFixed(2)}s</span>
                </div>
                <div class="message-timestamp">${formatTime(message.timestamp)}</div>
            </div>
        ` : `<div class="message-timestamp">${formatTime(message.timestamp)}</div>`;
        
        messageDiv.innerHTML = `
            <div class="bot-message">
                <span class="message-icon">🤖</span>
                <div class="message-content ${message.isError ? 'error-message' : ''}">
                    <div class="message-text">${escapeHtml(message.text)}</div>
                    ${sourcesHtml}
                    ${footerHtml}
                </div>
            </div>
        `;
    }
    
    thread.appendChild(messageDiv);
    
    // Scroll to bottom
    thread.scrollTop = thread.scrollHeight;
}

// ===== Loading Message =====
function addLoadingMessage() {
    const thread = document.getElementById('current-conversation-thread');
    const loadingDiv = document.createElement('div');
    const loadingId = 'loading_' + Date.now();
    loadingDiv.id = loadingId;
    loadingDiv.className = 'message-bubble';
    loadingDiv.innerHTML = `
        <div class="bot-message">
            <span class="message-icon">🤖</span>
            <div class="message-loading">
                <div class="typing-indicator">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
                <span>Thinking...</span>
            </div>
        </div>
    `;
    thread.appendChild(loadingDiv);
    thread.scrollTop = thread.scrollHeight;
    return loadingId;
}

function removeLoadingMessage(loadingId) {
    const loadingDiv = document.getElementById(loadingId);
    if (loadingDiv) {
        loadingDiv.remove();
    }
}

// ===== Start New Chat =====
async function startNewChat() {
    if (currentConversation.length === 0) {
        showQueryStatus('No conversation to save', 'info');
        return;
    }
    
    if (!confirm('Start a new conversation? Current conversation will be saved to history.')) {
        return;
    }
    
    // Save current conversation to history
    const conversationSummary = {
        id: currentSessionId,
        timestamp: new Date().toISOString(),
        messages: currentConversation,
        preview: currentConversation[0].question.substring(0, 100) + '...',
        messageCount: currentConversation.length
    };
    
    conversationHistory.unshift(conversationSummary);
    saveConversationHistory();
    
    // Clear current conversation
    currentConversation = [];
    currentSessionId = generateSessionId();
    sessionStorage.setItem('currentSessionId', currentSessionId);
    
    // Clear thread UI
    const thread = document.getElementById('current-conversation-thread');
    thread.innerHTML = `
        <div class="empty-state" id="empty-conversation-state">
            <p style="text-align: center; color: #999; padding: 40px;">
                No messages yet. Ask a question to start a conversation!
            </p>
        </div>
    `;
    
    // Clear backend session
    try {
        await fetch(`${API_BASE_URL}/conversation/${currentSessionId}`, {
            method: 'DELETE',
            credentials: 'include'
        });
    } catch (error) {
        console.error('Error clearing backend session:', error);
    }
    
    // Update history display
    updateConversationHistoryCount();
    renderConversationHistory();
    
    showQueryStatus('New conversation started!', 'success');
    
    // Focus on input
    document.getElementById('question-input').focus();
}

// ===== Conversation History Management =====
function saveConversationHistory() {
    try {
        localStorage.setItem('conversationHistory', JSON.stringify(conversationHistory));
    } catch (error) {
        console.error('Error saving conversation history:', error);
    }
}

function loadConversationHistory() {
    try {
        const saved = localStorage.getItem('conversationHistory');
        if (saved) {
            conversationHistory = JSON.parse(saved);
            updateConversationHistoryCount();
        }
    } catch (error) {
        console.error('Error loading conversation history:', error);
        conversationHistory = [];
    }
}

function updateConversationHistoryCount() {
    const header = document.getElementById('history-main-header');
    if (header) {
        const count = conversationHistory.length;
        header.textContent = count > 0 
            ? `📚 Shared Conversation History (${count} conversation${count !== 1 ? 's' : ''})`
            : '📚 Shared Conversation History';
    }
}

function renderConversationHistory() {
    const historyList = document.getElementById('history-list');
    if (!historyList) return;
    
    if (conversationHistory.length === 0) {
        historyList.innerHTML = '<p style="text-align: center; color: #999; padding: 20px;">No conversation history yet.</p>';
        return;
    }
    
    historyList.innerHTML = conversationHistory.map((conv, index) => `
        <div class="history-item" id="history-item-${index}">
            <div class="history-item-header" onclick="toggleHistoryItem(${index})">
                <div class="history-item-title">
                    <span class="history-item-icon">💬</span>
                    <div class="history-item-info">
                        <div class="history-item-preview">${escapeHtml(conv.preview)}</div>
                        <div class="history-item-meta">
                            <span>📅 ${formatDate(conv.timestamp)}</span>
                            <span>💬 ${conv.messageCount} message${conv.messageCount !== 1 ? 's' : ''}</span>
                        </div>
                    </div>
                </div>
                <span class="history-item-expand">▶</span>
            </div>
            <div class="history-item-content">
                ${conv.messages.map((msg, msgIndex) => `
                    <div class="history-qa-pair">
                        <div class="history-question">
                            <div class="history-question-label">Question ${msgIndex + 1}:</div>
                            <div class="history-question-text">${escapeHtml(msg.question)}</div>
                        </div>
                        <div class="history-answer">
                            <div class="history-answer-label">Answer:</div>
                            <div class="history-answer-text">${escapeHtml(msg.answer)}</div>
                            ${msg.sources && msg.sources.length > 0 ? `
                                <div class="message-sources" style="margin-top: 12px;">
                                    <h4>📚 Sources:</h4>
                                    ${msg.sources.map(source => `
                                        <div class="source-item">
                                            <span>📄 ${escapeHtml(source.title)}</span>
                                            <span class="source-confidence">${(source.score * 100).toFixed(1)}%</span>
                                        </div>
                                    `).join('')}
                                </div>
                            ` : ''}
                            ${msg.executionTime ? `
                                <div style="margin-top: 8px; font-size: 0.85em; color: #6c757d;">
                                    ⏱️ ${msg.executionTime.toFixed(2)}s
                                </div>
                            ` : ''}
                        </div>
                    </div>
                `).join('')}
            </div>
        </div>
    `).join('');
}

function toggleHistoryItem(index) {
    const item = document.getElementById(`history-item-${index}`);
    if (item) {
        item.classList.toggle('expanded');
    }
}

// ===== Utility Functions =====
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatTime(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', { 
        hour: '2-digit', 
        minute: '2-digit'
    });
}

function formatDate(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diffDays = Math.floor((now - date) / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) {
        return 'Today ' + date.toLocaleTimeString('en-US', { 
            hour: '2-digit', 
            minute: '2-digit'
        });
    } else if (diffDays === 1) {
        return 'Yesterday ' + date.toLocaleTimeString('en-US', { 
            hour: '2-digit', 
            minute: '2-digit'
        });
    } else {
        return date.toLocaleDateString('en-US', { 
            month: 'short', 
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }
}

function showQueryStatus(message, type = 'info') {
    const statusDiv = document.getElementById('query-status');
    if (!statusDiv) return;
    
    const colors = {
        success: '#28a745',
        error: '#dc3545',
        info: '#17a2b8'
    };
    
    statusDiv.textContent = message;
    statusDiv.style.color = colors[type] || colors.info;
    
    // Clear after 5 seconds
    setTimeout(() => {
        statusDiv.textContent = '';
    }, 5000);
}

function handleQuestionKeyPress(event) {
    // Submit on Ctrl+Enter or Cmd+Enter
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
        event.preventDefault();
        askQuestion();
    }
}

// ===== Update initializeApp Function =====
// Add to existing initializeApp() function:
function initializeApp() {
    try {
        checkAPIHealth();
        refreshVectorStats();
        loadDocumentCount();
        loadConversationCount();
        
        // Initialize session and conversation history
        initializeSession();
        renderConversationHistory();
        
    } catch (error) {
        console.error('Initialization error:', error);
        document.getElementById('session-info').textContent = 'Session: Initialization error - check console';
    }
}
```

#### 2.4 Add Chat Styles

**File:** `frontend/src/components/ChatMessage.css` (NEW FILE)

```css
.chat-message {
  margin: 16px 0;
  display: flex;
  flex-direction: column;
  animation: fadeIn 0.3s ease-in;
}

.user-message {
  align-items: flex-end;
}

.bot-message {
  align-items: flex-start;
}

.message-content {
  max-width: 80%;
  padding: 12px 16px;
  border-radius: 12px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.user-message .message-content {
  background: #007bff;
  color: white;
}

.bot-message .message-content {
  background: #f1f3f4;
  color: #333;
}

.message-icon {
  font-size: 20px;
  margin-right: 8px;
}

.sources-section {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #ddd;
  font-size: 0.9em;
}

.source-item {
  padding: 4px 0;
  color: #666;
}

.execution-time {
  margin-top: 8px;
  font-size: 0.85em;
  color: #888;
}

.message-timestamp {
  font-size: 0.75em;
  color: #999;
  margin-top: 4px;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
```

#### 2.5 Update Chat Container

**File:** `frontend/src/App.css`

**Add:**
```css
.chat-container {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 200px);
  max-width: 900px;
  margin: 0 auto;
}

.chat-history {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  scroll-behavior: smooth;
}

.chat-input-area {
  position: sticky;
  bottom: 0;
  background: white;
  padding: 16px;
  border-top: 1px solid #ddd;
  box-shadow: 0 -2px 8px rgba(0,0,0,0.1);
}

.input-controls {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}

.clear-button {
  background: #dc3545;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
}

.clear-button:hover {
  background: #c82333;
}
```

### Phase 3: Configuration Updates

#### 3.1 Update Backend Deployment

**File:** `k8s/backend-deployment.yaml`

**Add environment variables:**
```yaml
env:
  # ... existing env vars ...
  - name: SESSION_TIMEOUT_MINUTES
    value: "60"
  - name: MAX_CONVERSATION_TURNS
    value: "20"
  - name: MAX_CONCURRENT_SESSIONS
    value: "100"
```

**Resource limits remain the same:**
```yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "250m"
  limits:
    memory: "1Gi"
    cpu: "500m"
```

### Phase 4: Testing Plan

#### 4.1 Backend Testing

**Test Session Management:**
```bash
# Test 1: Create session and ask questions
curl -c cookies.txt -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is S3?"}'

# Test 2: Follow-up question (should use context)
curl -b cookies.txt -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "How do I secure it?"}'

# Test 3: Check session stats
curl http://localhost:8000/api/conversation/stats

# Test 4: Check memory usage
curl http://localhost:8000/api/metrics/memory

# Test 5: Clear conversation
curl -b cookies.txt -X DELETE http://localhost:8000/api/conversation/clear
```

#### 4.2 Frontend Testing

**Manual Tests:**
1. Ask initial question → Verify appears in chat
2. Ask follow-up → Verify context awareness
3. Scroll through history → Verify all messages visible
4. Clear conversation → Verify history cleared
5. Refresh page → Verify session persists (cookie-based)
6. Wait 1 hour → Verify session expires

#### 4.3 Load Testing

**Simulate Multiple Users:**
```bash
# Use Apache Bench or similar
ab -n 100 -c 10 -p query.json -T application/json \
  http://localhost:8000/api/query
```

**Monitor Memory:**
```bash
# Watch memory usage during load test
watch -n 1 'curl -s http://localhost:8000/api/metrics/memory | jq'
```

### Phase 5: Deployment Strategy

#### 5.1 Pre-Deployment Checklist

- [ ] Tag current working images as v1.0-stable
- [ ] Build new images with chat history feature
- [ ] Test locally with Docker Compose
- [ ] Test backend session management
- [ ] Test frontend chat UI
- [ ] Verify memory usage under load
- [ ] Update documentation

#### 5.2 Deployment Steps

```bash
# 1. Build and tag new images
cd backend
docker build -t rag-backend-langchain:v1.1-chat .
docker tag rag-backend-langchain:v1.1-chat \
  615299759525.dkr.ecr.ap-southeast-2.amazonaws.com/rag-backend-langchain:v1.1-chat
docker push 615299759525.dkr.ecr.ap-southeast-2.amazonaws.com/rag-backend-langchain:v1.1-chat

cd ../frontend
docker build -t rag-frontend-langchain:v1.1-chat .
docker tag rag-frontend-langchain:v1.1-chat \
  615299759525.dkr.ecr.ap-southeast-2.amazonaws.com/rag-frontend-langchain:v1.1-chat
docker push 615299759525.dkr.ecr.ap-southeast-2.amazonaws.com/rag-frontend-langchain:v1.1-chat

# 2. Update deployments
kubectl set image deployment/rag-backend-langchain \
  backend=615299759525.dkr.ecr.ap-southeast-2.amazonaws.com/rag-backend-langchain:v1.1-chat \
  -n langchain

kubectl set image deployment/rag-frontend-langchain \
  frontend=615299759525.dkr.ecr.ap-southeast-2.amazonaws.com/rag-frontend-langchain:v1.1-chat \
  -n langchain

# 3. Monitor rollout
kubectl rollout status deployment/rag-backend-langchain -n langchain
kubectl rollout status deployment/rag-frontend-langchain -n langchain

# 4. Verify functionality
kubectl port-forward -n langchain svc/rag-frontend-service 8080:80
# Test in browser: http://localhost:8080
```

#### 5.3 Rollback Plan

**If issues occur:**
```bash
# Rollback to stable version
kubectl set image deployment/rag-backend-langchain \
  backend=615299759525.dkr.ecr.ap-southeast-2.amazonaws.com/rag-backend-langchain:v1.0-stable \
  -n langchain

kubectl set image deployment/rag-frontend-langchain \
  frontend=615299759525.dkr.ecr.ap-southeast-2.amazonaws.com/rag-frontend-langchain:v1.0-stable \
  -n langchain
```

### Phase 6: Monitoring & Maintenance

#### 6.1 Add Monitoring Dashboard

**Metrics to Track:**
- Active sessions count
- Average conversation length (turns)
- Memory usage per session
- Session timeout rate
- Query response time

**Grafana Dashboard Queries:**
```promql
# Active sessions
sum(rag_active_sessions)

# Memory usage
container_memory_usage_bytes{pod=~"rag-backend.*"}

# Session duration
histogram_quantile(0.95, rate(rag_session_duration_seconds_bucket[5m]))
```

#### 6.2 Alerting Rules

**Set up alerts for:**
- Memory usage > 800MB (80% of limit)
- Active sessions > 80
- Session cleanup failures
- Query failures > 5% rate

### Phase 7: Documentation Updates

#### 7.1 Update README.md

**Add section:**
```markdown
## Conversation Features

The system now supports ChatGPT-style consecutive conversations:

- **Context Awareness**: Follow-up questions understand previous context
- **Session Management**: Conversations persist for 1 hour
- **Memory Limits**: Last 20 turns kept per conversation
- **Clear History**: Button to start fresh conversation

### Usage Example

```
User: "What is Amazon S3?"
Bot: [Detailed S3 explanation]

User: "How do I secure it?"  ← Understands "it" = S3
Bot: [S3 security best practices]

User: "What about encryption?"  ← Knows context is S3 security
Bot: [S3 encryption options]
```
```

#### 7.2 Update API Documentation

**Add to API docs:**
```markdown
### Session Management

**POST /api/query**
- Automatically creates/uses session via cookies
- Maintains conversation context
- Returns: answer, sources, execution_time

**DELETE /api/conversation/clear**
- Clears current session history
- Requires session cookie

**GET /api/conversation/stats**
- Returns active session statistics
- No authentication required

**GET /api/metrics/memory**
- Returns memory usage metrics
- Includes session statistics
```

## Summary

### Changes Required

**Backend (Minimal):**
- ✅ Add SessionMemoryManager class
- ✅ Update query method to use session memory
- ✅ Add 3 new API endpoints (clear, stats, metrics)
- ✅ Add psutil dependency
- ✅ Update environment variables

**Frontend (Moderate - Specific to Current Layout):**
- ✅ Reorganize 💬 MAKE A QUERY tab layout:
  - Move Answer section to TOP (becomes conversation thread)
  - Keep Ask Questions in MIDDLE (add New Chat button)
  - Keep Shared Conversation History at BOTTOM (enhance expandability)
- ✅ Add conversation thread UI with message bubbles
- ✅ Add sources, confidence, execution time to each message
- ✅ Implement New Chat button functionality
- ✅ Enhance history items to show full Q&A when expanded
- ✅ Add CSS styles for chat bubbles and history items
- ✅ Add JavaScript functions for:
  - Session management
  - Message rendering
  - Conversation saving/loading
  - History expansion
- ✅ Maintain current tab structure (no navigation changes)

**Infrastructure (None):**
- ✅ No resource limit changes needed
- ✅ No new services required
- ✅ Existing 1Gi memory is sufficient

### UI Flow

**User Experience:**
1. User opens 💬 MAKE A QUERY tab
2. Sees empty conversation thread at top
3. Types question in middle section
4. Clicks **Ask** button
   - Question appears in thread (right side, blue bubble)
   - Answer appears in thread (left side, white bubble with sources)
   - Thread auto-scrolls to latest message
5. User asks follow-up question
   - Continues in same thread
   - Context maintained automatically
6. User clicks **New Chat** button
   - Current conversation saved to history
   - Thread cleared
   - Ready for fresh conversation
   - Stays in same tab
7. User expands history item at bottom
   - Shows all Q&A pairs from that conversation
   - Each pair shows question, answer, sources, confidence, time

### Key Features

**Current Conversation Thread:**
- Scrollable area (max 500px height)
- User messages: right-aligned, blue bubbles
- Bot messages: left-aligned, white bubbles
- Each bot message shows:
  - Answer text
  - Sources with confidence percentages
  - Execution time
  - Timestamp
- Auto-scroll to latest message
- Empty state when no messages

**Ask Questions Section:**
- Textarea for input
- **Ask** button: continues conversation
- **New Chat** button: starts fresh (saves current to history)
- Status messages below input
- Keyboard shortcut: Ctrl+Enter to submit

**Shared Conversation History:**
- Collapsible section (existing behavior)
- List of past conversations
- Each item shows:
  - Preview of first question
  - Date/time
  - Message count
- Click to expand/collapse
- When expanded, shows:
  - All Q&A pairs in sequence
  - Full question and answer text
  - Sources with confidence
  - Execution time for each answer
- Stored in localStorage (persists across sessions)

### Estimated Effort

- Backend changes: 2-3 hours
- Frontend HTML structure: 1-2 hours
- Frontend CSS styling: 2-3 hours
- Frontend JavaScript logic: 3-4 hours
- Testing: 2-3 hours
- Documentation: 1-2 hours
- **Total: 1.5-2 days**

### Risk Assessment

**Low Risk:**
- Backend changes are additive (no breaking changes)
- Frontend changes maintain existing tab structure
- Easy rollback via Docker tags
- Memory requirements well within limits
- No navigation changes (stays in same tab)

**Mitigation:**
- Tag stable version before changes (v1.0-stable)
- Test thoroughly in local environment
- Deploy during low-usage period
- Monitor memory metrics closely
- Keep rollback plan ready

## Next Steps

1. **Backup current version** (tag as v1.0-stable)
2. **Implement backend changes** (session management)
3. **Implement frontend changes** (chat UI)
4. **Test locally** (Docker Compose)
5. **Deploy to staging** (if available)
6. **Deploy to production** (with monitoring)
7. **Update documentation**
8. **Monitor for 24 hours**

## Questions?

- Memory concerns? → Current 1Gi limit handles 1000+ long conversations
- Session persistence? → Cookie-based, 1-hour timeout
- Rollback plan? → Docker image tags enable instant rollback
- Performance impact? → Minimal, text is lightweight
