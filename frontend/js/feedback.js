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
            // Get stats from top questions
            const topQuestions = await api.getTopQuestions(1);
            const lowPerforming = await api.getLowPerformingQuestions();
            
            const total = topQuestions.length + lowPerforming.length;
            document.getElementById('fbTotal').textContent = total;
            
            // Calculate average from top questions
            if (topQuestions.length > 0) {
                const avg = topQuestions.reduce((sum, q) => sum + (q.avg_feedback_score || 0), 0) / topQuestions.length;
                document.getElementById('fbAvg').textContent = avg.toFixed(1);
            } else {
                document.getElementById('fbAvg').textContent = '0';
            }
            
            document.getElementById('fbHelpful').textContent = '75%'; // Placeholder
        } catch (error) {
            console.error('Error loading feedback stats:', error);
        }
    },

    async loadFeedback() {
        const container = document.getElementById('feedbackList');
        container.innerHTML = '<p class="loading-text">Loading feedback...</p>';
        
        try {
            const filter = document.getElementById('feedbackFilter').value;
            // Get top questions with their feedback
            const questions = await api.getTopQuestions(20);
            
            if (questions.length === 0) {
                container.innerHTML = '<p class="loading-text">No feedback yet</p>';
                return;
            }
            
            // Filter based on score
            let filtered = questions;
            if (filter === 'high') {
                filtered = questions.filter(q => (q.avg_feedback_score || 0) >= 4);
            } else if (filter === 'medium') {
                filtered = questions.filter(q => (q.avg_feedback_score || 0) >= 2 && (q.avg_feedback_score || 0) < 4);
            } else if (filter === 'low') {
                filtered = questions.filter(q => (q.avg_feedback_score || 0) < 2);
            }
            
            if (filtered.length === 0) {
                container.innerHTML = '<p class="loading-text">No feedback matching filter</p>';
                return;
            }
            
            container.innerHTML = filtered.map(q => {
                const score = q.avg_feedback_score || 0;
                const scoreClass = score >= 4 ? 'score-high' : (score >= 2 ? 'score-medium' : 'score-low');
                const scoreLabel = score >= 4 ? '👍 Good' : (score >= 2 ? '👌 OK' : '👎 Needs improvement');
                
                return `
                    <div class="feedback-item">
                        <div class="feedback-question">${q.question_text || 'N/A'}</div>
                        <div>
                            <span class="feedback-score ${scoreClass}">${scoreLabel} (${score.toFixed(1)})</span>
                            <span style="margin-left: 12px; font-size: 0.8rem; color: #666;">
                                Asked ${q.frequency || 0} times
                            </span>
                            <span style="margin-left: 12px; font-size: 0.8rem; color: #666;">
                                Last: ${q.last_asked ? new Date(q.last_asked).toLocaleDateString() : 'N/A'}
                            </span>
                        </div>
                    </div>
                `;
            }).join('');
            
        } catch (error) {
            container.innerHTML = `<p class="loading-text">Error loading feedback: ${error.message}</p>`;
        }
    },

    async loadTopQuestions() {
        const container = document.getElementById('topQuestionsList');
        container.innerHTML = '<p style="color: #999; font-size: 0.9rem;">Loading...</p>';
        
        try {
            const questions = await api.getTopQuestions(5);
            
            if (questions.length === 0) {
                container.innerHTML = '<p style="color: #999; font-size: 0.9rem;">No questions yet</p>';
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
            container.innerHTML = `<p style="color: #999; font-size: 0.9rem;">Error: ${error.message}</p>`;
        }
    },

    async loadLowPerforming() {
        const container = document.getElementById('lowPerformingList');
        container.innerHTML = '<p style="color: #999; font-size: 0.9rem;">Loading...</p>';
        
        try {
            const questions = await api.getLowPerformingQuestions(2, 3.0, 30);
            
            if (questions.length === 0) {
                container.innerHTML = '<p style="color: #999; font-size: 0.9rem;">No low performing questions</p>';
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
            container.innerHTML = `<p style="color: #999; font-size: 0.9rem;">Error: ${error.message}</p>`;
        }
    }
};

// Initialize feedback manager when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    feedbackManager.init();
});