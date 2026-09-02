// API Configuration
let API_BASE = localStorage.getItem('apiBase') || 'https://api-rag.stage.enset.top';

// Store API key (from localStorage)
let apiKey = localStorage.getItem('apiKey') || '';

// API Client
const api = {
    setApiKey(key) {
        apiKey = key;
        localStorage.setItem('apiKey', key);
    },

    getApiKey() {
        return apiKey;
    },

    setApiBase(url) {
        API_BASE = url;
        localStorage.setItem('apiBase', url);
    },

    getApiBase() {
        return API_BASE;
    },

    async request(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };
    
    if (apiKey) {
        headers['X-API-Key'] = apiKey;
    }
    
    try {
        const response = await fetch(url, {
            ...options,
            headers,
            mode: 'cors',
            credentials: 'include'
        });
        
        // Gérer les erreurs d'authentification
        if (response.status === 401 || response.status === 403) {
            // Ne supprimer la clé que si c'est un endpoint critique
            // Pour les feedbacks, on veut juste retourner une erreur
            if (endpoint.includes('/admin/') || endpoint === '/query') {
                localStorage.removeItem('apiKey');
                localStorage.removeItem('apiBase');
                throw new Error('Invalid API Key');
            }
            // Pour les endpoints non-critiques, juste throw une erreur
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || 'Unauthorized');
        }
        
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }
        
        return response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
},

    // Health Check
    async health() {
        return this.request('/health');
    },

    // Query
    async query(question, useCache = true, topK = null) {
        return this.request('/query', {
            method: 'POST',
            body: JSON.stringify({
                question,
                use_cache: useCache,
                top_k: topK
            })
        });
    },

    // Admin: Upload
    async upload(formData) {
        const response = await fetch(`${API_BASE}/admin/upload`, {
            method: 'POST',
            headers: {
                'X-API-Key': apiKey
            },
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }
        
        return response.json();
    },

    // Admin: Task Status
    async getTaskStatus(taskId) {
        return this.request(`/admin/task/${taskId}`);
    },

    // Admin: Documents
    async getDocuments(page = 1, limit = 50, search = '') {
        const params = new URLSearchParams({ page, limit });
        if (search) params.append('search', search);
        return this.request(`/admin/documents?${params}`);
    },

    async deleteDocument(sourceFile) {
        return this.request(`/admin/documents/${encodeURIComponent(sourceFile)}`, {
            method: 'DELETE'
        });
    },

    // Admin: API Keys
    async getApiKeys() {
        return this.request('/admin/api-keys');
    },

    async generateApiKey(role, description) {
        const formData = new URLSearchParams();
        formData.append('role', role);
        formData.append('description', description || '');
        
        return this.request('/admin/api-keys/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: formData.toString()
        });
    },

    async toggleApiKey(keyId) {
        return this.request(`/admin/api-keys/${keyId}/toggle`, {
            method: 'POST'
        });
    },

    async deleteApiKey(keyId) {
        return this.request(`/admin/api-keys/${keyId}`, {
            method: 'DELETE'
        });
    },

    // Admin: Cache
    async getCacheStats() {
        return this.request('/admin/cache/stats');
    },

    async clearCache() {
        return this.request('/admin/cache/clear', {
            method: 'DELETE'
        });
    },

    // Feedback
    async submitFeedback(data) {
        return this.request('/feedback/submit', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    async getQuestionStats(question) {
        return this.request(`/feedback/stats/question?question=${encodeURIComponent(question)}`);
    },

    async getTopQuestions(limit = 10, daysBack = 30) {
        return this.request(`/feedback/top-questions?limit=${limit}&days_back=${daysBack}`);
    },

    async getLowPerformingQuestions(minFrequency = 3, maxAvgScore = 3.0, daysBack = 30) {
        return this.request(
            `/feedback/low-performing-questions?min_frequency=${minFrequency}&max_avg_score=${maxAvgScore}&days_back=${daysBack}`
        );
    }
};

// Task polling
class TaskPoller {
    constructor(taskId, onProgress, onComplete, onError) {
        this.taskId = taskId;
        this.onProgress = onProgress;
        this.onComplete = onComplete;
        this.onError = onError;
        this.polling = false;
        this.interval = 1000;
        this.timeout = 300000;
        this.startTime = Date.now();
    }

    start() {
        this.polling = true;
        this.poll();
    }

    stop() {
        this.polling = false;
    }

    async poll() {
        if (!this.polling) return;

        try {
            const status = await api.getTaskStatus(this.taskId);
            
            if (status.status === 'completed' || status.status === 'failed') {
                this.polling = false;
                if (status.status === 'completed') {
                    this.onComplete(status);
                } else {
                    this.onError(status.message || 'Task failed');
                }
                return;
            }

            if (this.onProgress) {
                this.onProgress(status);
            }

            if (Date.now() - this.startTime > this.timeout) {
                this.polling = false;
                this.onError('Task timeout');
                return;
            }

            setTimeout(() => this.poll(), this.interval);
        } catch (error) {
            this.polling = false;
            this.onError(error.message);
        }
    }
}

// Exporter pour utilisation globale
window.api = api;
window.TaskPoller = TaskPoller;