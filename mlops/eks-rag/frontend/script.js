const API_BASE_URL = window.location.origin + '/api';

document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing...');
    try {
        checkAPIHealth();
        refreshVectorStats();
        loadDocumentCount();
        loadConversationCount();
    } catch (error) {
        console.error('Initialization error:', error);
        document.getElementById('session-info').textContent = 'Session: Initialization error - check console';
    }
});

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
    overlay.classList.add('show');
    
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
        alert('Please enter a question');
        return;
    }

    const answerDiv = document.getElementById('answer-area');
    answerDiv.innerHTML = `
        <div style="border: 1px solid #ddd; padding: 20px; margin: 10px 0; background-color: #f8f9fa; border-radius: 8px; text-align: center;">
            <div style="display: inline-block; position: relative; margin-bottom: 15px;">
                <div style="width: 40px; height: 40px; border: 4px solid #e9ecef; border-top: 4px solid #007bff; border-radius: 50%; animation: spin 1s linear infinite;"></div>
                <style>@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }</style>
            </div>
            <div style="font-size: 16px; font-weight: 500; color: #495057; margin-bottom: 8px;">🔍 Analyzing your question...</div>
            <div style="font-size: 14px; color: #6c757d; margin-bottom: 5px;">Question: "${question}"</div>
            <div style="font-size: 12px; color: #868e96;">Searching documents • Generating response • This may take a few seconds</div>
        </div>
    `;

    try {
        const response = await fetch(`${API_BASE_URL}/query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question: question, top_k: 5 })
        });
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(errorText || `Query failed: ${response.status}`);
        }
        const result = await response.json();
        questionInput.value = '';
        
        const answerHtml = `
            <div style="border: 2px solid #28a745; padding: 20px; margin: 10px 0; background-color: #f8fff9; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <div style="margin-bottom: 12px;">
                    <strong style="color: #495057;">Your Question:</strong>
                    <div style="background-color: #e3f2fd; padding: 10px; border-radius: 5px; margin-top: 5px; color: #1565c0; font-weight: 500;">${question}</div>
                </div>
                <div style="margin-bottom: 15px;">
                    <strong style="color: #495057;">Answer:</strong>
                    <div style="background-color: #ffffff; padding: 15px; border-radius: 5px; margin-top: 8px; border-left: 4px solid #28a745; color: #212529; line-height: 1.6; white-space: pre-wrap;">${result.answer}</div>
                </div>
                ${result.sources && result.sources.length > 0 ? `
                <div class="sources" style="margin-top: 15px; border-top: 1px solid #dee2e6; padding-top: 10px;">
                    <strong>Sources:</strong>
                    ${result.sources.map(source => `
                        <div class="source-item" style="font-size: 12px; margin: 5px 0; padding: 8px; background-color: #f8f9fa; border-radius: 4px;">
                            📄 <strong>${source.title}</strong> (Confidence: ${(source.score * 100).toFixed(1)}%)
                        </div>
                    `).join('')}
                </div>
                ` : ''}
                <div style="display: flex; justify-content: space-between; align-items: center; font-size: 12px; color: #6c757d; border-top: 1px solid #dee2e6; padding-top: 10px;">
                    <div>
                        <span style="background-color: #e9ecef; padding: 4px 8px; border-radius: 12px;">⏱️ ${result.processing_time?.toFixed(2) || 'N/A'}s</span>
                    </div>
                    <div style="color: #28a745; font-weight: 500;">✅ Complete</div>
                </div>
            </div>
        `;
        answerDiv.innerHTML = answerHtml;

        if (document.getElementById('conversation-history').style.display !== 'none') {
            loadAllHistory();
        }
    } catch (error) {
        console.error('Error asking question:', error);
        answerDiv.innerHTML = `<div style="color: red; padding: 15px; border: 1px solid #f44336; border-radius: 5px; background-color: #ffebee;"><strong>❌ Query Error:</strong> ${error.message}</div>`;
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
