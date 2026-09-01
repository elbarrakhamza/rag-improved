// Main Application
const app = {
    init() {
        console.log('🚀 Application initialisée');
        
        // Vérifier si déjà connecté
        const savedKey = localStorage.getItem('apiKey');
        const savedUrl = localStorage.getItem('apiBase');
        
        if (savedKey && savedUrl) {
            api.setApiKey(savedKey);
            api.setApiBase(savedUrl);
            this.verifyApiKey(savedKey, savedUrl);
        } else {
            this.showLogin();
        }
        
        // Setup login - utiliser addEventListener proprement
        const loginForm = document.getElementById('loginForm');
        if (loginForm) {
            // Supprimer les anciens listeners
            const newForm = loginForm.cloneNode(true);
            loginForm.parentNode.replaceChild(newForm, loginForm);
            
            newForm.addEventListener('submit', (e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log('🔑 Formulaire de connexion soumis');
                this.handleLogin();
            });
        }
        
        // Setup logout
        const logoutBtn = document.getElementById('logoutBtn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => {
                this.handleLogout();
            });
        }
        
        // Setup navigation après chargement de l'app
        this.setupNavigation();
    },

    showLogin() {
        console.log('📱 Affichage de la page de connexion');
        const loginPage = document.getElementById('loginPage');
        const appContainer = document.getElementById('appContainer');
        const errorDiv = document.getElementById('loginError');
        
        if (loginPage) loginPage.style.display = 'flex';
        if (appContainer) appContainer.style.display = 'none';
        if (errorDiv) errorDiv.style.display = 'none';
        
        // Vider le champ de clé pour forcer une nouvelle saisie
        const apiKeyInput = document.getElementById('apiKeyInput');
        if (apiKeyInput) apiKeyInput.value = '';
    },

    showApp() {
        console.log('📱 Affichage de l\'application');
        const loginPage = document.getElementById('loginPage');
        const appContainer = document.getElementById('appContainer');
        
        if (loginPage) loginPage.style.display = 'none';
        if (appContainer) appContainer.style.display = 'flex';
    },

    async verifyApiKey(key, url) {
        console.log('🔍 Vérification de la clé API...');
        try {
            api.setApiKey(key);
            api.setApiBase(url);
            
            // Tester avec un endpoint protégé
            const result = await api.getCacheStats();
            console.log('✅ Clé valide:', result);
            
            this.showApp();
            this.checkApiConnection();
            this.loadDashboard();
            showToast('✅ Connexion réussie !', 'success', 3000);
            
        } catch (error) {
            console.error('❌ Clé invalide:', error.message);
            localStorage.removeItem('apiKey');
            localStorage.removeItem('apiBase');
            this.showLogin();
            
            const errorDiv = document.getElementById('loginError');
            if (errorDiv) {
                errorDiv.textContent = '❌ Clé API invalide. Veuillez réessayer.';
                errorDiv.style.display = 'block';
            }
            document.getElementById('apiKeyInput').value = '';
        }
    },

    async handleLogin() {
        console.log('🔑 Tentative de connexion...');
        
        const apiKeyInput = document.getElementById('apiKeyInput');
        const apiUrlInput = document.getElementById('apiUrlInput');
        const errorDiv = document.getElementById('loginError');
        
        const key = apiKeyInput ? apiKeyInput.value.trim() : '';
        const url = apiUrlInput ? apiUrlInput.value.trim() : 'https://api-rag.stage.enset.top';
        
        // Validation
        if (!key) {
            if (errorDiv) {
                errorDiv.textContent = '❌ Veuillez entrer une clé API';
                errorDiv.style.display = 'block';
            }
            showToast('❌ Veuillez entrer une clé API', 'error', 3000);
            return;
        }
        
        if (!url) {
            if (errorDiv) {
                errorDiv.textContent = '❌ Veuillez entrer l\'URL de l\'API';
                errorDiv.style.display = 'block';
            }
            showToast('❌ Veuillez entrer l\'URL de l\'API', 'error', 3000);
            return;
        }
        
        // Désactiver le bouton pendant la vérification
        const loginBtn = document.querySelector('.btn-login');
        if (loginBtn) {
            loginBtn.disabled = true;
            loginBtn.textContent = '⏳ Vérification...';
        }
        
        try {
            api.setApiKey(key);
            api.setApiBase(url);
            
            // Tester avec admin/cache/stats
            const result = await api.getCacheStats();
            console.log('✅ Connexion réussie:', result);
            
            // Succès
            if (errorDiv) errorDiv.style.display = 'none';
            this.showApp();
            this.checkApiConnection();
            this.loadDashboard();
            showToast('✅ Connexion réussie !', 'success', 3000);
            
        } catch (error) {
            console.error('❌ Erreur de connexion:', error.message);
            
            // Échec
            if (errorDiv) {
                errorDiv.textContent = `❌ ${error.message}`;
                errorDiv.style.display = 'block';
            }
            showToast(`❌ ${error.message}`, 'error', 5000);
            
            // Nettoyer les credentials
            localStorage.removeItem('apiKey');
            localStorage.removeItem('apiBase');
            api.setApiKey('');
            
            // Réactiver le champ pour nouvelle saisie
            if (apiKeyInput) {
                apiKeyInput.value = '';
                apiKeyInput.focus();
            }
            
        } finally {
            // Réactiver le bouton
            if (loginBtn) {
                loginBtn.disabled = false;
                loginBtn.textContent = '🔓 Se connecter';
            }
        }
    },

    handleLogout() {
        if (confirm('Voulez-vous vraiment vous déconnecter ?')) {
            console.log('🚪 Déconnexion');
            localStorage.removeItem('apiKey');
            localStorage.removeItem('apiBase');
            api.setApiKey('');
            this.showLogin();
            
            const apiKeyInput = document.getElementById('apiKeyInput');
            if (apiKeyInput) {
                apiKeyInput.value = '';
                apiKeyInput.focus();
            }
            
            const errorDiv = document.getElementById('loginError');
            if (errorDiv) errorDiv.style.display = 'none';
            
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
                const targetTab = document.getElementById(`tab-${tabId}`);
                if (targetTab) targetTab.classList.add('active');
                
                const label = item.querySelector('.label');
                if (label && pageTitle) {
                    pageTitle.textContent = label.textContent;
                }
                
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

        const menuToggle = document.getElementById('menuToggle');
        if (menuToggle) {
            menuToggle.addEventListener('click', () => {
                document.getElementById('sidebar').classList.toggle('open');
            });
        }

        document.addEventListener('click', (e) => {
            const sidebar = document.getElementById('sidebar');
            const toggle = document.getElementById('menuToggle');
            if (window.innerWidth <= 768) {
                if (sidebar && toggle && !sidebar.contains(e.target) && !toggle.contains(e.target)) {
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
            await api.health();
            if (dotElement) dotElement.className = 'dot green';
            if (statusElement) statusElement.textContent = '✅ Connecté';
            if (roleElement) roleElement.textContent = '👑 Admin';
        } catch (error) {
            if (dotElement) dotElement.className = 'dot red';
            if (statusElement) statusElement.textContent = '❌ Déconnecté';
            if (roleElement) roleElement.textContent = '⚠️ Erreur';
            showToast(`❌ Erreur de connexion: ${error.message}`, 'error', 5000);
        }
    },

    async loadDashboard() {
        try {
            const docs = await api.getDocuments(1, 1);
            const statDocuments = document.getElementById('statDocuments');
            if (statDocuments) statDocuments.textContent = docs.total || 0;
            
            const cacheStats = await api.getCacheStats();
            const statCache = document.getElementById('statCache');
            if (statCache) statCache.textContent = cacheStats.total_cached || 0;
            
            const topQuestions = await api.getTopQuestions(1);
            const statFeedback = document.getElementById('statFeedback');
            if (statFeedback) statFeedback.textContent = topQuestions.length || 0;
            
        } catch (error) {
            console.error('Error loading dashboard:', error);
        }
    }
};

// Toast notification system
function showToast(message, type = 'info', duration = 5000) {
    const toast = document.getElementById('toast');
    if (!toast) return;
    
    toast.textContent = message;
    toast.className = `toast ${type}`;
    toast.classList.add('show');
    
    clearTimeout(toast._timeout);
    toast._timeout = setTimeout(() => {
        toast.classList.remove('show');
    }, duration);
}

// Initialization - attendre que le DOM soit chargé
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        console.log('📄 DOM chargé, initialisation...');
        app.init();
    });
} else {
    console.log('📄 DOM déjà chargé, initialisation...');
    app.init();
}

// Exposer app globalement
window.app = app;