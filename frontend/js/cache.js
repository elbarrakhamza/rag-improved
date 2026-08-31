// Cache Management
const cacheManager = {
    init() {
        this.loadStats();
        
        document.getElementById('refreshCacheBtn').addEventListener('click', () => {
            this.loadStats();
        });
        
        document.getElementById('clearCacheBtn').addEventListener('click', () => {
            if (confirm('Clear all cached data?')) {
                this.clearCache();
            }
        });
    },

    async loadStats() {
        try {
            const stats = await api.getCacheStats();
            
            document.getElementById('cacheStatus').textContent = stats.enabled ? '🟢 Online' : '🔴 Offline';
            document.getElementById('cacheEmbeddings').textContent = stats.cached_embeddings || 0;
            document.getElementById('cacheAnswers').textContent = stats.cached_answers || 0;
            document.getElementById('cacheTotal').textContent = stats.total_cached || 0;
            
            if (stats.enabled) {
                document.getElementById('cacheStatus').style.color = '#4CAF50';
            } else {
                document.getElementById('cacheStatus').style.color = '#f44336';
            }
            
        } catch (error) {
            document.getElementById('cacheStatus').textContent = '❌ Error';
            document.getElementById('cacheStatus').style.color = '#f44336';
            showToast(`Error loading cache stats: ${error.message}`, 'error');
        }
    },

    async clearCache() {
        try {
            await api.clearCache();
            showToast('Cache cleared successfully', 'success');
            this.loadStats();
        } catch (error) {
            showToast(`Error clearing cache: ${error.message}`, 'error');
        }
    }
};

// Initialize cache manager when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    cacheManager.init();
});