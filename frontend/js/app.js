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
        
        // Setup login
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

        if (window.notificationsManager) {
    window.notificationsManager.init();
}
        
        // Setup navigation
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
        // Ne pas essayer de charger les données ici
        try {
            api.setApiKey(key);
            api.setApiBase(url);
            
            // Tester avec un endpoint protégé
            const result = await api.getCacheStats();
            console.log('✅ Clé valide:', result);
            
            this.showApp();
            this.checkApiConnection();
            
            // Charger le dashboard APRÈS la connexion réussie
            setTimeout(() => {
                this.loadDashboard();
                this.loadFeedbackData();
            }, 500);
            
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
            const apiKeyInput = document.getElementById('apiKeyInput');
            if (apiKeyInput) apiKeyInput.value = '';
        }
    },

    async handleLogin() {
        console.log('🔑 Tentative de connexion...');
        
        const apiKeyInput = document.getElementById('apiKeyInput');
        const errorDiv = document.getElementById('loginError');
        
        const key = apiKeyInput ? apiKeyInput.value.trim() : '';
        // URL fixe - pas de champ dans le formulaire
        const url = 'https://api-rag.stage.enset.top';
        
        if (!key) {
            if (errorDiv) {
                errorDiv.textContent = '❌ Veuillez entrer une clé API';
                errorDiv.style.display = 'block';
            }
            showToast('❌ Veuillez entrer une clé API', 'error', 3000);
            return;
        }
        
        const loginBtn = document.querySelector('.btn-login');
        if (loginBtn) {
            loginBtn.disabled = true;
            loginBtn.textContent = '⏳ Vérification...';
        }
        
        try {
            api.setApiKey(key);
            api.setApiBase(url);
            
            const result = await api.getCacheStats();
            console.log('✅ Connexion réussie:', result);
            
            if (errorDiv) errorDiv.style.display = 'none';
            this.showApp();
            this.checkApiConnection();
            
            // Charger le dashboard APRÈS la connexion
            setTimeout(() => {
                this.loadDashboard();
                this.loadFeedbackData();
            }, 500);
            
            showToast('✅ Connexion réussie !', 'success', 3000);
            
        } catch (error) {
            console.error('❌ Erreur de connexion:', error.message);
            
            if (errorDiv) {
                errorDiv.textContent = `❌ ${error.message}`;
                errorDiv.style.display = 'block';
            }
            showToast(`❌ ${error.message}`, 'error', 5000);
            
            localStorage.removeItem('apiKey');
            localStorage.removeItem('apiBase');
            api.setApiKey('');
            
            if (apiKeyInput) {
                apiKeyInput.value = '';
                apiKeyInput.focus();
            }
            
        } finally {
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
                
                // Rafraîchir les données selon l'onglet
                if (tabId === 'documents' && window.documentsManager) {
                    setTimeout(() => window.documentsManager.loadDocuments(), 100);
                }
                if (tabId === 'apikeys' && window.apiKeysManager) {
                    setTimeout(() => window.apiKeysManager.loadApiKeys(), 100);
                }
                if (tabId === 'feedback' && window.feedbackManager) {
                    setTimeout(() => {
                        window.feedbackManager.loadFeedback();
                        window.feedbackManager.loadStats();
                    }, 100);
                }
                if (tabId === 'cache' && window.cacheManager) {
                    setTimeout(() => window.cacheManager.loadStats(), 100);
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
        console.log('📊 Chargement du dashboard...');
        try {
            const docs = await api.getDocuments(1, 1);
            const statDocuments = document.getElementById('statDocuments');
            if (statDocuments) statDocuments.textContent = docs.total || 0;
            
            const cacheStats = await api.getCacheStats();
            const statCache = document.getElementById('statCache');
            if (statCache) statCache.textContent = cacheStats.total_cached || 0;
            
            // Récupérer le nombre de feedbacks
            try {
                const topQuestions = await api.getTopQuestions(5);
                const statFeedback = document.getElementById('statFeedback');
                if (statFeedback) statFeedback.textContent = topQuestions.length || 0;
            } catch (e) {
                console.warn('Erreur chargement feedback stats:', e);
            }
            
            console.log('✅ Dashboard chargé');
        } catch (error) {
            console.error('❌ Erreur chargement dashboard:', error);
            // Ne pas afficher d'erreur à l'utilisateur
        }
    },

    async loadFeedbackData() {
        console.log('💬 Chargement des feedbacks...');
        try {
            if (window.feedbackManager) {
                await window.feedbackManager.loadTopQuestions();
                await window.feedbackManager.loadLowPerforming();
            }
            console.log('✅ Feedbacks chargés');
        } catch (error) {
            console.error('❌ Erreur chargement feedbacks:', error);
            // Ne pas afficher d'erreur à l'utilisateur
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

// Initialization
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        console.log('📄 DOM chargé, initialisation...');
        app.init();
    });
} else {
    console.log('📄 DOM déjà chargé, initialisation...');
    app.init();
}

window.app = app;