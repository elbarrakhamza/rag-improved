// Main Application
const app = {
    init() {
        this.setupNavigation();
        this.setupLogout();
        this.loadDashboard();
        
        // Check API connection
        this.checkApiConnection();
        
        // Gérer la clé API
        this.handleApiKey();
    },

    handleApiKey() {
        // Vérifier si une clé API est dans l'URL (paramètre ?api_key=xxx)
        const urlParams = new URLSearchParams(window.location.search);
        const apiKeyParam = urlParams.get('api_key');
        
        if (apiKeyParam) {
            api.setApiKey(apiKeyParam);
            // Nettoyer l'URL
            window.history.replaceState({}, document.title, window.location.pathname);
            showToast('✅ API Key chargée depuis l\'URL', 'success', 3000);
        }
        
        // Si pas de clé, demander
        if (!api.getApiKey()) {
            setTimeout(() => this.showApiKeyModal(), 500);
        }
    },

    showApiKeyModal() {
        const key = prompt('🔑 Entrez votre clé API admin :');
        if (key) {
            api.setApiKey(key);
            this.checkApiConnection();
        } else {
            // Réessayer après 3 secondes
            setTimeout(() => this.showApiKeyModal(), 3000);
        }
    },

    setupNavigation() {
        const navItems = document.querySelectorAll('.nav-item');
        const tabs = document.querySelectorAll('.tab-content');
        const pageTitle = document.getElementById('pageTitle');
        
        navItems.forEach(item => {
            item.addEventListener('click', () => {
                navItems.forEach(n => n.classList.remove('active'));
                item.classList.add('active');
                
                const tabId = item.dataset.tab;
                tabs.forEach(t => t.classList.remove('active'));
                document.getElementById(`tab-${tabId}`).classList.add('active');
                
                const label = item.querySelector('.label').textContent;
                pageTitle.textContent = label;
                
                if (tabId === 'documents' && window.documentsManager) {
                    window.documentsManager.loadDocuments();
                }
                if (tabId === 'apikeys' && window.apiKeysManager) {
                    window.apiKeysManager.loadApiKeys();
                }
                if (tabId === 'feedback' && window.feedbackManager) {
                    window.feedbackManager.loadFeedback();
                    window.feedbackManager.loadStats();
                }
                if (tabId === 'cache' && window.cacheManager) {
                    window.cacheManager.loadStats();
                }
            });
        });

        document.getElementById('menuToggle').addEventListener('click', () => {
            document.getElementById('sidebar').classList.toggle('open');
        });

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
            if (confirm('Êtes-vous sûr de vouloir vous déconnecter ?')) {
                localStorage.removeItem('apiKey');
                document.getElementById('userRole').textContent = 'Non connecté';
                showToast('🔓 Déconnecté', 'info', 3000);
                setTimeout(() => this.showApiKeyModal(), 1000);
            }
        });
    },

    async checkApiConnection() {
        const statusElement = document.querySelector('.api-key-status span:last-child');
        const dotElement = document.querySelector('.dot');
        const roleElement = document.getElementById('userRole');
        
        try {
            const health = await api.health();
            dotElement.className = 'dot green';
            statusElement.textContent = '✅ Connecté';
            roleElement.textContent = '👑 Admin';
            showToast('✅ Connecté à l\'API', 'success', 2000);
            console.log('Health check:', health);
        } catch (error) {
            dotElement.className = 'dot red';
            statusElement.textContent = '❌ Déconnecté';
            roleElement.textContent = '⚠️ Erreur';
            showToast(`❌ Impossible de se connecter à l'API: ${error.message}`, 'error', 5000);
            console.error('API Connection error:', error);
        }
    },

    async loadDashboard() {
        try {
            // Documents count
            const docs = await api.getDocuments(1, 1);
            document.getElementById('statDocuments').textContent = docs.total || 0;
            
            // Cache stats
            const cacheStats = await api.getCacheStats();
            document.getElementById('statCache').textContent = cacheStats.total_cached || 0;
            
            // Top questions count
            const topQuestions = await api.getTopQuestions(1);
            document.getElementById('statFeedback').textContent = topQuestions.length || 0;
            
            // Chunks count (approx)
            const allDocs = await api.getDocuments(1, 100);
            document.getElementById('statChunks').textContent = '...';
            
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

// Initialization
document.addEventListener('DOMContentLoaded', () => {
    // Vérifier si les managers existent
    if (typeof api === 'undefined') {
        console.error('❌ API module not loaded');
        return;
    }
    
    // Initialiser l'application
    app.init();
});

// Exposer app globalement
window.app = app;