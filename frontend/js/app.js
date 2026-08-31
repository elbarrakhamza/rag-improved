// Main Application
const app = {
    init() {
        this.setupNavigation();
        this.setupLogout();
        this.loadDashboard();
        
        // Check API connection
        this.checkApiConnection();
        
        // Gérer la clé API depuis l'URL ou localStorage
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
            showToast('API Key chargée depuis l\'URL', 'success');
        }
        
        // Si pas de clé, demander
        if (!api.getApiKey()) {
            setTimeout(() => this.showApiKeyModal(), 500);
        }
    },

    showApiKeyModal() {
        const key = prompt('Entrez votre clé API admin :');
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
                if (tabId === 'apikeys') {
                    // Refresh API keys
                }
                if (tabId === 'feedback') {
                    // Refresh feedback
                }
                if (tabId === 'cache') {
                    // Refresh cache stats
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
                showToast('Déconnecté', 'info');
                setTimeout(() => this.showApiKeyModal(), 1000);
            }
        });
    },

    async checkApiConnection() {
        const statusElement = document.querySelector('.api-key-status span:last-child');
        const dotElement = document.querySelector('.dot');
        
        try {
            await api.health();
            dotElement.className = 'dot green';
            statusElement.textContent = 'Connecté';
            document.getElementById('userRole').textContent = 'Admin';
            showToast('✅ Connecté à l\'API', 'success', 2000);
        } catch (error) {
            dotElement.className = 'dot red';
            statusElement.textContent = 'Déconnecté';
            document.getElementById('userRole').textContent = '❌ Erreur';
            showToast('❌ Impossible de se connecter à l\'API', 'error');
        }
    },

    async loadDashboard() {
        try {
            const docs = await api.getDocuments(1, 1);
            document.getElementById('statDocuments').textContent = docs.total || 0;
            
            const cacheStats = await api.getCacheStats();
            document.getElementById('statCache').textContent = cacheStats.total_cached || 0;
            
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

// Initialization
document.addEventListener('DOMContentLoaded', () => {
    app.init();
});