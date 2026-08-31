// Upload Management
const uploadManager = {
    files: [],
    currentTaskId: null,

    init() {
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        
        // Drag & Drop
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });

        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            this.handleFiles(e.dataTransfer.files);
        });

        fileInput.addEventListener('change', (e) => {
            this.handleFiles(e.target.files);
        });

        // Form submission
        document.getElementById('metadataForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.uploadFiles();
        });
    },

    handleFiles(fileList) {
        for (const file of fileList) {
            if (file.name.endsWith('.zip') || 
                file.name.endsWith('.pdf') || 
                file.name.endsWith('.txt') || 
                file.name.endsWith('.md') || 
                file.name.endsWith('.markdown')) {
                this.files.push(file);
            } else {
                showToast(`File ${file.name} not supported`, 'warning');
            }
        }
        this.renderFileList();
    },

    renderFileList() {
        const container = document.getElementById('fileList');
        if (this.files.length === 0) {
            container.innerHTML = '';
            return;
        }
        
        container.innerHTML = this.files.map((file, index) => `
            <div class="file-item">
                <span class="file-name">${file.name}</span>
                <span class="file-size">(${(file.size / 1024).toFixed(1)} KB)</span>
                <span class="file-remove" data-index="${index}">✕</span>
            </div>
        `).join('');

        container.querySelectorAll('.file-remove').forEach(el => {
            el.addEventListener('click', (e) => {
                const index = parseInt(e.target.dataset.index);
                this.files.splice(index, 1);
                this.renderFileList();
            });
        });
    },

    async uploadFiles() {
        if (this.files.length === 0) {
            showToast('Please select files to upload', 'warning');
            return;
        }

        const formData = new FormData();
        
        // Add files
        for (const file of this.files) {
            formData.append('files', file);
        }

        // Add metadata
        formData.append('brand', document.getElementById('metaBrand').value);
        formData.append('elevator_model', document.getElementById('metaModel').value);
        formData.append('document_type', document.getElementById('metaType').value);
        formData.append('document_version', document.getElementById('metaVersion').value || 'unknown');
        formData.append('visibility', document.getElementById('metaVisibility').value);
        formData.append('use_smart_pdf', document.getElementById('optSmartPDF').checked);
        formData.append('use_vision_llm', document.getElementById('optVisionLLM').checked);
        formData.append('skip_embedding', document.getElementById('optSkipEmbedding').checked);

        // Show progress
        const progressDiv = document.getElementById('uploadProgress');
        progressDiv.style.display = 'block';
        document.getElementById('uploadBtn').disabled = true;

        try {
            const result = await api.upload(formData);
            this.currentTaskId = result.task_id;
            
            showToast(`Upload started: ${result.files_count} files`, 'success');
            
            // Start polling
            this.pollTask(result.task_id);
            
        } catch (error) {
            showToast(`Upload failed: ${error.message}`, 'error');
            progressDiv.style.display = 'none';
            document.getElementById('uploadBtn').disabled = false;
        }
    },

    pollTask(taskId) {
        const poller = new TaskPoller(
            taskId,
            (status) => {
                this.updateProgress(status);
            },
            (status) => {
                this.onTaskComplete(status);
            },
            (error) => {
                showToast(`Task failed: ${error}`, 'error');
                document.getElementById('uploadBtn').disabled = false;
                document.getElementById('uploadProgress').style.display = 'none';
            }
        );
        poller.start();
    },

    updateProgress(status) {
        const total = status.total || 1;
        const progress = status.progress || 0;
        const percent = Math.round((progress / total) * 100);
        
        document.getElementById('progressFill').style.width = `${percent}%`;
        document.getElementById('progressMessage').textContent = status.message || 'Processing...';
        
        const statusDiv = document.getElementById('taskStatus');
        statusDiv.innerHTML = `
            <div>Status: ${status.status}</div>
            <div>Progress: ${progress}/${total}</div>
            <div>Mode: ${status.mode || 'production'}</div>
        `;
    },

    onTaskComplete(status) {
        const progressDiv = document.getElementById('uploadProgress');
        progressDiv.querySelector('.progress-fill').style.width = '100%';
        document.getElementById('progressMessage').textContent = status.message || 'Complete!';
        
        const statusDiv = document.getElementById('taskStatus');
        statusDiv.innerHTML = `
            <div style="color: #4CAF50;">✅ ${status.message}</div>
            <div>Chunks: ${status.chunks_count || status.chunks_inserted || 0}</div>
            ${status.chunks_file ? `<div>File: ${status.chunks_file}</div>` : ''}
        `;
        
        document.getElementById('uploadBtn').disabled = false;
        
        setTimeout(() => {
            progressDiv.style.display = 'none';
            // Clear files
            this.files = [];
            this.renderFileList();
            // Refresh documents
            if (window.documentsManager) {
                window.documentsManager.loadDocuments();
            }
        }, 5000);
    }
};

// Initialize upload manager when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    uploadManager.init();
});