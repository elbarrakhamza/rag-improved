// API Configuration
// Utiliser l'URL de l'API en production, ou localhost en développement
const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://localhost:8000'
    : 'https://api-rag.stage.enset.top';

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
                mode: 'cors'
            });
            
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
        // Utiliser URLSearchParams pour form-data
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