import './style.css'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';

const app = document.querySelector<HTMLDivElement>('#admin-app')!;

app.innerHTML = `
  <div class="header">
    <h1 class="header-title">AFSC</h1>
    <p class="header-subtitle">Admin Panel</p>
  </div>
  
  <div class="admin-container glass-strong">
    <div class="admin-tabs">
      <button class="tab-button active" data-tab="upload">Upload PDF</button>
      <button class="tab-button" data-tab="files">View Files</button>
    </div>
    
    <div class="tab-content active" id="upload-tab">
      <div class="admin-panel">
        <h2>Upload Reference PDF</h2>
        <p class="admin-description">Upload PDF documents to add them to the knowledge base. The system will automatically process and chunk the content for search.</p>
        
        <div class="upload-area">
          <input 
            type="file" 
            id="pdf-upload" 
            accept=".pdf"
            style="display: none;"
          />
          <label for="pdf-upload" class="upload-label">
            <span class="upload-icon">📄</span>
            <span>Choose PDF file</span>
          </label>
          <span id="file-name" class="file-name"></span>
        </div>
        
        <button id="upload-button" class="upload-button" disabled>Upload & Process</button>
        
        <div id="upload-status" class="upload-status"></div>
      </div>
    </div>
    
    <div class="tab-content" id="files-tab">
      <div class="admin-panel">
        <h2>Uploaded PDFs</h2>
        <p class="admin-description" style="margin-bottom: 20px;">Click on any file below to see its details and preview.</p>
        <div class="files-container">
          <div id="files-list" class="files-list">
            <div class="loading">Loading files...</div>
          </div>
          <div id="file-preview" class="file-preview" style="display: none;">
            <div class="preview-header">
              <h3 id="preview-filename">File Preview</h3>
              <button id="close-preview" class="close-preview-btn">×</button>
            </div>
            <div class="preview-content">
              <div id="preview-info" class="preview-info">
                <div class="preview-placeholder">
                  <p>Select a file from the list to see its details</p>
                </div>
              </div>
              <div id="preview-actions" class="preview-actions"></div>
            </div>
          </div>
          <div id="preview-placeholder" class="file-preview-placeholder" style="display: block;">
            <div class="preview-placeholder-content">
              <div class="preview-placeholder-icon">📄</div>
              <p class="preview-placeholder-text">Select a file to preview</p>
              <p class="preview-placeholder-hint">Click on any file in the list to see its details</p>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <div class="admin-actions">
      <a href="/" class="back-link">← Back to Chat</a>
    </div>
  </div>
  
  <div id="pdf-viewer-modal" class="pdf-viewer-modal" style="display: none;">
    <div class="pdf-viewer-container">
      <div class="pdf-viewer-header">
        <h3 id="pdf-viewer-title">PDF Viewer</h3>
        <button id="close-pdf-viewer" class="close-button">×</button>
      </div>
      <iframe id="pdf-viewer-iframe" class="pdf-viewer-iframe"></iframe>
    </div>
  </div>
`;

const pdfUpload = document.querySelector<HTMLInputElement>('#pdf-upload')!;
const uploadButton = document.querySelector<HTMLButtonElement>('#upload-button')!;
const uploadStatus = document.querySelector<HTMLDivElement>('#upload-status')!;
const fileName = document.querySelector<HTMLSpanElement>('#file-name')!;

let selectedFile: File | null = null;

pdfUpload.addEventListener('change', (e) => {
  const target = e.target as HTMLInputElement;
  if (target.files && target.files.length > 0) {
    selectedFile = target.files[0];
    fileName.textContent = selectedFile.name;
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
      fileName.textContent = '';
      selectedFile = null;
      uploadButton.disabled = true;
      
      // Refresh files list if on files tab
      if (document.querySelector('#files-tab')?.classList.contains('active')) {
        loadFilesList();
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

// Tab switching
const tabButtons = document.querySelectorAll('.tab-button');
const tabContents = document.querySelectorAll('.tab-content');

tabButtons.forEach(button => {
  button.addEventListener('click', () => {
    const targetTab = button.getAttribute('data-tab');
    
    // Update buttons
    tabButtons.forEach(btn => btn.classList.remove('active'));
    button.classList.add('active');
    
    // Update content
    tabContents.forEach(content => content.classList.remove('active'));
    const targetContent = document.getElementById(`${targetTab}-tab`);
    if (targetContent) {
      targetContent.classList.add('active');
      
      // Load files when switching to files tab
      if (targetTab === 'files') {
        loadFilesList();
      }
    }
  });
});

// Load files list
async function loadFilesList() {
  const filesList = document.getElementById('files-list');
  if (!filesList) return;
  
  filesList.innerHTML = '<div class="loading">Loading files...</div>';
  
  try {
    const response = await fetch(`${API_URL}/files`);
    const data = await response.json();
    
    if (data.success && data.files && data.files.length > 0) {
      filesList.innerHTML = data.files.map((file: any) => {
        const date = new Date(file.uploaded_at).toLocaleDateString();
        const fileSize = file.file_size ? `${(file.file_size / 1024).toFixed(1)} KB` : 'Unknown';
        const canView = file.id !== null && file.id !== undefined;
        const fileDataJson = JSON.stringify(file).replace(/"/g, '&quot;');
        
        return `
          <div class="file-item glass-strong" data-file-id="${file.id || ''}" data-filename="${file.filename}" data-file-data="${fileDataJson}">
            <div class="file-info">
              <h3 class="file-name">${file.filename}</h3>
              <div class="file-meta">
                <span>📄 ${file.pages_count} pages</span>
                <span>📦 ${file.chunks_count} chunks</span>
                <span>💾 ${fileSize}</span>
                <span>📅 ${date}</span>
                <span class="status-badge status-${file.status}">${file.status}</span>
              </div>
            </div>
            ${canView ? `
              <button class="view-pdf-button" data-file-id="${file.id}" data-filename="${file.filename}">
                👁️ View PDF
              </button>
            ` : '<span class="no-view">File not available for viewing</span>'}
          </div>
        `;
      }).join('');
      
      // Add event listeners to view buttons
      document.querySelectorAll('.view-pdf-button').forEach(button => {
        button.addEventListener('click', (e) => {
          const target = e.target as HTMLButtonElement;
          const fileId = target.getAttribute('data-file-id');
          const filename = target.getAttribute('data-filename');
          if (fileId) {
            viewPDF(parseInt(fileId), filename || 'document.pdf');
          }
        });
      });
      
      // Add event listeners to file items for preview
      document.querySelectorAll('.file-item').forEach(item => {
        item.addEventListener('click', (e) => {
          // Don't trigger if clicking the view button
          if ((e.target as HTMLElement).closest('.view-pdf-button')) {
            return;
          }
          
          const fileItem = e.currentTarget as HTMLElement;
          const fileId = fileItem.getAttribute('data-file-id');
          const filename = fileItem.getAttribute('data-filename');
          const fileData = fileItem.getAttribute('data-file-data');
          
          if (fileData) {
            try {
              const data = JSON.parse(fileData);
              showFilePreview(data);
            } catch (err) {
              console.error('Failed to parse file data:', err);
            }
          }
        });
      });
    } else {
      filesList.innerHTML = '<div class="no-files">No PDFs uploaded yet.</div>';
    }
  } catch (error) {
    filesList.innerHTML = `<div class="error">Failed to load files: ${error instanceof Error ? error.message : 'Unknown error'}</div>`;
  }
}

// PDF Viewer
const pdfViewerModal = document.getElementById('pdf-viewer-modal');
const pdfViewerIframe = document.getElementById('pdf-viewer-iframe') as HTMLIFrameElement;
const pdfViewerTitle = document.getElementById('pdf-viewer-title');
const closePdfViewer = document.getElementById('close-pdf-viewer');

function viewPDF(fileId: number, filename: string) {
  if (!pdfViewerModal || !pdfViewerIframe || !pdfViewerTitle) return;
  
  pdfViewerTitle.textContent = filename;
  pdfViewerIframe.src = `${API_URL}/files/${fileId}/pdf`;
  pdfViewerModal.style.display = 'flex';
}

closePdfViewer?.addEventListener('click', () => {
  if (pdfViewerModal && pdfViewerIframe) {
    pdfViewerModal.style.display = 'none';
    pdfViewerIframe.src = '';
  }
});

// Close modal when clicking outside
pdfViewerModal?.addEventListener('click', (e) => {
  if (e.target === pdfViewerModal) {
    if (pdfViewerModal && pdfViewerIframe) {
      pdfViewerModal.style.display = 'none';
      pdfViewerIframe.src = '';
    }
  }
});

// File Preview Section
const filePreview = document.getElementById('file-preview');
const previewFilename = document.getElementById('preview-filename');
const previewInfo = document.getElementById('preview-info');
const previewActions = document.getElementById('preview-actions');
const closePreview = document.getElementById('close-preview');

function showFilePreview(file: any) {
  if (!filePreview || !previewFilename || !previewInfo || !previewActions) return;
  
  const date = new Date(file.uploaded_at).toLocaleDateString('en-US', { 
    year: 'numeric', 
    month: 'long', 
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
  const fileSize = file.file_size ? `${(file.file_size / 1024 / 1024).toFixed(2)} MB` : 'Unknown';
  const canView = file.id !== null && file.id !== undefined;
  
  previewFilename.textContent = file.filename;
  
  previewInfo.innerHTML = `
    <div class="preview-section">
      <h4>File Information</h4>
      <div class="preview-details">
        <div class="detail-row">
          <span class="detail-label">Filename:</span>
          <span class="detail-value">${file.filename}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Status:</span>
          <span class="status-badge status-${file.status}">${file.status}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Pages:</span>
          <span class="detail-value">${file.pages_count}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Chunks:</span>
          <span class="detail-value">${file.chunks_count}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">File Size:</span>
          <span class="detail-value">${fileSize}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Uploaded:</span>
          <span class="detail-value">${date}</span>
        </div>
      </div>
    </div>
    ${file.metadata && Object.keys(file.metadata).length > 0 ? `
    <div class="preview-section">
      <h4>Document Analysis</h4>
      <div class="preview-details">
        ${file.metadata.title ? `
        <div class="detail-row">
          <span class="detail-label">Title:</span>
          <span class="detail-value">${file.metadata.title}</span>
        </div>
        ` : ''}
        ${file.metadata.summary ? `
        <div class="detail-row full-width">
          <span class="detail-label">Summary:</span>
          <span class="detail-value">${file.metadata.summary}</span>
        </div>
        ` : ''}
        ${file.metadata.topics && Array.isArray(file.metadata.topics) && file.metadata.topics.length > 0 ? `
        <div class="detail-row full-width">
          <span class="detail-label">Topics:</span>
          <span class="detail-value">${file.metadata.topics.map((t: string) => `<span class="topic-tag">${t}</span>`).join('')}</span>
        </div>
        ` : ''}
        ${file.metadata.key_points && Array.isArray(file.metadata.key_points) && file.metadata.key_points.length > 0 ? `
        <div class="detail-row full-width">
          <span class="detail-label">Key Points:</span>
          <ul class="key-points-list">
            ${file.metadata.key_points.map((point: string) => `<li>${point}</li>`).join('')}
          </ul>
        </div>
        ` : ''}
      </div>
    </div>
    ` : ''}
  `;
  
  previewActions.innerHTML = canView ? `
    <button class="preview-action-btn primary" data-preview-file-id="${file.id}" data-preview-filename="${file.filename}">
      👁️ View Full PDF
    </button>
  ` : `
    <div class="preview-no-action">PDF preview not available for this file</div>
  `;
  
  // Add event listener to preview action button
  const previewActionBtn = previewActions.querySelector('.preview-action-btn');
  if (previewActionBtn && canView) {
    previewActionBtn.addEventListener('click', () => {
      viewPDF(file.id, file.filename);
    });
  }
  
  filePreview.style.display = 'block';
  
  // Hide placeholder
  const placeholder = document.getElementById('preview-placeholder');
  if (placeholder) {
    placeholder.style.display = 'none';
  }
  
  // Highlight selected file
  document.querySelectorAll('.file-item').forEach(item => {
    item.classList.remove('selected');
  });
  document.querySelector(`[data-file-id="${file.id || ''}"][data-filename="${file.filename}"]`)?.classList.add('selected');
}

closePreview?.addEventListener('click', () => {
  if (filePreview) {
    filePreview.style.display = 'none';
  }
  const placeholder = document.getElementById('preview-placeholder');
  if (placeholder) {
    placeholder.style.display = 'block';
  }
  document.querySelectorAll('.file-item').forEach(item => {
    item.classList.remove('selected');
  });
});

