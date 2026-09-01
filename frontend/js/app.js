// Main Application
const app = {
    init() {
        // Vérifier si déjà connecté
        const savedKey = localStorage.getItem('apiKey');
        const savedUrl = localStorage.getItem('apiBase');
        
        if (savedKey && savedUrl) {
            api.setApiKey(savedKey);
            api.setApiBase(savedUrl);
            this.showApp();
            this.checkApiConnection();
        } else {
            this.showLogin();
        }
        
        // Setup login
        document.getElementById('loginForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleLogin();
        });
        
        // Setup logout
        document.getElementById('logoutBtn').addEventListener('click', () => {
            this.handleLogout();
        });
        
        // Setup navigation après chargement de l'app
        this.setupNavigation();
    },

    showLogin() {
        document.getElementById('loginPage').style.display = 'flex';
        document.getElementById('appContainer').style.display = 'none';
        document.getElementById('loginError').style.display = 'none';
    },

    showApp() {
        document.getElementById('loginPage').style.display = 'none';
        document.getElementById('appContainer').style.display = 'flex';
    },

    async handleLogin() {
        const apiKeyInput = document.getElementById('apiKeyInput');
        const apiUrlInput = document.getElementById('apiUrlInput');
        const errorDiv = document.getElementById('loginError');
        
        const key = apiKeyInput.value.trim();
        const url = apiUrlInput.value.trim();
        
        if (!key) {
            errorDiv.textContent = '❌ Veuillez entrer une clé API';
            errorDiv.style.display = 'block';
            return;
        }
        
        if (!url) {
            errorDiv.textContent = '❌ Veuillez entrer l\'URL de l\'API';
            errorDiv.style.display = 'block';
            return;
        }
        
        // Tester la connexion
        try {
            api.setApiKey(key);
            api.setApiBase(url);
            
            const result = await api.health();
            
            if (result.status === 'ok' || result.status === 'degraded') {
                // Connexion réussie
                errorDiv.style.display = 'none';
                this.showApp();
                this.checkApiConnection();
                showToast('✅ Connexion réussie !', 'success', 3000);
            } else {
                errorDiv.textContent = '❌ API non disponible. Vérifiez l\'URL.';
                errorDiv.style.display = 'block';
            }
        } catch (error) {
            errorDiv.textContent = `❌ Erreur de connexion: ${error.message}`;
            errorDiv.style.display = 'block';
        }
    },

    handleLogout() {
        if (confirm('Voulez-vous vraiment vous déconnecter ?')) {
            localStorage.removeItem('apiKey');
            localStorage.removeItem('apiBase');
            this.showLogin();
            document.getElementById('apiKeyInput').value = '';
            showToast('🔓 Déconnecté', 'info', 3000);
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
                
                // Rafraîchir les onglets
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

    async checkApiConnection() {
        const statusElement = document.querySelector('.api-key-status span:last-child');
        const dotElement = document.querySelector('.dot');
        const roleElement = document.getElementById('userRole');
        
        try {
            const health = await api.health();
            dotElement.className = 'dot green';
            statusElement.textContent = '✅ Connecté';
            roleElement.textContent = '👑 Admin';
        } catch (error) {
            dotElement.className = 'dot red';
            statusElement.textContent = '❌ Déconnecté';
            roleElement.textContent = '⚠️ Erreur';
            showToast(`❌ Erreur de connexion: ${error.message}`, 'error', 5000);
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

window.app = app;