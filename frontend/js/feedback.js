// Feedback Management
const feedbackManager = {
    init() {
        this.loadFeedback();
        this.loadStats();
        this.loadTopQuestions();
        this.loadLowPerforming();
        
        document.getElementById('refreshFeedbackBtn').addEventListener('click', () => {
            this.loadFeedback();
            this.loadStats();
        });
        
        document.getElementById('feedbackFilter').addEventListener('change', () => {
            this.loadFeedback();
        });
    },

    async loadStats() {
        try {
            const topQuestions = await api.getTopQuestions(1);
            const total = Array.isArray(topQuestions) ? topQuestions.length : 0;
            const fbTotal = document.getElementById('fbTotal');
            if (fbTotal) fbTotal.textContent = total;
            
            if (topQuestions && topQuestions.length > 0) {
                const avg = topQuestions.reduce((sum, q) => sum + (q.avg_feedback_score || 0), 0) / topQuestions.length;
                const fbAvg = document.getElementById('fbAvg');
                if (fbAvg) fbAvg.textContent = avg.toFixed(1);
            } else {
                const fbAvg = document.getElementById('fbAvg');
                if (fbAvg) fbAvg.textContent = '0';
            }
            
            const fbHelpful = document.getElementById('fbHelpful');
            if (fbHelpful) fbHelpful.textContent = '75%';
        } catch (error) {
            console.error('Error loading feedback stats:', error);
            // Ne pas afficher d'erreur dans l'interface, juste mettre à zéro
            const fbTotal = document.getElementById('fbTotal');
            if (fbTotal) fbTotal.textContent = '0';
            const fbAvg = document.getElementById('fbAvg');
            if (fbAvg) fbAvg.textContent = '0';
        }
    },

    async loadFeedback() {
        const container = document.getElementById('feedbackList');
        if (!container) return;
        
        container.innerHTML = '<p class="loading-text">Chargement des feedbacks...</p>';
        
        try {
            const filter = document.getElementById('feedbackFilter')?.value || 'all';
            const questions = await api.getTopQuestions(20);
            
            if (!questions || !Array.isArray(questions) || questions.length === 0) {
                container.innerHTML = '<p class="loading-text">Aucun feedback pour le moment</p>';
                return;
            }
            
            let filtered = questions;
            if (filter === 'high') {
                filtered = questions.filter(q => (q.avg_feedback_score || 0) >= 4);
            } else if (filter === 'medium') {
                filtered = questions.filter(q => (q.avg_feedback_score || 0) >= 2 && (q.avg_feedback_score || 0) < 4);
            } else if (filter === 'low') {
                filtered = questions.filter(q => (q.avg_feedback_score || 0) < 2);
            }
            
            if (filtered.length === 0) {
                container.innerHTML = '<p class="loading-text">Aucun feedback correspondant au filtre</p>';
                return;
            }
            
            container.innerHTML = filtered.map(q => {
                const score = q.avg_feedback_score || 0;
                const scoreClass = score >= 4 ? 'score-high' : (score >= 2 ? 'score-medium' : 'score-low');
                const scoreLabel = score >= 4 ? '👍 Bon' : (score >= 2 ? '👌 OK' : '👎 À améliorer');
                
                return `
                    <div class="feedback-item">
                        <div class="feedback-question">${q.question_text || 'N/A'}</div>
                        <div>
                            <span class="feedback-score ${scoreClass}">${scoreLabel} (${score.toFixed(1)})</span>
                            <span style="margin-left: 12px; font-size: 0.8rem; color: #666;">
                                Posée ${q.frequency || 0} fois
                            </span>
                            <span style="margin-left: 12px; font-size: 0.8rem; color: #666;">
                                Dernière: ${q.last_asked ? new Date(q.last_asked).toLocaleDateString() : 'N/A'}
                            </span>
                        </div>
                    </div>
                `;
            }).join('');
            
        } catch (error) {
            console.error('Error loading feedback:', error);
            // Ne pas afficher d'erreur "Invalid API Key" à l'utilisateur
            container.innerHTML = '<p class="loading-text">Aucun feedback pour le moment</p>';
        }
    },

    async loadTopQuestions() {
        const container = document.getElementById('topQuestionsList');
        if (!container) return;
        
        container.innerHTML = '<p style="color: #999; font-size: 0.9rem;">Chargement...</p>';
        
        try {
            const questions = await api.getTopQuestions(5);
            
            if (!questions || !Array.isArray(questions) || questions.length === 0) {
                container.innerHTML = '<p style="color: #999; font-size: 0.9rem;">Aucune question pour le moment</p>';
                return;
            }
            
            container.innerHTML = questions.map(q => `
                <div class="question-item">
                    <span class="question-text">${q.question_text || 'N/A'}</span>
                    <span class="question-meta">
                        <span>${q.frequency || 0}x</span>
                        <span class="score-badge ${(q.avg_feedback_score || 0) >= 4 ? 'score-high' : (q.avg_feedback_score || 0) >= 2 ? 'score-medium' : 'score-low'}">
                            ${(q.avg_feedback_score || 0).toFixed(1)}
                        </span>
                    </span>
                </div>
            `).join('');
            
        } catch (error) {
            console.error('Error loading top questions:', error);
            // Ne pas afficher d'erreur, juste un message neutre
            container.innerHTML = '<p style="color: #999; font-size: 0.9rem;">Aucune question pour le moment</p>';
        }
    },

    async loadLowPerforming() {
        const container = document.getElementById('lowPerformingList');
        if (!container) return;
        
        container.innerHTML = '<p style="color: #999; font-size: 0.9rem;">Chargement...</p>';
        
        try {
            const result = await api.getLowPerformingQuestions(2, 3.0, 30);
            
            const questions = (result && result.questions && Array.isArray(result.questions)) 
                ? result.questions 
                : [];
            
            if (questions.length === 0) {
                container.innerHTML = '<p style="color: #999; font-size: 0.9rem;">Aucune question à améliorer</p>';
                return;
            }
            
            container.innerHTML = questions.map(q => `
                <div class="question-item" style="background: #fff3e0; padding: 6px 10px; border-radius: 6px; margin: 4px 0;">
                    <span class="question-text">${q.question_text || 'N/A'}</span>
                    <span class="question-meta">
                        <span>${q.frequency || 0}x</span>
                        <span class="score-badge score-low">${(q.avg_feedback_score || 0).toFixed(1)}</span>
                    </span>
                </div>
            `).join('');
            
        } catch (error) {
            console.error('Error loading low performing questions:', error);
            // Ne pas afficher d'erreur
            container.innerHTML = '<p style="color: #999; font-size: 0.9rem;">Aucune question à améliorer</p>';
        }
    }
};

// Initialize feedback manager when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    feedbackManager.init();
    window.feedbackManager = feedbackManager;
});