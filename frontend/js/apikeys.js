// API Keys Management
const apiKeysManager = {
    init() {
        this.loadApiKeys();
        
        document.getElementById('generateKeyBtn').addEventListener('click', () => {
            const form = document.getElementById('generateKeyForm');
            form.style.display = form.style.display === 'none' ? 'block' : 'none';
        });
        
        document.getElementById('cancelGenerateBtn').addEventListener('click', () => {
            document.getElementById('generateKeyForm').style.display = 'none';
        });
        
        document.getElementById('confirmGenerateBtn').addEventListener('click', () => {
            this.generateKey();
        });
    },

    async loadApiKeys() {
        const container = document.getElementById('apiKeysList');
        container.innerHTML = '<p class="loading-text">Loading API keys...</p>';
        
        try {
            const keys = await api.getApiKeys();
            
            if (keys.length === 0) {
                container.innerHTML = '<p class="loading-text">No API keys found</p>';
                return;
            }
            
            container.innerHTML = keys.map(key => `
                <div class="apikey-item">
                    <div class="apikey-info">
                        <div>
                            <span class="apikey-role role-${key.role}">${key.role}</span>
                            <span class="apikey-status ${key.is_active ? 'active' : 'inactive'}">
                                ${key.is_active ? '✅ Active' : '❌ Inactive'}
                            </span>
                        </div>
                        <div style="margin-top: 4px;">
                            <span class="apikey-key">${key.key_hash ? key.key_hash.substring(0, 20) + '...' : 'N/A'}</span>
                            <span style="font-size: 0.8rem; color: #666; margin-left: 8px;">
                                ${key.description || 'No description'}
                            </span>
                        </div>
                        <div style="font-size: 0.75rem; color: #999; margin-top: 4px;">
                            Created: ${new Date(key.created_at).toLocaleString()}
                            ${key.last_used ? ` | Last used: ${new Date(key.last_used).toLocaleString()}` : ''}
                        </div>
                    </div>
                    <div class="apikey-actions">
                        <button class="btn ${key.is_active ? 'btn-danger' : 'btn-success'}" data-id="${key.id}" data-toggle>
                            ${key.is_active ? '🔴 Deactivate' : '🟢 Activate'}
                        </button>
                        <button class="btn btn-danger" data-id="${key.id}" data-delete>🗑️</button>
                    </div>
                </div>
            `).join('');

            // Toggle handlers
            container.querySelectorAll('[data-toggle]').forEach(el => {
                el.addEventListener('click', async (e) => {
                    const id = e.target.dataset.id;
                    await this.toggleKey(id);
                });
            });

            // Delete handlers
            container.querySelectorAll('[data-delete]').forEach(el => {
                el.addEventListener('click', async (e) => {
                    const id = e.target.dataset.id;
                    if (confirm('Delete this API key?')) {
                        await this.deleteKey(id);
                    }
                });
            });
            
        } catch (error) {
            container.innerHTML = `<p class="loading-text">Error loading API keys: ${error.message}</p>`;
        }
    },

    async generateKey() {
        const role = document.getElementById('newKeyRole').value;
        const description = document.getElementById('newKeyDesc').value || 'No description';
        
        try {
            const result = await api.generateApiKey(role, description);
            showToast(`API Key generated: ${result.api_key}`, 'success');
            document.getElementById('generateKeyForm').style.display = 'none';
            this.loadApiKeys();
        } catch (error) {
            showToast(`Error generating key: ${error.message}`, 'error');
        }
    },

    async toggleKey(id) {
        try {
            await api.toggleApiKey(id);
            showToast('API key toggled', 'success');
            this.loadApiKeys();
        } catch (error) {
            showToast(`Error toggling key: ${error.message}`, 'error');
        }
    },

    async deleteKey(id) {
        try {
            await api.deleteApiKey(id);
            showToast('API key deleted', 'success');
            this.loadApiKeys();
        } catch (error) {
            showToast(`Error deleting key: ${error.message}`, 'error');
        }
    }
};

// Initialize API keys manager when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    apiKeysManager.init();
});