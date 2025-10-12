const API_BASE_URL = window.location.origin + '/api';
const ACCESS_CODE = 'cloudteam';

// ===== Global State Management =====
let currentConversation = [];  // Current active conversation thread
let conversationHistory = [];  // All past conversations
let currentSessionId = null;   // Current session ID

document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, checking authentication...');
    
    // Check if session is authenticated
    if (!sessionStorage.getItem('authenticated')) {
        showAccessModal();
        return;
    }
    
    // Initialize app if authenticated
    initializeApp();
});

function showAccessModal() {
    const overlay = document.createElement('div');
    overlay.id = 'access-modal';
    overlay.style.cssText = `
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        width: 100vw !important;
        height: 100vh !important;
        background: rgba(0, 0, 0, 0.8) !important;
        z-index: 99999 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    `;
    
    overlay.innerHTML = `
        <div style="background: white; border-radius: 12px; padding: 30px; max-width: 400px; width: 90%; text-align: center; box-shadow: 0 20px 40px rgba(0,0,0,0.3);">
            <div style="font-size: 1.5em; margin-bottom: 20px; color: #333;">🔒 Access Required</div>
            <div style="margin-bottom: 20px; color: #666;">Enter access code to continue:</div>
            <input type="password" id="access-code-input" placeholder="Access Code" style="width: 100%; padding: 12px; border: 2px solid #ddd; border-radius: 6px; font-size: 16px; margin-bottom: 20px; text-align: center;">
            <div id="access-error" style="color: red; margin-bottom: 15px; min-height: 20px;"></div>
            <button onclick="checkAccessCode()" style="background: #007bff; color: white; border: none; padding: 12px 30px; border-radius: 6px; font-size: 16px; cursor: pointer; width: 100%;">Submit</button>
        </div>
    `;
    
    document.body.appendChild(overlay);
    
    // Focus on input
    setTimeout(() => {
        document.getElementById('access-code-input').focus();
    }, 100);
    
    // Handle Enter key
    document.getElementById('access-code-input').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            checkAccessCode();
        }
    });
}

function checkAccessCode() {
    const input = document.getElementById('access-code-input');
    const error = document.getElementById('access-error');
    const code = input.value.trim();
    
    if (code === ACCESS_CODE) {
        sessionStorage.setItem('authenticated', 'true');
        document.getElementById('access-modal').remove();
        initializeApp();
    } else {
        error.textContent = 'Invalid access code. Please try again.';
        input.value = '';
        input.focus();
    }
}

function initializeApp() {
    try {
        initializeSession();
        checkAPIHealth();
        refreshVectorStats();
        loadDocumentCount();
        loadConversationCount();
    } catch (error) {
        console.error('Initialization error:', error);
        document.getElementById('session-info').textContent = 'Session: Initialization error - check console';
    }
}

// ===== Initialize Session =====
function initializeSession() {
    // Get or create session ID
    currentSessionId = sessionStorage.getItem('currentSessionId');
    if (!currentSessionId) {
        currentSessionId = generateSessionId();
        sessionStorage.setItem('currentSessionId', currentSessionId);
    }
    console.log('Session initialized:', currentSessionId);
}

function generateSessionId() {
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

async function loadDocumentCount() {
    try {
        const response = await fetch(`${API_BASE_URL}/documents`);
        if (response.ok) {
            const data = await response.json();
            const count = data.documents ? data.documents.length : 0;
            const mainHeader = document.getElementById('documents-main-header');
            if (mainHeader) {
                mainHeader.textContent = count > 0 ? `📚 Available Documents (${count})` : '📚 Available Documents';
            }
        }
    } catch (error) {
        console.error('Error loading document count:', error);
    }
}

async function loadConversationCount() {
    try {
        const response = await fetch(`${API_BASE_URL}/conversation-history`);
        if (response.ok) {
            const data = await response.json();
            const count = data.history ? data.history.length : 0;
            const mainHeader = document.getElementById('history-main-header');
            if (mainHeader) {
                mainHeader.textContent = count > 0 ? `📚 Shared Conversation History (${count} conversations)` : '📚 Shared Conversation History';
            }
        }
    } catch (error) {
        console.error('Error loading conversation count:', error);
    }
}

async function checkAPIHealth() {
    try {
        const response = await fetch(`${API_BASE_URL}/`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const data = await response.json();
        document.getElementById('weaviate-status').textContent = data.weaviate_status ? '✅ Connected' : '❌ Disconnected';
        document.getElementById('s3-status').textContent = data.s3_status ? '✅ Connected' : '❌ Disconnected';
        document.getElementById('bedrock-status').textContent = data.bedrock_status ? '✅ Connected' : '❌ Disconnected';
        document.getElementById('session-status').innerHTML = `✅ ${data.session_id}`;
        document.getElementById('document-count').textContent = (await getDocumentCount()) || '0';
        const queryButton = document.querySelector('#query-tab button[onclick="askQuestion()"]');
        if (queryButton) {
            queryButton.disabled = !(data.weaviate_status && data.bedrock_status);
            queryButton.title = queryButton.disabled ? 'Some services are unavailable. Please wait...' : '';
        }
    } catch (error) {
        console.error('API Health Check Failed:', error);
        ['weaviate-status', 's3-status', 'bedrock-status', 'session-status'].forEach(id => {
            document.getElementById(id).textContent = '❌ Error';
        });
        const queryButton = document.querySelector('#query-tab button[onclick="askQuestion()"]');
        if (queryButton) {
            queryButton.disabled = true;
            queryButton.title = 'API connection error';
        }
    }
}

function showTab(event, tabName) {
    document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
    document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
    document.getElementById(`${tabName}-tab`).classList.add('active');
    event.target.classList.add('active');
}

async function uploadFile() {
    const fileInput = document.getElementById('file-upload');
    const file = fileInput.files[0];
    if (!file) return;

    const statusDiv = document.getElementById('document-action-status');
    const originalContent = '<strong>Supported formats:</strong> PDF, Word (.docx), Excel (.xlsx), PowerPoint (.pptx), CSV, Text (.txt), Markdown (.md)';
    statusDiv.innerHTML = `<p style="color: #007bff;"><i>Uploading ${file.name}...</i></p>`;

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch(`${API_BASE_URL}/documents/upload`, { method: 'POST', body: formData });
        if (!response.ok) throw new Error(`Upload failed: ${response.status}`);
        const result = await response.json();
        statusDiv.innerHTML = `<p style="color: green;">✅ ${result.message}</p>`;
        await refreshDocuments();
        await refreshVectorStats();
        await loadDocumentCount();
    } catch (error) {
        statusDiv.innerHTML = `<p style="color: red;">❌ Upload failed: ${error.message}</p>`;
    } finally {
        fileInput.value = '';
        setTimeout(() => { statusDiv.innerHTML = originalContent; }, 3000);
    }
}

async function processDocuments() {
    const statusDiv = document.getElementById('document-action-status');
    const originalContent = '<strong>Supported formats:</strong> PDF, Word (.docx), Excel (.xlsx), PowerPoint (.pptx), CSV, Text (.txt), Markdown (.md)';
    statusDiv.innerHTML = `<p style="color: #007bff;"><i>Processing documents into vector database...</i></p>`;

    try {
        const response = await fetch(`${API_BASE_URL}/documents/auto-index`, { method: 'POST' });
        if (!response.ok) throw new Error(`Processing failed: ${response.status}`);
        const result = await response.json();
        statusDiv.innerHTML = `<p style="color: green;">✅ ${result.message}</p>`;
        await refreshVectorStats();
    } catch (error) {
        statusDiv.innerHTML = `<p style="color: red;">❌ Processing failed: ${error.message}</p>`;
    } finally {
        setTimeout(() => { statusDiv.innerHTML = originalContent; }, 3000);
    }
}

async function refreshDocuments() {
    const statusDiv = document.getElementById('document-action-status');
    const originalContent = '<strong>Supported formats:</strong> PDF, Word (.docx), Excel (.xlsx), PowerPoint (.pptx), CSV, Text (.txt), Markdown (.md)';
    statusDiv.innerHTML = `<p style="color: #007bff;"><i>Refreshing document list...</i></p>`;
    
    const documentsList = document.getElementById('documents-list');
    documentsList.innerHTML = '<p style="color: orange;">Loading documents...</p>';
    
    try {
        const response = await fetch(`${API_BASE_URL}/documents`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        const data = await response.json();
        displayDocuments(data.documents || []);
        document.getElementById('document-count').textContent = data.documents ? data.documents.length : 0;
        statusDiv.innerHTML = `<p style="color: green;">✅ Document list refreshed (${data.documents ? data.documents.length : 0} documents)</p>`;
    } catch (error) {
        console.error('Error loading documents:', error);
        statusDiv.innerHTML = `<p style="color: red;">❌ Refresh failed: ${error.message}</p>`;
        documentsList.innerHTML = `
            <div style="color: red; padding: 15px; border: 1px solid #f44336; border-radius: 5px; background-color: #ffebee;">
                <strong>❌ Error loading documents:</strong> ${error.message}
                <br><br>
                <button onclick="refreshDocuments()" style="background-color: #f44336; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer;">
                    🔄 Retry
                </button>
            </div>
        `;
    } finally {
        setTimeout(() => { statusDiv.innerHTML = originalContent; }, 3000);
    }
}

function displayDocuments(documents) {
    const documentsList = document.getElementById('documents-list');
    const mainHeader = document.getElementById('documents-main-header');
    
    if (documents.length === 0) {
        documentsList.innerHTML = `
            <div style="text-align: center; padding: 20px; color: #666;">
                <p style="font-size: 16px;">📁 No documents uploaded yet</p>
                <p>Upload some documents to get started with Q&A!</p>
            </div>
        `;
        if(mainHeader) mainHeader.textContent = '📚 Available Documents';
        return;
    }

    // Update header with count
    if(mainHeader) mainHeader.textContent = `📚 Available Documents (${documents.length})`;

    const documentsHtml = documents.map(doc => `
        <div style="border: 1px solid #ddd; padding: 15px; margin: 10px 0; background-color: #fafafa; border-radius: 5px; position: relative;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div style="flex-grow: 1;">
                    <div style="font-weight: bold; color: #333; margin-bottom: 5px;">${doc.filename}</div>
                    <div style="font-size: 12px; color: #666; margin-bottom: 5px;">
                        <strong>Size:</strong> ${formatFileSize(doc.size)} | 
                        <strong>Modified:</strong> ${new Date(doc.last_modified).toLocaleString()} | 
                        <strong>Uploaded by:</strong> ${doc.uploaded_by || 'unknown'}
                    </div>
                    <div style="font-size: 12px; color: #666; margin-bottom: 5px;">
                        <strong>S3 Key:</strong> 
                        <a href="#" onclick="downloadDocument('${doc.filename}')" style="color: #007bff; text-decoration: none; cursor: pointer;" title="Click to download">
                            ${doc.key || `documents/${doc.filename}`}
                        </a>
                    </div>
                </div>
                <div style="margin-left: 15px;">
                    <button onclick="deleteDocument('${doc.filename}')" style="background-color: #dc3545; color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 12px;">
                        🗑️ Delete
                    </button>
                </div>
            </div>
        </div>
    `).join('');
    documentsList.innerHTML = documentsHtml;
}

async function downloadDocument(filename) {
    try {
        showToast('Generating download link...', 'info');
        const response = await fetch(`${API_BASE_URL}/documents/${encodeURIComponent(filename)}/download`);
        if (!response.ok) {
            throw new Error(`Download failed: ${response.status}`);
        }
        const data = await response.json();
        
        // Open download link in new tab
        window.open(data.download_url, '_blank');
        showToast('Download started!', 'success');
    } catch (error) {
        console.error('Download error:', error);
        showToast(`Download failed: ${error.message}`, 'error');
    }
}

// Modern Modal Functions
function showDeleteModal(filename, onConfirm) {
    // Prevent multiple modals
    const existingModal = document.querySelector('.modal-overlay');
    if (existingModal) {
        existingModal.remove();
    }
    
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.style.cssText = `
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        width: 100vw !important;
        height: 100vh !important;
        background: rgba(0, 0, 0, 0.5) !important;
        z-index: 9999 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        opacity: 0;
        transition: opacity 0.3s ease;
    `;
    overlay.innerHTML = `
        <div class="modal-dialog">
            <div class="modal-header">
                <span class="icon">🗑️</span>
                Delete Document
            </div>
            <div class="modal-body">
                Are you sure you want to delete <span class="modal-filename">${filename}</span>?
                <div class="modal-warning">This action cannot be undone.</div>
            </div>
            <div class="modal-footer">
                <button class="modal-btn modal-btn-cancel" onclick="closeModal()">Cancel</button>
                <button class="modal-btn modal-btn-delete" onclick="confirmDelete()">Delete</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(overlay);
    
    // Force reflow and show with animation
    overlay.offsetHeight;
    overlay.style.opacity = '1';
    
    // Close on ESC key
    const handleEsc = (e) => {
        if (e.key === 'Escape') {
            closeModal();
        }
    };
    document.addEventListener('keydown', handleEsc);
    
    // Close on backdrop click
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) closeModal();
    });
    
    // Store functions globally for onclick handlers
    window.closeModal = () => {
        overlay.classList.remove('show');
        setTimeout(() => {
            if (overlay.parentNode) {
                document.body.removeChild(overlay);
            }
            delete window.closeModal;
            delete window.confirmDelete;
        }, 300);
        document.removeEventListener('keydown', handleEsc);
    };
    
    window.confirmDelete = () => {
        closeModal();
        onConfirm();
    };
}

function showToast(message, type = 'success') {
    const statusDiv = document.getElementById('document-action-status');
    const originalContent = '<strong>Supported formats:</strong> PDF, Word (.docx), Excel (.xlsx), PowerPoint (.pptx), CSV, Text (.txt), Markdown (.md)';
    
    let color, icon;
    switch(type) {
        case 'success': color = 'green'; icon = '✅'; break;
        case 'error': color = 'red'; icon = '❌'; break;
        case 'info': color = '#007bff'; icon = 'ℹ️'; break;
        default: color = 'green'; icon = '✅';
    }
    
    statusDiv.innerHTML = `<p style="color: ${color};">${icon} ${message}</p>`;
    setTimeout(() => { statusDiv.innerHTML = originalContent; }, 3000);
}

async function deleteDocument(filename) {
    showDeleteModal(filename, async () => {
        showLoading('Deleting document...');
        try {
            const response = await fetch(`${API_BASE_URL}/documents/${encodeURIComponent(filename)}`, {
                method: 'DELETE'
            });
            if (!response.ok) {
                throw new Error(`Delete failed: ${response.status}`);
            }
            const result = await response.json();
            showToast(`Document deleted successfully: ${result.message}`, 'success');
            const docCount = await getDocumentCount();
            document.getElementById('document-count').textContent = docCount;
            if (document.getElementById('documents-list').style.display !== 'none') {
                refreshDocuments();
            }
            refreshVectorStats();
            await loadDocumentCount();
        } catch (error) {
            console.error('Error deleting document:', error);
            showToast(`Delete failed: ${error.message}`, 'error');
        } finally {
            hideLoading();
        }
    });
}

async function applySettings() {
    const settings = {
        embedding_model: document.querySelector('input[name="embedding-model-radio"]:checked').value,
        chunk_size: parseInt(document.getElementById('chunk-size').value),
        chunk_overlap: parseInt(document.getElementById('chunk-overlap').value),
        chunking_method: document.getElementById('chunking-method').value
    };
    showLoading('Applying settings...');
    try {
        const response = await fetch(`${API_BASE_URL}/settings`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings)
        });
        if (!response.ok) {
            throw new Error(`Settings update failed: ${response.status}`);
        }
        alert('✅ Settings applied successfully');
        refreshVectorStats();
    } catch (error) {
        console.error('Settings error:', error);
        alert(`❌ Settings update failed: ${error.message}`);
    } finally {
        hideLoading();
    }
}

async function refreshVectorStats() {
    try {
        const response = await fetch(`${API_BASE_URL}/vector-stats`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const stats = await response.json();
        document.getElementById('indexed-count').textContent = stats.indexed_documents || '-';
        document.getElementById('vector-dims').textContent = stats.vector_dimensions || '-';
        document.getElementById('chunk-count').textContent = stats.total_chunks || '-';
    } catch (error) {
        console.error('Error loading vector stats:', error);
    }
}

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

async function loadAllHistory() {
    const historyDiv = document.getElementById('conversation-history');
    historyDiv.innerHTML = '<p style="color: orange;">Loading conversation history...</p>';
    try {
        const response = await fetch(`${API_BASE_URL}/conversation-history`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        const data = await response.json();
        displayConversationHistory(data.history || []);
    } catch (error) {
        console.error('Error loading history:', error);
        historyDiv.innerHTML = `
            <div style="color: red; padding: 15px; border: 1px solid #f44336; border-radius: 5px; background-color: #ffebee;">
                <strong>❌ Error loading history:</strong> ${error.message}
                <br><br>
                <button onclick="loadAllHistory()" style="background-color: #f44336; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer;">
                    🔄 Retry
                </button>
            </div>
        `;
    }
}

function displayConversationHistory(history) {
    const container = document.getElementById('conversation-history');
    const mainHeader = document.getElementById('history-main-header');

    if (!history || history.length === 0) {
        container.innerHTML = '<p class="empty-state">No questions asked yet. Start by asking a question above!</p>';
        if(mainHeader) mainHeader.textContent = '📚 Shared Conversation History';
        return;
    }
    
    const sortedHistory = history.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    
    if(mainHeader) mainHeader.textContent = `📚 Shared Conversation History (${sortedHistory.length} conversations)`;

    const historyHtml = sortedHistory.map((item, index) => `
        <div class="history-item" style="border: 1px solid #ddd; padding: 15px; margin: 10px 0; background-color: #fafafa; border-radius: 5px; cursor: pointer;" onclick="toggleHistoryItem(${index})">
            <div style="font-size: 12px; color: #666; margin-bottom: 8px;">
                <strong>Session:</strong> ${item.session_id} |
                <strong>Time:</strong> ${new Date(item.timestamp).toLocaleString()}
            </div>
            <div style="margin-bottom: 8px;">
                <strong style="color: #2196F3;">Question:</strong> ${item.question}
            </div>
            <div id="answer-preview-${index}" style="margin-bottom: 8px;">
                <strong style="color: #4CAF50;">Answer:</strong> ${item.answer.substring(0, 200)}${item.answer.length > 200 ? '... <span style="color: #2196F3;">(Click to expand)</span>' : ''}
            </div>
            <div id="answer-full-${index}" style="margin-bottom: 8px; display: none;">
                <strong style="color: #4CAF50;">Answer:</strong>
                <div style="background-color: #f5f5f5; padding: 10px; border-radius: 3px; margin-top: 5px; white-space: pre-wrap;">${item.answer}</div>
                ${item.sources && item.sources.length > 0 ? `
                <div style="margin-top: 10px;">
                    <strong>Sources:</strong>
                    ${item.sources.map(source => `
                        <div style="font-size: 11px; margin: 3px 0; padding: 5px; background-color: #e8f5e8; border-radius: 3px;">
                            📄 ${source.title} (${source.score || 'N/A'} confidence)
                        </div>
                    `).join('')}
                </div>
                ` : ''}
                <div style="margin-top: 10px; font-size: 11px; color: #666;">
                    <em>Click to collapse</em>
                </div>
            </div>
            <div style="font-size: 11px; color: #999;">
                <strong>Sources:</strong> ${item.sources?.length || 0} documents |
                <strong>Processing:</strong> ${item.processing_time?.toFixed(2) || 'N/A'}s |
                <span style="color: #2196F3;">Click to ${item.answer.length > 200 ? 'expand' : 'view details'}</span>
            </div>
        </div>
    `).join('');

    container.innerHTML = historyHtml;
}

function toggleHistoryItem(index) {
    const preview = document.getElementById(`answer-preview-${index}`);
    const full = document.getElementById(`answer-full-${index}`);
    if (preview.style.display === 'none') {
        preview.style.display = 'block';
        full.style.display = 'none';
    } else {
        preview.style.display = 'none';
        full.style.display = 'block';
    }
}

function showLoading(message = 'Loading...') {
    document.getElementById('loading-text').textContent = message;
    document.getElementById('loading-overlay').style.display = 'flex';
}

function hideLoading() {
    document.getElementById('loading-overlay').style.display = 'none';
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

async function getDocumentCount() {
    try {
        const response = await fetch(`${API_BASE_URL}/documents`);
        if (response.ok) {
            const data = await response.json();
            return data.documents ? data.documents.length : 0;
        }
    } catch (error) {
        console.error('Error getting document count:', error);
    }
    return 0;
}

function toggleDocuments(button) {
    const list = document.getElementById('documents-list');
    const isHidden = list.style.display === 'none';

    if (isHidden) {
        list.style.display = 'block';
        button.textContent = '▼ CLICK TO HIDE DOCUMENTS';
        if (list.innerHTML.includes('<!--')) {
            refreshDocuments();
        }
    } else {
        list.style.display = 'none';
        button.textContent = '▶ CLICK TO LIST DOCUMENTS';
    }
}

function toggleHistory(button) {
    const list = document.getElementById('conversation-history');
    const isHidden = list.style.display === 'none';

    if (isHidden) {
        list.style.display = 'block';
        button.textContent = '▼ CLICK TO HIDE CHAT HISTORY';
        if (list.innerHTML.includes('<!--')) {
            loadAllHistory();
        }
    } else {
        list.style.display = 'none';
        button.textContent = '▶ CLICK TO LIST CHAT HISTORY';
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
            </div>
        `;
    } else {
        const sourcesHtml = message.sources && message.sources.length > 0 ? `
            <div class="message-sources">
                <h4>📚 Sources:</h4>
                ${message.sources.map(source => `
                    <div class="source-item">
                        <span>📄 ${escapeHtml(source.title)}</span>
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
                <div class="message-content ${message.isError ? 'error-message' : ''}">
                    <div class="message-text">${escapeHtml(message.text)}</div>
                    ${sourcesHtml}
                    ${footerHtml}
                </div>
            </div>
        `;
    }
    
    thread.appendChild(messageDiv);
    thread.scrollTop = thread.scrollHeight;
    
    // Dynamically adjust height based on content
    const contentHeight = thread.scrollHeight;
    if (contentHeight > 600) {
        thread.style.maxHeight = '800px';
    } else if (contentHeight > 300) {
        thread.style.maxHeight = '600px';
    } else {
        thread.style.maxHeight = '300px';
    }
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
function startNewChat() {
    if (currentConversation.length > 0) {
        // Save current conversation to history
        conversationHistory.push({
            id: currentSessionId,
            timestamp: new Date().toISOString(),
            messages: [...currentConversation]
        });
        
        // Save to localStorage
        localStorage.setItem('conversationHistory', JSON.stringify(conversationHistory));
    }
    
    // Clear current conversation
    currentConversation = [];
    
    // Generate new session ID
    currentSessionId = generateSessionId();
    sessionStorage.setItem('currentSessionId', currentSessionId);
    
    // Clear the thread UI
    const thread = document.getElementById('current-conversation-thread');
    thread.innerHTML = `
        <div class="empty-state" id="empty-conversation-state">
            <p style="text-align: center; color: #999; padding: 40px;">
                No messages yet. Ask a question to start a conversation!
            </p>
        </div>
    `;
    
    showQueryStatus('New conversation started!', 'success');
    document.getElementById('question-input').focus();
}

// ===== Handle Enter Key =====
function handleQuestionKeyPress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        askQuestion();
    }
}

// ===== Show Query Status =====
function showQueryStatus(message, type) {
    const statusDiv = document.getElementById('query-status');
    const colors = {
        success: '#28a745',
        error: '#dc3545',
        info: '#007bff'
    };
    const tipHtml = '💡 <strong>Tip:</strong> You can keep asking questions in a conversation, or click <strong>NEW CHAT</strong> to start a new thread.';
    
    statusDiv.innerHTML = `<p style="color: ${colors[type] || colors.info};">${message}</p>`;
    setTimeout(() => {
        statusDiv.innerHTML = tipHtml;
    }, 3000);
}

// ===== Utility Functions =====
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatTime(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
}

