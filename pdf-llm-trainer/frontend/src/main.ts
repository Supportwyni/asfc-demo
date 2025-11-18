import './style.css'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

const app = document.querySelector<HTMLDivElement>('#app')!;

app.innerHTML = `
  <div class="header">
    <h1 class="header-title">ASFC</h1>
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

let messages: ChatMessage[] = [];

function addMessage(role: 'user' | 'assistant', content: string) {
  messages.push({ role, content });
  renderMessages();
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
  // Escape HTML first
  let formatted = escapeHtml(text);
  
  // Convert double newlines to paragraph breaks
  formatted = formatted.replace(/\n\n+/g, '</p><p>');
  
  // Convert single newlines to <br>
  formatted = formatted.replace(/\n/g, '<br>');
  
  // Wrap in paragraph tags
  if (formatted && !formatted.startsWith('<p>')) {
    formatted = '<p>' + formatted + '</p>';
  }
  
  // Clean up empty paragraphs
  formatted = formatted.replace(/<p><\/p>/g, '');
  formatted = formatted.replace(/<p><br><\/p>/g, '<p></p>');
  
  return formatted;
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
    statusDiv.textContent = `API server not running - Make sure backend is started on port 5000`;
    statusDiv.className = 'status error';
    // Show error message in chat
    chatContainer.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">⚠️</div>
        <div class="empty-state-text">Cannot connect to API server</div>
        <div class="empty-state-subtext" style="margin-top: 12px; font-size: 13px; color: var(--text-secondary);">
          Please make sure the backend server is running on http://localhost:5000
          <br>Run: <code style="background: rgba(255,255,255,0.1); padding: 2px 6px; border-radius: 4px;">python -m backend.start</code>
        </div>
      </div>
    `;
  }
}

checkHealth();

// Focus input on load
questionInput.focus();

// Admin panel functionality
let selectedFile: File | null = null;
let adminPanelVisible = false;

// Toggle admin panel
adminButton.addEventListener('click', () => {
  adminPanelVisible = !adminPanelVisible;
  if (adminPanelVisible) {
    chatContainer.style.display = 'none';
    adminPanel.classList.remove('admin-panel-hidden');
    adminPanel.classList.add('admin-panel-visible');
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
      
      // Refresh files list
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
