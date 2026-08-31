// Documents Management
const documentsManager = {
    currentPage: 1,
    totalPages: 0,
    searchTerm: '',

    init() {
        this.loadDocuments();
        
        document.getElementById('refreshDocsBtn').addEventListener('click', () => {
            this.loadDocuments();
        });
        
        document.getElementById('docSearch').addEventListener('input', (e) => {
            this.searchTerm = e.target.value;
            this.currentPage = 1;
            this.loadDocuments();
        });
    },

    async loadDocuments() {
        const container = document.getElementById('documentsList');
        container.innerHTML = '<p class="loading-text">Loading documents...</p>';
        
        try {
            const data = await api.getDocuments(this.currentPage, 50, this.searchTerm);
            
            if (data.documents.length === 0) {
                container.innerHTML = '<p class="loading-text">No documents found</p>';
                return;
            }
            
            container.innerHTML = data.documents.map(doc => `
                <div class="doc-item">
                    <div class="doc-info">
                        <div class="doc-name">${doc.source_file}</div>
                        <div class="doc-meta">
                            <span>🏷️ ${doc.brand || 'N/A'}</span>
                            <span>📦 ${doc.model || 'N/A'}</span>
                            <span>📄 ${doc.type || 'N/A'}</span>
                            <span>📌 ${doc.version || 'N/A'}</span>
                            <span class="visibility-tag ${doc.visibility === 'private' ? 'private' : 'public'}">
                                ${doc.visibility || 'public'}
                            </span>
                        </div>
                    </div>
                    <div class="doc-actions">
                        <button class="btn btn-danger" data-file="${doc.source_file}">🗑️ Delete</button>
                    </div>
                </div>
            `).join('');

            // Delete handlers
            container.querySelectorAll('[data-file]').forEach(el => {
                el.addEventListener('click', async (e) => {
                    const file = e.target.dataset.file;
                    if (confirm(`Delete "${file}"?`)) {
                        await this.deleteDocument(file);
                    }
                });
            });

            // Pagination
            const total = data.total || 0;
            this.totalPages = Math.ceil(total / 50);
            this.renderPagination();
            
        } catch (error) {
            container.innerHTML = `<p class="loading-text">Error loading documents: ${error.message}</p>`;
        }
    },

    renderPagination() {
        const container = document.getElementById('docPagination');
        if (this.totalPages <= 1) {
            container.innerHTML = '';
            return;
        }
        
        let html = '';
        for (let i = 1; i <= Math.min(this.totalPages, 10); i++) {
            html += `<button class="${i === this.currentPage ? 'active' : ''}" data-page="${i}">${i}</button>`;
        }
        container.innerHTML = html;
        
        container.querySelectorAll('[data-page]').forEach(el => {
            el.addEventListener('click', (e) => {
                this.currentPage = parseInt(e.target.dataset.page);
                this.loadDocuments();
            });
        });
    },

    async deleteDocument(sourceFile) {
        try {
            await api.deleteDocument(sourceFile);
            showToast(`Document "${sourceFile}" deleted`, 'success');
            this.loadDocuments();
        } catch (error) {
            showToast(`Error deleting document: ${error.message}`, 'error');
        }
    }
};

// Initialize documents manager when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    documentsManager.init();
    window.documentsManager = documentsManager;
});