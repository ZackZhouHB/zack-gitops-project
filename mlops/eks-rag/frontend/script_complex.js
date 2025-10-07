// Configuration - will be dynamically set based on ingress
const API_BASE_URL = window.location.origin + '/api';

// Global state
let conversationHistory = [];
let currentSyncJobId = null;

// Test function
function testAPI() {
    console.log('testAPI called');
    alert('Test function called!');
    
    fetch(`${API_BASE_URL}/`)
        .then(response => response.json())
        .then(data => {
            console.log('API test success:', data);
            alert('API test success: ' + JSON.stringify(data));
        })
        .catch(error => {
            console.error('API test failed:', error);
            alert('API test failed: ' + error);
        });
}

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded');
    checkSystemStatus();
    refreshDocuments();
    loadConversationHistory();
    
    // Set up enter key for question input
    document.getElementById('question-input').addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && e.ctrlKey) {
            askQuestion();
        }
    });
});

// Tab management
function showTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Remove active class from all buttons
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Show selected tab
    document.getElementById(tabName + '-tab').classList.add('active');
    
    // Add active class to clicked button
    event.target.classList.add('active');
}

// System status check
async function checkSystemStatus() {
    try {
        const response = await fetch(`${API_BASE_URL}/`);
        const data = await response.json();
        
        updateStatusIndicator('backend-status', true, 'Healthy');
        updateStatusIndicator('kendra-status', data.kendra_status, data.kendra_status ? 'Connected' : 'Disconnected');
        updateStatusIndicator('s3-status', data.s3_status, data.s3_status ? 'Connected' : 'Disconnected');
        updateStatusIndicator('bedrock-status', data.bedrock_status, data.bedrock_status ? 'Connected' : 'Disconnected');
        
    } catch (error) {
        console.error('Error checking system status:', error);
        updateStatusIndicator('backend-status', false, 'Error');
        updateStatusIndicator('kendra-status', false, 'Unknown');
        updateStatusIndicator('s3-status', false, 'Unknown');
        updateStatusIndicator('bedrock-status', false, 'Unknown');
    }
}

function updateStatusIndicator(elementId, isHealthy, text) {
    const element = document.getElementById(elementId);
    element.textContent = text;
    element.className = 'status-value ' + (isHealthy ? 'healthy' : 'error');
}

// Document management
async function refreshDocuments() {
    try {
        const response = await fetch(`${API_BASE_URL}/documents`);
        const data = await response.json();
        
        displayDocuments(data.documents);
        document.getElementById('document-count').textContent = data.documents.length;
        
    } catch (error) {
        console.error('Error fetching documents:', error);
        document.getElementById('documents-list').innerHTML = '<p class="empty-state">Error loading documents</p>';
    }
}

function displayDocuments(documents) {
    const container = document.getElementById('documents-list');
    
    if (documents.length === 0) {
        container.innerHTML = '<p class="empty-state">No documents found. Upload some documents to get started.</p>';
        return;
    }
    
    const documentsHtml = documents.map(doc => `
        <div class="document-item">
            <div class="document-info">
                <div class="document-name">${doc.filename}</div>
                <div class="document-meta">
                    Size: ${formatFileSize(doc.size)} | 
                    Modified: ${new Date(doc.last_modified).toLocaleString()}
                </div>
            </div>
            <button onclick="deleteDocument('${doc.filename}')" style="background: #dc3545; color: white;">🗑️ Delete</button>
        </div>
    `).join('');
    
    container.innerHTML = documentsHtml;
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

async function uploadFile() {
    const fileInput = document.getElementById('file-upload');
    const file = fileInput.files[0];
    
    if (!file) return;
    
    const formData = new FormData();
    formData.append('file', file);
    
    showLoading('Uploading file to S3...');
    
    try {
        const response = await fetch(`${API_BASE_URL}/documents/upload`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showAlert(data.message, 'success');
            refreshDocuments();
            fileInput.value = ''; // Clear the input
            
            // Suggest syncing with Kendra
            showAlert('File uploaded! Remember to sync with Kendra to make it searchable.', 'info');
        } else {
            showAlert(`Error: ${data.detail}`, 'error');
        }
    } catch (error) {
        console.error('Error uploading file:', error);
        showAlert('Failed to upload file. Please try again.', 'error');
    } finally {
        hideLoading();
    }
}

async function deleteDocument(filename) {
    if (!confirm(`Are you sure you want to delete "${filename}"?`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/documents/${encodeURIComponent(filename)}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showAlert(data.message, 'success');
            refreshDocuments();
        } else {
            showAlert(`Error: ${data.detail}`, 'error');
        }
    } catch (error) {
        console.error('Error deleting document:', error);
        showAlert('Failed to delete document. Please try again.', 'error');
    }
}

async function syncDocuments() {
    showLoading('Starting Kendra sync job...');
    
    try {
        const response = await fetch(`${API_BASE_URL}/documents/sync`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (response.ok) {
            currentSyncJobId = data.job_id;
            showAlert(`Sync job started: ${data.job_id}`, 'success');
            monitorSyncStatus(data.job_id);
        } else {
            showAlert(`Error: ${data.detail}`, 'error');
        }
    } catch (error) {
        console.error('Error starting sync:', error);
        showAlert('Failed to start sync. Please try again.', 'error');
    } finally {
        hideLoading();
    }
}

async function monitorSyncStatus(jobId) {
    const statusContainer = document.getElementById('sync-status');
    
    const checkStatus = async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/documents/sync-status/${jobId}`);
            const data = await response.json();
            
            const status = data.status;
            statusContainer.innerHTML = `
                <div class="sync-job">
                    <strong>Job ID:</strong> ${jobId}<br>
                    <strong>Status:</strong> <span class="status-${status.status.toLowerCase()}">${status.status}</span><br>
                    ${status.documents_added ? `<strong>Documents Added:</strong> ${status.documents_added}<br>` : ''}
                    ${status.documents_modified ? `<strong>Documents Modified:</strong> ${status.documents_modified}<br>` : ''}
                    ${status.documents_failed ? `<strong>Documents Failed:</strong> ${status.documents_failed}<br>` : ''}
                    ${status.error_message ? `<strong>Error:</strong> ${status.error_message}<br>` : ''}
                </div>
            `;
            
            if (status.status === 'SUCCEEDED') {
                showAlert('Kendra sync completed successfully!', 'success');
                currentSyncJobId = null;
            } else if (status.status === 'FAILED') {
                showAlert('Kendra sync failed. Check the status for details.', 'error');
                currentSyncJobId = null;
            } else if (status.status === 'SYNCING') {
                // Continue monitoring
                setTimeout(checkStatus, 5000);
            }
            
        } catch (error) {
            console.error('Error checking sync status:', error);
            statusContainer.innerHTML = '<p class="error">Error checking sync status</p>';
        }
    };
    
    checkStatus();
}

// Query management
async function askQuestion() {
    console.log('askQuestion called');
    const questionInput = document.getElementById('question-input');
    const question = questionInput.value.trim();
    
    console.log('Question:', question);
    
    if (!question) {
        showAlert('Please enter a question.', 'error');
        return;
    }
    
    const topK = parseInt(document.getElementById('top-k-select').value);
    
    showLoading('Searching with Kendra and generating answer...');
    console.log('Loading shown, making API call');
    
    try {
        // Create AbortController for timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 120000); // 2 minutes
        
        console.log('Making fetch request to:', `${API_BASE_URL}/query`);
        const response = await fetch(`${API_BASE_URL}/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                question: question,
                top_k: topK
            }),
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        console.log('Response received:', response.status, response.ok);
        
        const data = await response.json();
        console.log('Response data:', data);
        
        if (response.ok) {
            console.log('Response OK, adding to history');
            addToConversationHistory(data);
            questionInput.value = ''; // Clear the input
            showTab('query'); // Switch to query tab if not already there
            loadConversationHistory(); // Refresh history from server
        } else {
            console.log('Response not OK:', data);
            showAlert(`Error: ${data.detail}`, 'error');
        }
    } catch (error) {
        console.error('Error querying RAG system:', error);
        showAlert('Failed to process question. Please try again.', 'error');
    } finally {
        console.log('Hiding loading');
        hideLoading();
    }
}

function addToConversationHistory(queryResult) {
    conversationHistory.unshift(queryResult);
    
    // Keep only last 10 conversations
    if (conversationHistory.length > 10) {
        conversationHistory = conversationHistory.slice(0, 10);
    }
    
    displayConversationHistory();
}

function displayConversationHistory() {
    console.log('displayConversationHistory called with', conversationHistory.length, 'items');
    const container = document.getElementById('conversation-history');
    
    if (!container) {
        console.error('conversation-history container not found');
        return;
    }
    
    if (conversationHistory.length === 0) {
        container.innerHTML = '<p class="empty-state">No questions asked yet. Start by asking a question above!</p>';
        return;
    }
    
    try {
        const conversationHtml = conversationHistory.map((item, index) => {
            console.log('Processing item', index, item);
            return `
                <div class="conversation-item">
                    <div class="question">❓ ${item.question || 'No question'}</div>
                    <div class="answer">🤖 ${item.answer || 'No answer'}</div>
                    <div class="sources">
                        <strong>📚 Sources:</strong>
                        ${(item.sources || []).map(source => `
                            <div class="source-item">
                                <strong>${source.title || 'No title'}</strong> (Score: ${source.score || 'N/A'})<br>
                                <small>${source.uri || 'No URI'}</small><br>
                                <em>${source.excerpt || 'No excerpt'}</em>
                            </div>
                        `).join('')}
                    </div>
                    <div class="processing-time">⏱️ Processing time: ${item.processing_time || 0}s</div>
                </div>
            `;
        }).join('');
        
        console.log('Setting HTML content');
        container.innerHTML = conversationHtml;
        console.log('HTML content set successfully');
    } catch (error) {
        console.error('Error in displayConversationHistory:', error);
        container.innerHTML = '<p class="error">Error displaying conversation history</p>';
    }
}

// Utility functions
function showLoading(message = 'Loading...') {
    document.getElementById('loading-text').textContent = message;
    document.getElementById('loading-overlay').style.display = 'flex';
}

function hideLoading() {
    document.getElementById('loading-overlay').style.display = 'none';
}

async function loadConversationHistory() {
    console.log('loadConversationHistory called');
    try {
        console.log('Fetching from:', `${API_BASE_URL}/conversation-history`);
        const response = await fetch(`${API_BASE_URL}/conversation-history`);
        console.log('History response:', response.status, response.ok);
        
        const data = await response.json();
        console.log('History data:', data);
        
        const historyContainer = document.getElementById('conversation-history');
        console.log('History container:', historyContainer);
        
        if (response.ok && data.history && data.history.length > 0) {
            console.log('Loading', data.history.length, 'conversations');
            conversationHistory = data.history.reverse();
            displayConversationHistory();
        } else {
            console.log('No history or response not OK');
            historyContainer.innerHTML = '<p class="empty-state">No questions asked yet. Start by asking a question above!</p>';
        }
    } catch (error) {
        console.error('Error loading conversation history:', error);
        const historyContainer = document.getElementById('conversation-history');
        historyContainer.innerHTML = '<p class="empty-state">Error loading conversation history.</p>';
    }
}

function showAlert(message, type = 'info') {
    // Remove existing alerts
    const existingAlerts = document.querySelectorAll('.alert');
    existingAlerts.forEach(alert => alert.remove());
    
    // Create new alert
    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.textContent = message;
    
    // Insert at the top of the container
    const container = document.querySelector('.container');
    container.insertBefore(alert, container.firstChild);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        alert.remove();
    }, 5000);
}
