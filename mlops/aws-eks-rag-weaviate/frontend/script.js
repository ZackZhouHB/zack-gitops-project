const API_BASE_URL = window.location.origin + '/api';

document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing...');
    console.log('API_BASE_URL:', API_BASE_URL);

    // Initialize with error handling
    try {
        loadAllHistory();
        checkAPIHealth();
        loadDocumentCount();
        refreshDocuments();
        refreshVectorStats();
    } catch (error) {
        console.error('Initialization error:', error);
        document.getElementById('session-info').textContent = 'Session: Initialization error - check console';
    }
});

async function checkAPIHealth() {
    try {
        const response = await fetch(`${API_BASE_URL}/`);
        if (response.ok) {
            const data = await response.json();
            console.log('API Health:', data);

            document.getElementById('weaviate-status').textContent = data.weaviate_status ? '✅ Connected' : '❌ Disconnected';
            document.getElementById('s3-status').textContent = data.s3_status ? '✅ Connected' : '❌ Disconnected';
            document.getElementById('bedrock-status').textContent = data.bedrock_status ? '✅ Connected' : '❌ Disconnected';

            document.getElementById('session-info').textContent = `Session: ${data.session_id} | Status: Ready`;

            // Enable/disable features based on service availability
            const queryButton = document.querySelector('#query-tab button[onclick="askQuestion()"]');

            if (data.weaviate_status && data.bedrock_status) {
                // All services ready
                if (queryButton) queryButton.disabled = false;
            } else {
                // Some services down
                if (queryButton) {
                    queryButton.disabled = true;
                    queryButton.title = 'Some services are unavailable. Please wait...';
                }
            }

            return data;
        } else {
            throw new Error(`HTTP ${response.status}`);
        }
    } catch (error) {
        console.error('API Health Check Failed:', error);
        ['weaviate-status', 's3-status', 'bedrock-status'].forEach(id => {
            document.getElementById(id).textContent = '❌ Error';
        });
        document.getElementById('session-info').textContent = 'Session: Error connecting to API';

        // Disable query features when API is down
        const queryButton = document.querySelector('#query-tab button[onclick="askQuestion()"]');

        if (queryButton) {
            queryButton.disabled = true;
            queryButton.title = 'API connection error';
        }

        return null;
    }
}

function showTab(tabName) {
    document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
    document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
    
    document.getElementById(`${tabName}-tab`).classList.add('active');
    event.target.classList.add('active');
}

async function uploadFile() {
    const fileInput = document.getElementById('file-upload');
    const file = fileInput.files[0];
    
    if (!file) return;

    showLoading('Uploading file...');
    
    try {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch(`${API_BASE_URL}/documents/upload`, {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            const result = await response.json();
            showAlert(`✅ ${result.message}`, 'success');
            refreshDocuments();
            refreshVectorStats();
        } else {
            throw new Error(`Upload failed: ${response.status}`);
        }
    } catch (error) {
        console.error('Upload error:', error);
        showAlert(`❌ Upload failed: ${error.message}`, 'error');
    } finally {
        hideLoading();
        fileInput.value = '';
    }
}

async function refreshDocuments() {
    console.log('Refreshing documents...');
    try {
        const response = await fetch(`${API_BASE_URL}/documents`);
        console.log('Documents response status:', response.status);

        if (response.ok) {
            const data = await response.json();
            console.log('Documents data:', data);
            displayDocuments(data.documents || []);
            document.getElementById('document-count').textContent = data.documents ? data.documents.length : 0;
        } else {
            console.error('Documents API error:', response.status, response.statusText);
            displayDocuments([]);
            document.getElementById('document-count').textContent = '❌ Error';
        }
    } catch (error) {
        console.error('Error loading documents:', error);
        displayDocuments([]);
        document.getElementById('documents-list').innerHTML = `
            <div style="color: red; padding: 15px; border: 1px solid #f44336; border-radius: 5px; background-color: #ffebee;">
                <strong>❌ Error loading documents:</strong> ${error.message}
                <br><br>
                <button onclick="refreshDocuments()" style="background-color: #f44336; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer;">
                    🔄 Retry
                </button>
            </div>
        `;
        document.getElementById('document-count').textContent = '❌ Error';
    }
}

function displayDocuments(documents) {
    const container = document.getElementById('documents-list');
    
    if (documents.length === 0) {
        container.innerHTML = '<p class="empty-state">No documents uploaded yet</p>';
        return;
    }
    
    const html = documents.map(doc => `
        <div class="document-item">
            <div class="document-info">
                <span class="document-name">${doc.filename}</span>
                <span class="document-size">${formatFileSize(doc.size)}</span>
                <span class="document-date">${new Date(doc.last_modified).toLocaleDateString()}</span>
            </div>
            <button onclick="deleteDocument('${doc.filename}')" class="delete-btn">🗑️</button>
        </div>
    `).join('');
    
    container.innerHTML = html;
}

async function deleteDocument(filename) {
    if (!confirm(`Delete "${filename}"?`)) return;
    
    try {
        const response = await fetch(`${API_BASE_URL}/documents/${encodeURIComponent(filename)}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showAlert('✅ Document deleted', 'success');
            refreshDocuments();
            refreshVectorStats();
        } else {
            throw new Error(`Delete failed: ${response.status}`);
        }
    } catch (error) {
        console.error('Delete error:', error);
        showAlert(`❌ Delete failed: ${error.message}`, 'error');
    }
}

async function applySettings() {
    const settings = {
        embedding_model: document.getElementById('embedding-model').value,
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
        
        if (response.ok) {
            showAlert('✅ Settings applied successfully', 'success');
            refreshVectorStats();
        } else {
            throw new Error(`Settings update failed: ${response.status}`);
        }
    } catch (error) {
        console.error('Settings error:', error);
        showAlert(`❌ Settings update failed: ${error.message}`, 'error');
    } finally {
        hideLoading();
    }
}

async function processAllDocuments() {
    console.log('Processing and indexing all documents...');
    showLoading('Processing and indexing documents...');

    try {
        // Get all documents from S3
        const docsResponse = await fetch(`${API_BASE_URL}/documents`);
        if (!docsResponse.ok) {
            throw new Error(`Failed to fetch documents: ${docsResponse.status}`);
        }

        const docsData = await docsResponse.json();
        const documents = docsData.documents || [];

        if (documents.length === 0) {
            showAlert('ℹ️ No documents to process', 'info');
            return;
        }

        let processed = 0;
        let failed = 0;

        // Process each document
        for (const doc of documents) {
            try {
                console.log(`Processing document: ${doc.filename}`);

                // Re-index the document (this will re-extract text and index in Weaviate)
                const reindexResponse = await fetch(`${API_BASE_URL}/documents/reindex/${encodeURIComponent(doc.filename)}`, {
                    method: 'POST'
                });

                if (reindexResponse.ok) {
                    processed++;
                    console.log(`✅ Successfully indexed: ${doc.filename}`);
                } else {
                    failed++;
                    console.error(`❌ Failed to index: ${doc.filename} - ${reindexResponse.status}`);
                }
            } catch (error) {
                failed++;
                console.error(`❌ Error processing ${doc.filename}:`, error);
            }
        }

        // Refresh the display
        refreshDocuments();
        refreshVectorStats();

        // Show results
        if (failed === 0) {
            showAlert(`✅ Successfully processed and indexed ${processed} documents!`, 'success');
        } else {
            showAlert(`⚠️ Processed ${processed} documents, ${failed} failed`, 'warning');
        }

    } catch (error) {
        console.error('Error processing documents:', error);
        showAlert(`❌ Error processing documents: ${error.message}`, 'error');
    } finally {
        hideLoading();
    }
}

async function refreshVectorStats() {
    console.log('Refreshing vector stats...');
    try {
        const response = await fetch(`${API_BASE_URL}/vector-stats`);
        console.log('Vector stats response status:', response.status);

        if (response.ok) {
            const stats = await response.json();
            console.log('Vector stats data:', stats);

            document.getElementById('indexed-count').textContent = stats.indexed_documents || '-';
            document.getElementById('vector-dims').textContent = stats.vector_dimensions || '-';
            document.getElementById('chunk-count').textContent = stats.total_chunks || '-';

            showAlert('✅ Vector stats refreshed', 'success');
        } else {
            console.error('Vector stats API error:', response.status, response.statusText);
            showAlert(`❌ Failed to refresh stats: ${response.status}`, 'error');
        }
    } catch (error) {
        console.error('Error loading vector stats:', error);
        showAlert(`❌ Error refreshing stats: ${error.message}`, 'error');
    }
}

async function askQuestion() {
    const questionInput = document.getElementById('question-input');
    const question = questionInput.value.trim();
    
    if (!question) {
        showAlert('Please enter a question', 'warning');
        return;
    }
    
    const topK = parseInt(document.getElementById('top-k-select').value);
    
    showLoading('Searching documents and generating answer...');
    
    try {
        const response = await fetch(`${API_BASE_URL}/query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question, top_k: topK })
        });
        
        if (response.ok) {
            const result = await response.json();
            displayQueryResult(result);
            loadAllHistory();
            questionInput.value = '';
        } else {
            throw new Error(`Query failed: ${response.status}`);
        }
    } catch (error) {
        console.error('Query error:', error);
        showAlert(`❌ Query failed: ${error.message}`, 'error');
    } finally {
        hideLoading();
    }
}

function displayQueryResult(result) {
    const container = document.getElementById('conversation-history');
    
    const resultHtml = `
        <div class="query-result">
            <div class="question">
                <strong>Q:</strong> ${result.question}
            </div>
            <div class="answer">
                <strong>A:</strong> ${result.answer}
            </div>
            <div class="sources">
                <strong>Sources:</strong>
                ${result.sources.map(source => `
                    <div class="source-item">
                        <span class="source-title">${source.title}</span>
                        <span class="source-score">Score: ${(source.score * 100).toFixed(1)}%</span>
                        <div class="source-excerpt">${source.excerpt}</div>
                    </div>
                `).join('')}
            </div>
            <div class="processing-time">
                Processing time: ${result.processing_time.toFixed(2)}s
            </div>
        </div>
    `;
    
    container.innerHTML = resultHtml + container.innerHTML;
}

async function loadAllHistory() {
    try {
        const response = await fetch(`${API_BASE_URL}/conversation-history`);
        if (response.ok) {
            const data = await response.json();
            displayConversationHistory(data.history);
        }
    } catch (error) {
        console.error('Error loading history:', error);
    }
}

function displayConversationHistory(history) {
    const container = document.getElementById('conversation-history');
    
    if (!history || history.length === 0) {
        container.innerHTML = '<p class="empty-state">No questions asked yet. Start by asking a question above!</p>';
        return;
    }
    
    const html = history.map(item => `
        <div class="history-item">
            <div class="history-header">
                <span class="session-id">Session: ${item.session_id}</span>
                <span class="timestamp">${new Date(item.timestamp).toLocaleString()}</span>
            </div>
            <div class="history-question">
                <strong>Q:</strong> ${item.question}
            </div>
            <div class="history-answer">
                <strong>A:</strong> ${item.answer}
            </div>
        </div>
    `).join('');
    
    container.innerHTML = html;
}

function showLoading(message = 'Loading...') {
    document.getElementById('loading-text').textContent = message;
    document.getElementById('loading-overlay').style.display = 'flex';
}

function hideLoading() {
    document.getElementById('loading-overlay').style.display = 'none';
}

function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.textContent = message;
    alertDiv.style.cssText = `
        position: fixed; top: 20px; right: 20px; z-index: 1000;
        padding: 12px 20px; border-radius: 4px; color: white;
        background: ${type === 'success' ? '#28a745' : type === 'error' ? '#dc3545' : '#ffc107'};
    `;
    
    document.body.appendChild(alertDiv);
    setTimeout(() => alertDiv.remove(), 3000);
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function loadDocumentCount() {
    refreshDocuments();
}

async function loadAllHistory(retryCount = 0, maxRetries = 5) {
    const historyDiv = document.getElementById('conversation-history');
    
    if (retryCount === 0) {
        historyDiv.innerHTML = '<p style="color: orange;">Loading conversation history...</p>';
    } else {
        historyDiv.innerHTML = `<p style="color: orange;">Loading conversation history... (attempt ${retryCount + 1}/${maxRetries + 1})</p>`;
    }

    try {
        console.log('Fetching from:', `${API_BASE_URL}/conversation-history`);
        const response = await fetch(`${API_BASE_URL}/conversation-history`, {
            timeout: 30000 // 30 second timeout
        });
        console.log('Response status:', response.status);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        console.log('History data:', data);

        if (data.history && data.history.length > 0) {
            // Sort by timestamp (newest first)
            const sortedHistory = data.history.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

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

            historyDiv.innerHTML = `
                <h3 style="color: #333; margin-bottom: 15px;">📚 Shared Conversation History (${sortedHistory.length} conversations)</h3>
                ${historyHtml}
            `;
        } else {
            historyDiv.innerHTML = `
                <div style="text-align: center; padding: 20px; color: #666;">
                    <p style="font-size: 16px;">🤔 No conversations found yet</p>
                    <p>Start by asking a question above to see the conversation history here!</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('Error loading history:', error);
        
        // Auto-retry with exponential backoff for 502/503/504 errors
        if (retryCount < maxRetries && (error.message.includes('502') || error.message.includes('503') || error.message.includes('504'))) {
            const delay = Math.pow(2, retryCount) * 2000; // 2s, 4s, 8s, 16s, 32s
            console.log(`Retrying in ${delay/1000}s... (attempt ${retryCount + 1}/${maxRetries})`);
            
            historyDiv.innerHTML = `
                <div style="color: orange; padding: 15px; border: 1px solid #ff9800; border-radius: 5px; background-color: #fff3e0;">
                    <strong>⏳ Backend starting up...</strong> Retrying in ${delay/1000} seconds (${retryCount + 1}/${maxRetries})
                    <div style="margin-top: 10px; background-color: #ddd; border-radius: 10px; overflow: hidden;">
                        <div style="width: 0%; height: 20px; background-color: #ff9800; transition: width ${delay}ms linear;" id="retry-progress"></div>
                    </div>
                </div>
            `;
            
            // Animate progress bar
            setTimeout(() => {
                const progressBar = document.getElementById('retry-progress');
                if (progressBar) progressBar.style.width = '100%';
            }, 100);
            
            setTimeout(() => {
                loadAllHistory(retryCount + 1, maxRetries);
            }, delay);
        } else {
            // Show error only after all retries exhausted or for non-502 errors
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
    }
}

async function loadDocumentCount() {
    try {
        const response = await fetch(`${API_BASE_URL}/documents`);
        if (response.ok) {
            const data = await response.json();
            const documentCount = data.documents ? data.documents.length : 0;
            document.getElementById('document-count').textContent = documentCount;
            return documentCount;
        }
    } catch (error) {
        console.error('Error loading document count:', error);
        document.getElementById('document-count').textContent = '❌ Error';
    }
    return 0;
}

async function askQuestion() {
    const questionInput = document.getElementById('question-input');
    const question = questionInput.value.trim();

    if (!question) {
        alert('Please enter a question');
        return;
    }

    const historyDiv = document.getElementById('conversation-history');

    // Create a professional loading indicator with status updates
    historyDiv.innerHTML = `
        <div style="border: 1px solid #ddd; padding: 20px; margin: 10px 0; background-color: #f8f9fa; border-radius: 8px; text-align: center;">
            <div style="display: inline-block; position: relative; margin-bottom: 15px;">
                <div style="width: 40px; height: 40px; border: 4px solid #e9ecef; border-top: 4px solid #007bff; border-radius: 50%; animation: spin 1s linear infinite;"></div>
                <style>
                    @keyframes spin {
                        0% { transform: rotate(0deg); }
                        100% { transform: rotate(360deg); }
                    }
                </style>
            </div>
            <div style="font-size: 16px; font-weight: 500; color: #495057; margin-bottom: 8px;">
                🔍 Analyzing your question...
            </div>
            <div style="font-size: 14px; color: #6c757d; margin-bottom: 5px;">
                Question: "${question}"
            </div>
            <div style="font-size: 12px; color: #868e96;">
                Searching documents • Generating response • This may take a few seconds
            </div>
            <div style="margin-top: 15px; height: 4px; background-color: #e9ecef; border-radius: 2px; overflow: hidden;">
                <div style="height: 100%; background: linear-gradient(90deg, #007bff, #0056b3); width: 0%; animation: loading-bar 3s ease-in-out infinite;"></div>
            </div>
            <style>
                @keyframes loading-bar {
                    0% { width: 0%; }
                    50% { width: 70%; }
                    100% { width: 100%; }
                }
            </style>
        </div>
    `;

    try {
        const response = await fetch(`${API_BASE_URL}/query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question: question, top_k: 5 })
        });

        if (response.ok) {
            const result = await response.json();
            questionInput.value = '';

            // Display the answer with success styling
            const answerHtml = `
                <div style="border: 2px solid #28a745; padding: 20px; margin: 10px 0; background-color: #f8fff9; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <div style="display: flex; align-items: center; margin-bottom: 15px;">
                        <div style="width: 24px; height: 24px; background-color: #28a745; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin-right: 10px;">
                            <span style="color: white; font-size: 14px;">✓</span>
                        </div>
                        <div style="font-weight: 600; color: #28a745; font-size: 16px;">Answer Generated</div>
                    </div>
                    <div style="margin-bottom: 12px;">
                        <strong style="color: #495057;">Your Question:</strong>
                        <div style="background-color: #e3f2fd; padding: 10px; border-radius: 5px; margin-top: 5px; color: #1565c0; font-weight: 500;">${question}</div>
                    </div>
                    <div style="margin-bottom: 15px;">
                        <strong style="color: #495057;">Answer:</strong>
                        <div style="background-color: #ffffff; padding: 15px; border-radius: 5px; margin-top: 8px; border-left: 4px solid #28a745; color: #212529; line-height: 1.6; white-space: pre-wrap;">${result.answer}</div>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; font-size: 12px; color: #6c757d; border-top: 1px solid #dee2e6; padding-top: 10px;">
                        <div>
                            <span style="background-color: #e9ecef; padding: 4px 8px; border-radius: 12px;">⏱️ ${result.processing_time?.toFixed(2) || 'N/A'}s</span>
                            <span style="background-color: #e9ecef; padding: 4px 8px; border-radius: 12px; margin-left: 8px;">📄 ${result.sources?.length || 0} sources</span>
                        </div>
                        <div style="color: #28a745; font-weight: 500;">✅ Complete</div>
                    </div>
                </div>
            `;

            historyDiv.innerHTML = answerHtml;

            // Reload history after showing the answer
            setTimeout(() => loadAllHistory(), 2000);
        } else {
            const errorText = await response.text();
            historyDiv.innerHTML = `
                <div style="border: 2px solid #dc3545; padding: 20px; margin: 10px 0; background-color: #fff5f5; border-radius: 8px;">
                    <div style="display: flex; align-items: center; margin-bottom: 10px;">
                        <div style="width: 24px; height: 24px; background-color: #dc3545; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin-right: 10px;">
                            <span style="color: white; font-size: 14px;">✗</span>
                        </div>
                        <div style="font-weight: 600; color: #dc3545; font-size: 16px;">Processing Error</div>
                    </div>
                    <div style="color: #721c24; background-color: #f8d7da; padding: 10px; border-radius: 5px;">
                        ${errorText}
                    </div>
                </div>
            `;
        }
    } catch (error) {
        console.error('Error asking question:', error);
        historyDiv.innerHTML = `
            <div style="border: 2px solid #dc3545; padding: 20px; margin: 10px 0; background-color: #fff5f5; border-radius: 8px;">
                <div style="display: flex; align-items: center; margin-bottom: 10px;">
                    <div style="width: 24px; height: 24px; background-color: #dc3545; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin-right: 10px;">
                        <span style="color: white; font-size: 14px;">✗</span>
                    </div>
                    <div style="font-weight: 600; color: #dc3545; font-size: 16px;">Connection Error</div>
                </div>
                <div style="color: #721c24; background-color: #f8d7da; padding: 10px; border-radius: 5px;">
                    Failed to process question: ${error.message}
                </div>
                <div style="margin-top: 15px;">
                    <button onclick="loadAllHistory()" style="background-color: #dc3545; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer;">
                        🔄 Return to History
                    </button>
                </div>
            </div>
        `;
    }
}

// Function to load Kendra sync history
async function loadKendraSyncHistory() {
    const syncStatusDiv = document.getElementById('sync-status');
    syncStatusDiv.innerHTML = '<p style="color: orange;">Loading sync history...</p>';

    try {
        const response = await fetch(`${API_BASE_URL}/documents/sync-history`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        displaySyncHistory(data.sync_history || []);
    } catch (error) {
        console.error('Error loading sync history:', error);
        syncStatusDiv.innerHTML = `
            <div style="color: red; padding: 10px; border: 1px solid #f44336; border-radius: 5px; background-color: #ffebee;">
                <strong>❌ Error loading sync history:</strong> ${error.message}
            </div>
        `;
    }
}

function displaySyncHistory(syncHistory) {
    const syncStatusDiv = document.getElementById('sync-status');

    if (syncHistory.length === 0) {
        syncStatusDiv.innerHTML = `
            <div style="text-align: center; padding: 20px; color: #666;">
                <p style="font-size: 16px;">📋 No sync history available</p>
                <p>Click "Sync with Kendra" to start a sync job</p>
            </div>
        `;
        return;
    }

    const syncHtml = syncHistory.map((item, index) => `
        <div style="border: 1px solid #ddd; padding: 15px; margin: 10px 0; background-color: #fafafa; border-radius: 5px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <div style="font-weight: bold; color: #333;">
                    ${item.status === 'STARTED' ? '🔄' : '✅'} Sync Job
                </div>
                <div style="font-size: 12px; color: #666;">
                    ${new Date(item.timestamp).toLocaleString()}
                </div>
            </div>
            <div style="font-size: 12px; color: #666; margin-bottom: 5px;">
                <strong>Job ID:</strong> ${item.job_id}
            </div>
            <div style="font-size: 12px; color: #666; margin-bottom: 5px;">
                <strong>Session:</strong> ${item.session_id}
            </div>
            <div style="font-size: 12px; color: #666;">
                <strong>Message:</strong> ${item.message}
            </div>
        </div>
    `).join('');

    syncStatusDiv.innerHTML = `
        <h4 style="color: #333; margin-bottom: 15px;">📊 Kendra Sync History (${syncHistory.length} jobs)</h4>
        ${syncHtml}
    `;
}

// Tab switching function
function showTab(tabName) {
    // Hide all tab contents
    const tabContents = document.querySelectorAll('.tab-content');
    tabContents.forEach(content => {
        content.classList.remove('active');
    });

    // Remove active class from all tab buttons
    const tabButtons = document.querySelectorAll('.tab-button');
    tabButtons.forEach(button => {
        button.classList.remove('active');
    });

    // Show selected tab content
    document.getElementById(tabName + '-tab').classList.add('active');

    // Add active class to clicked button
    event.target.classList.add('active');

    // Load content for the tab if needed
    if (tabName === 'documents') {
        refreshDocuments();
    }
}

// Document management functions
async function refreshDocuments() {
    const documentsList = document.getElementById('documents-list');
    documentsList.innerHTML = '<p style="color: orange;">Loading documents...</p>';

    try {
        const response = await fetch(`${API_BASE_URL}/documents`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        displayDocuments(data.documents || []);

        // Update document count
        document.getElementById('document-count').textContent = data.documents ? data.documents.length : 0;
    } catch (error) {
        console.error('Error loading documents:', error);
        documentsList.innerHTML = `
            <div style="color: red; padding: 15px; border: 1px solid #f44336; border-radius: 5px; background-color: #ffebee;">
                <strong>❌ Error loading documents:</strong> ${error.message}
                <br><br>
                <button onclick="refreshDocuments()" style="background-color: #f44336; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer;">
                    🔄 Retry
                </button>
            </div>
        `;
    }
}

function displayDocuments(documents) {
    const documentsList = document.getElementById('documents-list');

    if (documents.length === 0) {
        documentsList.innerHTML = `
            <div style="text-align: center; padding: 20px; color: #666;">
                <p style="font-size: 16px;">📁 No documents uploaded yet</p>
                <p>Upload some documents to get started with Q&A!</p>
            </div>
        `;
        return;
    }

    const documentsHtml = documents.map((doc, index) => `
        <div style="border: 1px solid #ddd; padding: 15px; margin: 10px 0; background-color: #fafafa; border-radius: 5px; position: relative;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div style="flex-grow: 1;">
                    <div style="font-weight: bold; color: #333; margin-bottom: 5px;">${doc.filename}</div>
                    <div style="font-size: 12px; color: #666; margin-bottom: 5px;">
                        <strong>Size:</strong> ${formatFileSize(doc.size)} |
                        <strong>Modified:</strong> ${new Date(doc.last_modified).toLocaleString()} |
                        <strong>Uploaded by:</strong> ${doc.uploaded_by || 'Unknown'}
                    </div>
                    <div style="font-size: 11px; color: #999;">
                        <strong>S3 Key:</strong> ${doc.key}
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

    documentsList.innerHTML = `
        <h3 style="color: #333; margin-bottom: 15px;">📚 Available Documents (${documents.length})</h3>
        ${documentsHtml}
    `;
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

    if (!file) {
        alert('Please select a file to upload');
        return;
    }

    const documentsList = document.getElementById('documents-list');
    documentsList.innerHTML = '<p style="color: blue;">Uploading file...</p>';

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch(`${API_BASE_URL}/documents/upload`, {
            method: 'POST',
            body: formData
        });

        if (response.ok) {
            const result = await response.json();
            alert(`✅ File uploaded successfully: ${result.message}`);
            fileInput.value = ''; // Clear the file input
            refreshDocuments(); // Refresh the documents list
        } else {
            const errorText = await response.text();
            alert(`❌ Upload failed: ${errorText}`);
            refreshDocuments(); // Refresh to show previous state
        }
    } catch (error) {
        console.error('Error uploading file:', error);
        alert(`❌ Upload failed: ${error.message}`);
        refreshDocuments(); // Refresh to show previous state
    }
}

async function deleteDocument(filename) {
    if (!confirm(`Are you sure you want to delete "${filename}"? This action cannot be undone.`)) {
        return;
    }

    const documentsList = document.getElementById('documents-list');
    documentsList.innerHTML = '<p style="color: orange;">Deleting document...</p>';

    try {
        const response = await fetch(`${API_BASE_URL}/documents/${encodeURIComponent(filename)}`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' }
        });

        if (response.ok) {
            const result = await response.json();
            alert(`✅ Document deleted successfully: ${result.message}`);
            refreshDocuments(); // Refresh the documents list
            loadDocumentCount(); // Update document count
        } else {
            const errorText = await response.text();
            alert(`❌ Delete failed: ${errorText}`);
            refreshDocuments(); // Refresh to show previous state
        }
    } catch (error) {
        console.error('Error deleting document:', error);
        alert(`❌ Delete failed: ${error.message}`);
        refreshDocuments(); // Refresh to show previous state
    }
}

async function syncDocuments() {
    const syncStatusDiv = document.getElementById('sync-status');
    syncStatusDiv.innerHTML = '<p style="color: blue;">Starting sync with Kendra...</p>';

    try {
        const response = await fetch(`${API_BASE_URL}/documents/sync`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        if (response.ok) {
            const result = await response.json();
            alert(`✅ ${result.message}\n\nJob ID: ${result.job_id}\nStatus: ${result.status}`);

            // Reload sync history after a delay
            setTimeout(() => {
                loadKendraSyncHistory();
            }, 1000);
        } else {
            const errorText = await response.text();
            alert(`❌ Sync failed: ${errorText}`);
            loadKendraSyncHistory(); // Reload to show previous state
        }
    } catch (error) {
        console.error('Error syncing documents:', error);
        alert(`❌ Sync failed: ${error.message}`);
        loadKendraSyncHistory(); // Reload to show previous state
    }
}

// Toggle function for expanding/collapsing history items
function toggleHistoryItem(index) {
    const preview = document.getElementById(`answer-preview-${index}`);
    const full = document.getElementById(`answer-full-${index}`);

    if (preview.style.display === 'none') {
        // Currently expanded, so collapse it
        preview.style.display = 'block';
        full.style.display = 'none';
    } else {
        // Currently collapsed, so expand it
        preview.style.display = 'none';
        full.style.display = 'block';
    }
}
