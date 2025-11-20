import './style.css'
import './selection-styles.css'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';

// Configure marked options
marked.setOptions({
  breaks: true,
  gfm: true,
  headerIds: false,
  mangle: false,
  pedantic: false,
  sanitize: false
});

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

const app = document.querySelector<HTMLDivElement>('#app')!;

app.innerHTML = `
  <div class="header">
    <h1 class="header-title">AFSC</h1>
    <p class="header-subtitle">Aviation Chat Assistant</p>
    <!-- Hidden admin button - click top-right corner to access -->
    <button id="admin-button" class="admin-button-hidden" title="Admin Panel">⚙️</button>
  </div>
  
  <div id="chat-container" class="chat-container glass-strong"></div>
  
  <!-- Admin Panel (hidden by default, replaces chat area) -->
  <div id="admin-panel" class="admin-panel-hidden glass-strong">
    <div class="admin-panel-header-main">
      <h2 class="admin-title">Admin Panel</h2>
      <button id="close-admin" class="close-admin-button-main">×</button>
    </div>
    
    <div class="admin-panel-content">
      <!-- Admin Dashboard -->
      <div id="admin-dashboard" class="admin-dashboard">
        <div class="admin-dashboard-content">
          <h3 class="admin-dashboard-title">Admin Dashboard</h3>
          
          <!-- Quick Actions Section -->
          <div class="admin-dashboard-section">
            <h4 class="admin-section-title">Quick Actions</h4>
            <button id="view-pdfs-button" class="admin-action-button">
              <div class="admin-action-icon">📚</div>
              <div class="admin-action-text">
                <div class="admin-action-title">View Uploaded PDFs</div>
                <div class="admin-action-subtitle">Browse and manage all PDF files</div>
        </div>
            </button>
      </div>
      
          <!-- Upload Section -->
          <div class="admin-dashboard-section">
            <h4 class="admin-section-title">Upload New PDF</h4>
      <div class="admin-upload-section">
        <div class="upload-area-main">
          <input 
            type="file" 
            id="pdf-upload" 
            accept=".pdf"
            style="display: none;"
          />
          <label for="pdf-upload" class="upload-label-main">
            <div class="upload-icon-large">📄</div>
            <div class="upload-text-main">
              <div class="upload-title">Choose PDF file</div>
              <div class="upload-subtitle">Click to select or drag and drop</div>
            </div>
          </label>
          <div id="file-name-main" class="file-name-main"></div>
        </div>
        <button id="upload-button" class="upload-button-main" disabled>Upload & Process</button>
        <div id="upload-status" class="upload-status-main"></div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- PDF List Page (hidden by default) -->
      <div id="pdf-list-page" class="pdf-list-page-hidden">
        <div class="pdf-list-page-header">
          <button id="back-to-admin" class="back-button">← Back to Admin</button>
          <h3 class="pdf-list-title">Uploaded PDFs</h3>
        </div>
        <div id="pdf-list" class="pdf-list">
          <div class="loading">Click "View Uploaded PDFs" to load files...</div>
        </div>
      </div>
    </div>
  </div>
  
  <div class="input-area glass">
    <input 
      type="text" 
      id="question-input" 
      class="input-field"
      placeholder="Ask a question..."
      autocomplete="off"
    />
    <button id="send-button" class="send-button">Send</button>
  </div>
  
  <div id="status" class="status"></div>
`;

const chatContainer = document.querySelector<HTMLDivElement>('#chat-container')!;
const questionInput = document.querySelector<HTMLInputElement>('#question-input')!;
const sendButton = document.querySelector<HTMLButtonElement>('#send-button')!;
const statusDiv = document.querySelector<HTMLDivElement>('#status')!;

// Admin panel elements
const adminButton = document.querySelector<HTMLButtonElement>('#admin-button')!;
const adminPanel = document.querySelector<HTMLDivElement>('#admin-panel')!;
const closeAdminButton = document.querySelector<HTMLButtonElement>('#close-admin')!;
const pdfUpload = document.querySelector<HTMLInputElement>('#pdf-upload')!;
const uploadButton = document.querySelector<HTMLButtonElement>('#upload-button')!;
const uploadStatus = document.querySelector<HTMLDivElement>('#upload-status')!;
const pdfList = document.querySelector<HTMLDivElement>('#pdf-list')!;
const adminDashboard = document.querySelector<HTMLDivElement>('#admin-dashboard')!;
const pdfListPage = document.querySelector<HTMLDivElement>('#pdf-list-page')!;
const viewPdfsButton = document.querySelector<HTMLButtonElement>('#view-pdfs-button')!;
const backToAdminButton = document.querySelector<HTMLButtonElement>('#back-to-admin')!;

let messages: ChatMessage[] = [];

// Generate or retrieve session ID (only store session ID, not messages)
function getSessionId(): string {
  let sessionId = localStorage.getItem('chat-session-id');
  if (!sessionId) {
    sessionId = `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    localStorage.setItem('chat-session-id', sessionId);
  }
  return sessionId;
}

// Load messages from server
async function loadMessages(): Promise<void> {
  try {
    const sessionId = getSessionId();
    const response = await fetch(`${API_URL}/chat/history?session_id=${sessionId}&limit=50`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    if (response.ok) {
      const data = await response.json();
      if (data.success && data.messages) {
        messages = data.messages;
        renderMessages();
      }
    }
  } catch (error) {
    console.error('Failed to load messages from server:', error);
    messages = [];
  }
}

// Save messages to server
async function saveMessages(): Promise<void> {
  try {
    const sessionId = getSessionId();
    const response = await fetch(`${API_URL}/chat/history`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        session_id: sessionId,
        messages: messages
      }),
    });
    
    if (!response.ok) {
      console.error('Failed to save messages to server');
    }
  } catch (error) {
    console.error('Failed to save messages to server:', error);
  }
}

function addMessage(role: 'user' | 'assistant', content: string) {
  messages.push({ role, content });
  renderMessages();
  // Save to server asynchronously (don't wait)
  saveMessages().catch(err => console.error('Error saving messages:', err));
}

function renderMessages() {
  if (messages.length === 0) {
    chatContainer.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">💬</div>
        <div class="empty-state-text">Start a conversation</div>
      </div>
    `;
    return;
  }

  chatContainer.innerHTML = messages.map(msg => {
    const isUser = msg.role === 'user';
    // Format the content - convert line breaks to <br> and preserve formatting
    const formattedContent = formatMessageContent(msg.content);
    return `
      <div class="message ${isUser ? 'user' : 'assistant'}">
        <div class="message-bubble">
          <div class="message-content">${formattedContent}</div>
        </div>
      </div>
    `;
  }).join('');
  
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

function escapeHtml(text: string): string {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function formatMessageContent(text: string): string {
  // Parse Markdown and sanitize HTML
  try {
    const html = marked.parse(text);
    // Sanitize to prevent XSS attacks
    return DOMPurify.sanitize(html, {
      ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'blockquote', 'code', 'pre', 'a', 'table', 'thead', 'tbody', 'tr', 'th', 'td'],
      ALLOWED_ATTR: ['href', 'title', 'class']
    });
  } catch (error) {
    console.error('Markdown parsing error:', error);
    // Fallback to plain text if Markdown parsing fails
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML.replace(/\n/g, '<br>');
  }
}

async function sendMessage() {
  const question = questionInput.value.trim();
  if (!question) return;
  
  questionInput.value = '';
  sendButton.disabled = true;
  addMessage('user', question);
  
  statusDiv.textContent = 'Thinking...';
  statusDiv.className = 'status loading';
  
  try {
    const response = await fetch(`${API_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ question }),
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const data = await response.json();
    
    if (data.success) {
      addMessage('assistant', data.response);
      statusDiv.textContent = '';
      statusDiv.className = '';
    } else {
      addMessage('assistant', `Error: ${data.error || 'Unknown error'}`);
      statusDiv.textContent = 'Error occurred';
      statusDiv.className = 'status error';
    }
  } catch (error) {
    console.error('Chat API error:', error);
    const errorMsg = error instanceof Error ? error.message : 'Failed to connect to API server';
    addMessage('assistant', `Connection Error: ${errorMsg}. Please make sure the backend server is running on http://localhost:5000`);
    statusDiv.textContent = 'Connection error - Check console for details';
    statusDiv.className = 'status error';
  } finally {
    sendButton.disabled = false;
    questionInput.focus();
  }
}

// Event listeners
sendButton.addEventListener('click', sendMessage);

questionInput.addEventListener('keypress', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

// Check API health on load
async function checkHealth() {
  try {
    const response = await fetch(`${API_URL}/health`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    if (response.ok) {
      statusDiv.textContent = 'Connected';
      statusDiv.className = 'status connected';
      setTimeout(() => {
        statusDiv.textContent = '';
      }, 2000);
    } else {
      throw new Error(`Health check failed: ${response.status}`);
    }
  } catch (error) {
    console.error('API connection error:', error);
    const errorMsg = error instanceof Error ? error.message : 'Unknown error';
    statusDiv.textContent = `❌ API server not running - Backend not connected`;
    statusDiv.className = 'status error';
    // Show error message in chat
    chatContainer.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">⚠️</div>
        <div class="empty-state-text">Cannot connect to API server</div>
        <div class="empty-state-subtext" style="margin-top: 12px; font-size: 13px; color: var(--text-secondary);">
          <strong>Backend server is not running!</strong>
          <br><br>
          To start the backend server:
          <br>
          <code style="background: rgba(255,255,255,0.1); padding: 4px 8px; border-radius: 4px; display: inline-block; margin-top: 8px;">
            python backend/start.py
          </code>
          <br><br>
          Or from the project root:
          <br>
          <code style="background: rgba(255,255,255,0.1); padding: 4px 8px; border-radius: 4px; display: inline-block; margin-top: 8px;">
            cd backend && python start.py
          </code>
          <br><br>
          <small>Error: ${errorMsg}</small>
        </div>
      </div>
    `;
  }
}

// Load saved messages from server on page load
loadMessages().catch(err => console.error('Error loading messages:', err));

checkHealth();

// Focus input on load
questionInput.focus();

// Admin panel functionality
let selectedFile: File | null = null;
let adminPanelVisible = false;
let cachedPdfFiles: any[] = [];
let lastPdfListLoad: number = 0;
const PDF_CACHE_DURATION = 30000; // Cache for 30 seconds

// Upload/Replace PDF file
function uploadPdfFile(existingFilename: string, fileId: number | null | undefined) {
  // Create a hidden file input
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = '.pdf';
  input.style.display = 'none';
  
  input.addEventListener('change', async (e) => {
    const target = e.target as HTMLInputElement;
    if (target.files && target.files.length > 0) {
      const file = target.files[0];
      await uploadAndReplacePdf(file, existingFilename, fileId);
    }
    document.body.removeChild(input);
  });
  
  document.body.appendChild(input);
  input.click();
}

// Upload and replace PDF
async function uploadAndReplacePdf(file: File, existingFilename: string, fileId: number | null | undefined) {
  const formData = new FormData();
  formData.append('file', file);
  
  // Add flag to indicate this is a replacement
  if (fileId) {
    formData.append('replace_id', fileId.toString());
  } else {
    formData.append('replace_filename', existingFilename);
  }
  
  try {
    uploadStatus.textContent = `Uploading and replacing PDF "${existingFilename}"...`;
    uploadStatus.className = 'upload-status loading';
    
    const response = await fetch(`${API_URL}/upload`, {
      method: 'POST',
      body: formData,
    });
    
    const data = await response.json();
    
    if (data.success) {
      uploadStatus.textContent = `✓ Success! PDF replaced and processed`;
      uploadStatus.className = 'upload-status success';
      
      // Reload PDF list
      setTimeout(() => {
        loadPdfList();
        uploadStatus.textContent = '';
      }, 2000);
    } else {
      uploadStatus.textContent = `✗ Error: ${data.error || 'Upload failed'}`;
      uploadStatus.className = 'upload-status error';
    }
  } catch (error) {
    uploadStatus.textContent = `✗ Error: ${error instanceof Error ? error.message : 'Failed to upload'}`;
    uploadStatus.className = 'upload-status error';
  }
}

// View PDF file - opens in new tab using signed URL
async function viewPdf(fileId: number | null, filename: string) {
  try {
    let signedUrl: string | null = null;
    
    if (fileId !== null && fileId !== undefined && !isNaN(Number(fileId))) {
      // Use ID if available
      const apiUrl = `${API_URL}/files/${fileId}/pdf`;
      console.log(`Getting signed URL by ID: ID=${fileId}, filename=${filename}`);
      
      const response = await fetch(apiUrl);
      const data = await response.json();
      
      if (data.success && data.url) {
        signedUrl = data.url;
      }
    } else {
      // Fallback to filename
      const encodedFilename = encodeURIComponent(filename);
      const apiUrl = `${API_URL}/files/by-name/${encodedFilename}/pdf`;
      console.log(`Getting signed URL by filename: ${filename}`);
    
    const response = await fetch(apiUrl);
    const data = await response.json();
    
      if (data.success && data.url) {
        signedUrl = data.url;
      }
    }
    
    if (!signedUrl) {
      const errorMsg = 'Failed to get PDF URL';
      alert(`Failed to open PDF: ${errorMsg}`);
      console.error('PDF URL fetch failed:', errorMsg);
      return;
    }
    
    // Open signed URL directly in browser (works for private buckets)
    // Signed URLs are temporary but work just like public URLs
    window.open(signedUrl, '_blank');
  } catch (error) {
    console.error('Failed to open PDF:', error);
    alert(`Failed to open PDF: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
}

// Show PDF in modal
function showPdfModal(url: string, filename: string, fileId: number | null = null) {
  // Create modal container
  const modal = document.createElement('div');
  modal.className = 'pdf-viewer-modal';
  
  const deleteButtonHtml = fileId ? `
    <button class="delete-button" data-file-id="${fileId}" data-filename="${escapeHtml(filename)}">🗑️ Delete</button>
  ` : '';
  
  modal.innerHTML = `
    <div class="pdf-viewer-container">
      <div class="pdf-viewer-header">
        <h3>${escapeHtml(filename)}</h3>
        <div class="pdf-viewer-header-actions">
          ${deleteButtonHtml}
          <button class="close-button">×</button>
        </div>
      </div>
      <div class="pdf-viewer-content">
        <iframe src="${url}" class="pdf-viewer-iframe" frameborder="0"></iframe>
      </div>
    </div>
  `;
  
  document.body.appendChild(modal);
  
  // Close button handler
  const closeButton = modal.querySelector('.close-button');
  if (closeButton) {
    closeButton.addEventListener('click', () => {
      modal.remove();
    });
  }
  
  // Delete button handler
  if (fileId) {
    const deleteButton = modal.querySelector('.delete-button');
    if (deleteButton) {
      deleteButton.addEventListener('click', () => {
        deletePdfFile(fileId, filename, modal);
      });
    }
  }
  
  // Close on background click
  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      modal.remove();
    }
  });
}

// Setup PDF selection functionality
function setupPdfSelection(files: any[]) {
  const selectAllCheckbox = document.querySelector<HTMLInputElement>('#select-all-pdfs');
  const deleteSelectedButton = document.querySelector<HTMLButtonElement>('.delete-selected-button');
  const selectionCountSpan = document.querySelector<HTMLSpanElement>('.selection-count');
  
  if (!selectAllCheckbox || !deleteSelectedButton || !selectionCountSpan) {
    console.error('[SELECTION] Missing selection controls');
    return;
  }
  
  console.log('[SELECTION] Setting up selection for', files.length, 'files');
  
  const updateSelectionUI = () => {
    const checkboxes = document.querySelectorAll<HTMLInputElement>('.pdf-item-checkbox');
    const selectedCount = Array.from(checkboxes).filter(cb => cb.checked).length;
    const totalCount = checkboxes.length;
    
    console.log('[SELECTION] Selected:', selectedCount, 'of', totalCount);
    
    selectionCountSpan.textContent = `${selectedCount} selected`;
    deleteSelectedButton.disabled = selectedCount === 0;
    selectAllCheckbox.checked = selectedCount === totalCount && totalCount > 0;
    selectAllCheckbox.indeterminate = selectedCount > 0 && selectedCount < totalCount;
    
    // Add visual feedback to selected items
    const pdfItems = document.querySelectorAll('.pdf-gallery-item');
    pdfItems.forEach((item, index) => {
      const checkbox = item.querySelector<HTMLInputElement>('.pdf-item-checkbox');
      if (checkbox && checkbox.checked) {
        item.classList.add('selected');
      } else {
        item.classList.remove('selected');
      }
    });
  };
  
  // Select all checkbox handler with animation
  selectAllCheckbox.addEventListener('change', (e) => {
    console.log('[SELECTION] Select all toggled:', selectAllCheckbox.checked);
    const checkboxes = document.querySelectorAll<HTMLInputElement>('.pdf-item-checkbox');
    
    // Add animation effect
    selectAllCheckbox.parentElement?.classList.add('selecting');
    setTimeout(() => {
      selectAllCheckbox.parentElement?.classList.remove('selecting');
    }, 300);
    
    checkboxes.forEach(cb => cb.checked = selectAllCheckbox.checked);
    updateSelectionUI();
  });
  
  // Individual checkbox handlers
  const checkboxes = document.querySelectorAll<HTMLInputElement>('.pdf-item-checkbox');
  console.log('[SELECTION] Found', checkboxes.length, 'checkboxes');
  
  checkboxes.forEach((checkbox, index) => {
    checkbox.addEventListener('change', (e) => {
      console.log('[SELECTION] Checkbox', index, 'changed:', checkbox.checked);
      updateSelectionUI();
    });
  });
  
  // Delete selected button handler
  deleteSelectedButton.addEventListener('click', async () => {
    const selectedCheckboxes = Array.from(document.querySelectorAll<HTMLInputElement>('.pdf-item-checkbox:checked'));
    const selectedFiles = selectedCheckboxes.map(cb => ({
      id: parseInt(cb.getAttribute('data-file-id') || '0'),
      filename: cb.getAttribute('data-filename') || 'unknown'
    }));
    
    if (selectedFiles.length === 0) return;
    
    const fileList = selectedFiles.map(f => f.filename).join('\n  • ');
    if (!confirm(`Are you sure you want to delete ${selectedFiles.length} PDF(s)?\n\n  • ${fileList}\n\nThis action cannot be undone.`)) {
      return;
    }
    
    await deleteSelectedPdfs(selectedFiles);
  });
  
  updateSelectionUI();
}

// Delete multiple PDFs
async function deleteSelectedPdfs(files: { id: number; filename: string }[]) {
  const uploadStatus = document.querySelector<HTMLDivElement>('.upload-status')!;
  let successCount = 0;
  let failCount = 0;
  
  uploadStatus.textContent = `Deleting ${files.length} PDF(s)...`;
  uploadStatus.className = 'upload-status loading';
  
  for (const file of files) {
    try {
      const response = await fetch(`${API_URL}/files/${file.id}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    const data = await response.json();
    
    if (data.success) {
        successCount++;
      } else {
        failCount++;
        console.error(`Failed to delete ${file.filename}:`, data.error);
      }
    } catch (error) {
      failCount++;
      console.error(`Failed to delete ${file.filename}:`, error);
    }
      }
      
  // Clear cache and reload PDF list
  cachedPdfFiles = [];
  loadPdfList(true);
      
      // Show success message
  if (failCount === 0) {
    uploadStatus.textContent = `✓ Successfully deleted ${successCount} PDF(s)`;
      uploadStatus.className = 'upload-status success';
  } else {
    uploadStatus.textContent = `⚠ Deleted ${successCount} PDF(s), ${failCount} failed`;
    uploadStatus.className = 'upload-status error';
  }
  
      setTimeout(() => {
        uploadStatus.textContent = '';
        uploadStatus.className = '';
      }, 3000);
}

// Delete single PDF file (kept for compatibility)
async function deletePdfFile(fileId: number, filename: string, modal: HTMLElement | null = null) {
  await deleteSelectedPdfs([{ id: fileId, filename }]);
  if (modal) {
    modal.remove();
  }
}

// deletePdfFile is now used directly via event listeners, no need for global

// Load PDF list
async function loadPdfList(forceReload: boolean = false) {
  try {
    let files: any[] = [];
    
    // Use cache if available and not forcing reload
    if (!forceReload && cachedPdfFiles.length > 0) {
      console.log('[DEBUG] Using cached PDF list');
      files = cachedPdfFiles;
    } else {
      // Fetch from API
    pdfList.innerHTML = '<div class="loading">Loading PDFs...</div>';
    const response = await fetch(`${API_URL}/files`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const data = await response.json();
    
    console.log('[DEBUG] API response:', data);
    console.log('[DEBUG] Files count:', data.files?.length || 0);
    
    if (data.success && data.files && data.files.length > 0) {
        files = data.files;
        cachedPdfFiles = files;
        lastPdfListLoad = Date.now();
      } else {
        pdfList.innerHTML = `<div class="no-pdfs">No PDFs found.</div>`;
        return;
      }
    }
    
    if (files.length > 0) {
      // Store files array for later use
      
      // Update header with selection controls
      const pdfListPageHeader = document.querySelector('.pdf-list-page-header');
      if (pdfListPageHeader) {
        pdfListPageHeader.innerHTML = `
          <button class="back-button" id="back-to-admin-from-list">← Back to Admin</button>
          <div class="pdf-list-header-content">
            <h3 class="pdf-list-title">Uploaded PDFs</h3>
            <div class="pdf-selection-controls-inline">
              <div class="selection-info">
                <input type="checkbox" id="select-all-pdfs" class="pdf-select-checkbox" />
                <label for="select-all-pdfs">Select</label>
                <span class="selection-count">0 selected</span>
              </div>
              <button class="delete-selected-button" disabled>Delete Selected</button>
            </div>
          </div>
        `;
        
        // Re-attach back button handler
        const backButtonFromList = document.querySelector('#back-to-admin-from-list');
        if (backButtonFromList) {
          backButtonFromList.addEventListener('click', () => {
            showAdminDashboard();
          });
        }
      }
      
      pdfList.innerHTML = '<div class="pdf-gallery-grid">' + files.map((file: any, index: number) => {
        const fileId = file.id !== null && file.id !== undefined ? file.id : null;
        const filename = file.filename;
        const displayFilename = escapeHtml(filename);
        
        return `
        <div class="pdf-gallery-item ${fileId !== null ? 'selectable' : ''}" data-file-id="${fileId !== null ? fileId : ''}" data-filename="${filename}" data-index="${index}">
          ${fileId !== null ? `
          <div class="pdf-select-wrapper">
            <input type="checkbox" class="pdf-item-checkbox" data-file-id="${fileId}" data-filename="${escapeHtml(filename)}" />
          </div>
          ` : ''}
          <div class="pdf-gallery-content">
          <div class="pdf-gallery-thumbnail">
            <div class="pdf-thumbnail-icon">📄</div>
            <div class="pdf-thumbnail-overlay">
              <div class="pdf-thumbnail-status ${file.status === 'processed' ? 'status-processed' : 'status-processing'}">
                ${file.status === 'processed' ? '✓' : '⏳'}
              </div>
            </div>
          </div>
          <div class="pdf-gallery-info">
              <div class="pdf-gallery-header">
                <div class="pdf-gallery-name">${displayFilename}</div>
              </div>
            <div class="pdf-gallery-meta">
              ${file.pages_count ? `${file.pages_count} pages` : ''}
              ${file.file_size ? ` • ${formatFileSize(file.file_size)}` : ''}
            </div>
            <div class="pdf-gallery-date">
              ${file.uploaded_at ? new Date(file.uploaded_at).toLocaleDateString() : ''}
              </div>
            </div>
          </div>
        </div>
      `;
      }).join('') + '</div>';
      
      // Setup selection functionality
      setupPdfSelection(files);
      
      // Add click handlers to PDF gallery items
      const pdfItems = pdfList.querySelectorAll('.pdf-gallery-item');
      console.log(`Found ${pdfItems.length} PDF items, files array has ${files.length} items`);
      
      pdfItems.forEach((item, index) => {
        const file = files[index];
        const filename = item.getAttribute('data-filename') || 'document.pdf';
        const actualFileId = file?.id;
        
        // Get file URL and open in new tab when admin clicks
        const pdfContent = item.querySelector('.pdf-gallery-content');
        if (pdfContent) {
          pdfContent.addEventListener('click', async (e) => {
            // Don't open PDF if clicking on checkbox
            if ((e.target as HTMLElement).closest('.pdf-item-checkbox') || (e.target as HTMLElement).closest('.pdf-select-wrapper')) {
              return;
            }
          e.preventDefault();
          
          try {
            let publicUrl: string | null = null;
            
            // First, check if we already have the URL in metadata
            if (file.metadata?.public_url) {
              publicUrl = file.metadata.public_url;
              console.log(`Using public_url from metadata: ${publicUrl}`);
            } else {
              // Get URL from API
              if (actualFileId !== null && actualFileId !== undefined && !isNaN(Number(actualFileId))) {
              const response = await fetch(`${API_URL}/files/${actualFileId}/pdf`);
              const data = await response.json();
              
              if (data.success && data.url) {
                  publicUrl = data.url;
              }
            } else {
                // Fallback: try filename-based endpoint
                const encodedFilename = encodeURIComponent(filename);
                const response = await fetch(`${API_URL}/files/by-name/${encodedFilename}/pdf`);
                const data = await response.json();
                
                if (data.success && data.url) {
                  publicUrl = data.url;
                }
              }
            }
            
            // Get signed URL from backend (works for private buckets)
            // This is the standard approach - backend generates temporary signed URL
            const backendUrl = actualFileId !== null && actualFileId !== undefined && !isNaN(Number(actualFileId))
              ? `${API_URL}/files/${actualFileId}/pdf`
              : `${API_URL}/files/by-name/${encodeURIComponent(filename)}/pdf`;
            
            // Fetch signed URL from backend
            fetch(backendUrl)
              .then(response => {
                if (!response.ok) {
                  throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                return response.json();
              })
              .then(data => {
                if (data.success && data.url) {
                  // Open the signed URL directly in browser (works for private buckets)
                  // Signed URLs are temporary but work just like public URLs
                  window.open(data.url, '_blank');
              } else {
                  throw new Error(data.error || 'Failed to get PDF URL');
              }
              })
              .catch(error => {
                console.error('Failed to load PDF:', error);
                alert(`Failed to open PDF: ${error.message}`);
              });
          } catch (error) {
            console.error('Failed to open PDF:', error);
            alert(`Failed to open PDF: ${error instanceof Error ? error.message : 'Unknown error'}`);
          }
        });
        }
      });
    } else {
      console.log('[DEBUG] No files in response or empty array');
      console.log('[DEBUG] Response data:', data);
      pdfList.innerHTML = `<div class="no-pdfs">No PDFs found. 
        <br><small style="color: var(--text-secondary); margin-top: 8px; display: block;">
          Total: ${data.total || 0} files
          <br>Success: ${data.success ? 'Yes' : 'No'}
        </small>
      </div>`;
    }
  } catch (error) {
    console.error('Failed to load PDF list:', error);
    pdfList.innerHTML = `<div class="error">Failed to load PDFs: ${error instanceof Error ? error.message : 'Unknown error'}</div>`;
  }
}

function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// Show admin dashboard
function showAdminDashboard() {
  adminDashboard.style.display = 'block';
  pdfListPage.classList.remove('pdf-list-page-visible');
  pdfListPage.classList.add('pdf-list-page-hidden');
  window.location.hash = 'admin';
}

// Show PDF list page
function showPdfListPage() {
  adminDashboard.style.display = 'none';
  pdfListPage.classList.remove('pdf-list-page-hidden');
  pdfListPage.classList.add('pdf-list-page-visible');
  window.location.hash = 'pdfs';
  // Load PDFs (will use cache if recent)
  const now = Date.now();
  if (cachedPdfFiles.length === 0 || (now - lastPdfListLoad) > PDF_CACHE_DURATION) {
    loadPdfList(true); // Force reload
  } else {
    loadPdfList(false); // Use cache
  }
}

// Toggle admin panel
adminButton.addEventListener('click', () => {
  adminPanelVisible = !adminPanelVisible;
  if (adminPanelVisible) {
    chatContainer.style.display = 'none';
    adminPanel.classList.remove('admin-panel-hidden');
    adminPanel.classList.add('admin-panel-visible');
    showAdminDashboard(); // Show dashboard, not PDF list
  } else {
    chatContainer.style.display = 'flex';
    adminPanel.classList.remove('admin-panel-visible');
    adminPanel.classList.add('admin-panel-hidden');
  }
});

closeAdminButton.addEventListener('click', () => {
  adminPanelVisible = false;
  chatContainer.style.display = 'flex';
  adminPanel.classList.remove('admin-panel-visible');
  adminPanel.classList.add('admin-panel-hidden');
});

// Navigate to PDF list page
viewPdfsButton.addEventListener('click', () => {
  showPdfListPage();
});

// Navigate back to admin dashboard
backToAdminButton.addEventListener('click', () => {
  showAdminDashboard();
});

// Handle URL hash on page load and changes
function handleRoute() {
  const hash = window.location.hash.slice(1); // Remove the # symbol
  
  if (hash === 'admin') {
    adminPanelVisible = true;
    chatContainer.style.display = 'none';
    adminPanel.classList.remove('admin-panel-hidden');
    adminPanel.classList.add('admin-panel-visible');
    showAdminDashboard();
  } else if (hash === 'pdfs') {
    adminPanelVisible = true;
    chatContainer.style.display = 'none';
    adminPanel.classList.remove('admin-panel-hidden');
    adminPanel.classList.add('admin-panel-visible');
    showPdfListPage();
  }
}

// Listen for hash changes (back/forward navigation)
window.addEventListener('hashchange', handleRoute);

// Handle initial route on page load
handleRoute();


// File upload handling
pdfUpload.addEventListener('change', (e) => {
  const target = e.target as HTMLInputElement;
  if (target.files && target.files.length > 0) {
    selectedFile = target.files[0];
    const fileNameMain = document.querySelector<HTMLDivElement>('#file-name-main')!;
    fileNameMain.textContent = selectedFile.name;
    uploadButton.disabled = false;
    uploadStatus.textContent = '';
  }
});

uploadButton.addEventListener('click', async () => {
  if (!selectedFile) return;
  
  uploadButton.disabled = true;
  uploadStatus.textContent = 'Uploading and processing PDF...';
  uploadStatus.className = 'upload-status loading';
  
  const formData = new FormData();
  formData.append('file', selectedFile);
  
  try {
    const response = await fetch(`${API_URL}/upload`, {
      method: 'POST',
      body: formData,
    });
    
    // Check if response is ok
    if (!response.ok) {
      const errorText = await response.text();
      let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
      try {
        const errorData = JSON.parse(errorText);
        errorMessage = errorData.error || errorMessage;
      } catch {
        errorMessage = errorText || errorMessage;
      }
      throw new Error(errorMessage);
    }
    
    const data = await response.json();
    
    if (data.success) {
      uploadStatus.textContent = `✓ Success! Processed ${data.chunks_created} chunks from ${data.pages_processed} pages`;
      uploadStatus.className = 'upload-status success';
      
      // Reset form
      pdfUpload.value = '';
      const fileNameMain = document.querySelector<HTMLDivElement>('#file-name-main')!;
      fileNameMain.textContent = '';
      selectedFile = null;
      uploadButton.disabled = true;
      
      // Show success message in chat
      addMessage('assistant', `PDF "${data.filename}" has been successfully processed and added to the knowledge base. You can now ask questions about it!`);
      
      // Clear cache and refresh files list if we're on the PDF list page
      cachedPdfFiles = [];
      if (pdfListPage.classList.contains('pdf-list-page-visible')) {
        loadPdfList(true);
      }
    } else {
      uploadStatus.textContent = `✗ Error: ${data.error || 'Upload failed'}`;
      uploadStatus.className = 'upload-status error';
    }
  } catch (error) {
    uploadStatus.textContent = `✗ Error: ${error instanceof Error ? error.message : 'Failed to upload'}`;
    uploadStatus.className = 'upload-status error';
  } finally {
    uploadButton.disabled = false;
  }
});
