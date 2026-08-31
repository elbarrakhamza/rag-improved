// Main Application
const app = {
    init() {
        this.setupNavigation();
        this.setupLogout();
        this.loadDashboard();
        
        // Check API connection
        this.checkApiConnection();
    },

    setupNavigation() {
        const navItems = document.querySelectorAll('.nav-item');
        const tabs = document.querySelectorAll('.tab-content');
        const pageTitle = document.getElementById('pageTitle');
        
        navItems.forEach(item => {
            item.addEventListener('click', () => {
                // Update active nav
                navItems.forEach(n => n.classList.remove('active'));
                item.classList.add('active');
                
                // Show corresponding tab
                const tabId = item.dataset.tab;
                tabs.forEach(t => t.classList.remove('active'));
                document.getElementById(`tab-${tabId}`).classList.add('active');
                
                // Update title
                const label = item.querySelector('.label').textContent;
                pageTitle.textContent = label;
                
                // Trigger refresh for some tabs
                if (tabId === 'documents' && window.documentsManager) {
                    window.documentsManager.loadDocuments();
                }
                if (tabId === 'apikeys') {
                    // API keys will refresh on click
                }
                if (tabId === 'feedback') {
                    // Feedback will refresh on click
                }
                if (tabId === 'cache') {
                    // Cache stats will refresh on click
                }
            });
        });

        // Menu toggle for mobile
        document.getElementById('menuToggle').addEventListener('click', () => {
            document.getElementById('sidebar').classList.toggle('open');
        });

        // Close sidebar on outside click (mobile)
        document.addEventListener('click', (e) => {
            const sidebar = document.getElementById('sidebar');
            const toggle = document.getElementById('menuToggle');
            if (window.innerWidth <= 768) {
                if (!sidebar.contains(e.target) && !toggle.contains(e.target)) {
                    sidebar.classList.remove('open');
                }
            }
        });
    },

    setupLogout() {
        document.getElementById('logoutBtn').addEventListener('click', () => {
            if (confirm('Are you sure you want to logout?')) {
                localStorage.removeItem('apiKey');
                document.getElementById('apiKeyInput').value = '';
                // Reload to show login screen
                location.reload();
            }
        });
    },

    async checkApiConnection() {
        try {
            await api.health();
            document.querySelector('.dot').className = 'dot green';
            document.querySelector('.api-key-status span:last-child').textContent = 'Connected';
        } catch (error) {
            document.querySelector('.dot').className = 'dot red';
            document.querySelector('.api-key-status span:last-child').textContent = 'Disconnected';
            showToast('Cannot connect to API. Please check if the server is running.', 'error');
        }
    },

    async loadDashboard() {
        try {
            // Load stats
            const docs = await api.getDocuments(1, 1);
            document.getElementById('statDocuments').textContent = docs.total || 0;
            
            // Get cache stats for total cache items
            const cacheStats = await api.getCacheStats();
            document.getElementById('statCache').textContent = cacheStats.total_cached || 0;
            
            // Approximate chunks count from first document
            // In a real implementation, you'd have a dedicated endpoint
            const allDocs = await api.getDocuments(1, 100);
            let totalChunks = 0;
            // This is a placeholder - in production you'd have a proper endpoint
            document.getElementById('statChunks').textContent = '...';
            
            // Feedback count from top questions
            const topQuestions = await api.getTopQuestions(1);
            document.getElementById('statFeedback').textContent = topQuestions.length || 0;
            
        } catch (error) {
            console.error('Error loading dashboard:', error);
        }
    }
};

// Toast notification system
function showToast(message, type = 'info', duration = 5000) {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type}`;
    toast.classList.add('show');
    
    clearTimeout(toast._timeout);
    toast._timeout = setTimeout(() => {
        toast.classList.remove('show');
    }, duration);
}

// API Key input dialog (simple version)
function showApiKeyInput() {
    const key = prompt('Enter your API Key:');
    if (key) {
        api.setApiKey(key);
        location.reload();
    }
}

// Initialization
document.addEventListener('DOMContentLoaded', () => {
    // Check if API key is set
    if (!api.getApiKey()) {
        showApiKeyInput();
    }
    
    app.init();
});