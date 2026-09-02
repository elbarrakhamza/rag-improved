// Tasks Management
const tasksManager = {
    tasks: [],
    currentPage: 1,
    limit: 20,

    init() {
        this.loadTasks();
        
        document.getElementById('refreshTasksBtn').addEventListener('click', () => {
            this.loadTasks();
        });
        
        // Polling automatique toutes les 30 secondes
        setInterval(() => {
            this.loadTasks(true); // silent refresh
        }, 30000);
    },

    async loadTasks(silent = false) {
        const container = document.getElementById('tasksList');
        if (!container) return;
        
        if (!silent) {
            container.innerHTML = '<p class="loading-text">Chargement des tâches...</p>';
        }
        
        try {
            const tasks = await api.getTasks(this.limit, (this.currentPage - 1) * this.limit);
            this.tasks = tasks;
            this.renderTasks(tasks);
        } catch (error) {
            if (!silent) {
                container.innerHTML = `<p class="loading-text">Erreur de chargement: ${error.message}</p>`;
            }
            console.error('Error loading tasks:', error);
        }
    },

    renderTasks(tasks) {
        const container = document.getElementById('tasksList');
        if (!container) return;
        
        if (!tasks || tasks.length === 0) {
            container.innerHTML = '<p class="loading-text">Aucune tâche trouvée</p>';
            return;
        }
        
        container.innerHTML = tasks.map(task => {
            const statusClass = `status-${task.status}`;
            const files = Array.isArray(task.files) ? task.files : JSON.parse(task.files);
            const options = task.options || {};
            const mode = options.mode || 'auto';
            const chunks = task.chunks ? (Array.isArray(task.chunks) ? task.chunks : JSON.parse(task.chunks)) : null;
            const chunkCount = chunks ? chunks.length : 0;
            
            return `
                <div class="task-item" data-task-id="${task.id}">
                    <div class="task-info">
                        <div class="task-id">📄 Tâche: ${task.id.substring(0, 8)}...</div>
                        <div>
                            <span class="task-status ${statusClass}">${task.status}</span>
                            <span style="margin-left: 12px; font-size: 0.8rem; color: #666;">
                                Mode: <strong>${mode}</strong>
                            </span>
                            <span style="margin-left: 12px; font-size: 0.8rem; color: #666;">
                                Fichiers: ${files.length}
                            </span>
                            ${chunkCount > 0 ? `<span style="margin-left: 12px; font-size: 0.8rem; color: #666;">Chunks: ${chunkCount}</span>` : ''}
                        </div>
                        <div class="task-meta">
                            <span>📅 ${new Date(task.created_at).toLocaleString()}</span>
                            <span>🔄 ${new Date(task.updated_at).toLocaleString()}</span>
                            ${task.error_message ? `<span style="color: #c62828;">❌ ${task.error_message}</span>` : ''}
                        </div>
                        ${chunks && task.status !== 'COMPLETED' && task.status !== 'CANCELLED' && task.status !== 'FAILED' ? `
                            <div class="task-chunks-preview">
                                <details>
                                    <summary style="cursor: pointer; font-weight: 500; color: #1a73e8;">
                                        📝 Aperçu des chunks (${chunks.length})
                                    </summary>
                                    <pre>${JSON.stringify(chunks.slice(0, 2), null, 2)}${chunks.length > 2 ? '\n... (autres chunks)' : ''}</pre>
                                </details>
                            </div>
                        ` : ''}
                    </div>
                    <div class="task-actions">
                        ${this.getActions(task)}
                    </div>
                </div>
            `;
        }).join('');
        
        // Attacher les événements
        container.querySelectorAll('[data-action]').forEach(el => {
            el.addEventListener('click', (e) => {
                const action = el.dataset.action;
                const taskId = el.closest('.task-item').dataset.taskId;
                this.handleAction(action, taskId);
            });
        });
    },

    getActions(task) {
        const actions = [];
        const status = task.status;
        
        // Visualiser les chunks
        if (task.chunks && (status === 'CHUNKS_GENERATED' || status === 'CHUNKS_MODIFIED' || status === 'EMBEDDING_IN_PROGRESS')) {
            actions.push(`<button class="btn btn-secondary" data-action="view-chunks">👁️ Voir</button>`);
        }
        
        // Modifier les chunks (uniquement si en attente de validation)
        if (status === 'CHUNKS_GENERATED' || status === 'CHUNKS_MODIFIED') {
            actions.push(`<button class="btn btn-primary" data-action="edit-chunks">✏️ Modifier</button>`);
            actions.push(`<button class="btn btn-success" data-action="validate">✅ Valider</button>`);
        }
        
        // Annuler (si pas encore terminé)
        if (status !== 'COMPLETED' && status !== 'CANCELLED' && status !== 'FAILED') {
            actions.push(`<button class="btn btn-danger" data-action="cancel">❌ Annuler</button>`);
        }
        
        // Relancer (si échec)
        if (status === 'FAILED') {
            actions.push(`<button class="btn btn-warning" data-action="retry">🔄 Relancer</button>`);
        }
        
        return actions.join('');
    },

    async handleAction(action, taskId) {
        switch(action) {
            case 'view-chunks':
                await this.viewChunks(taskId);
                break;
            case 'edit-chunks':
                await this.editChunks(taskId);
                break;
            case 'validate':
                await this.validateTask(taskId);
                break;
            case 'cancel':
                await this.cancelTask(taskId);
                break;
            case 'retry':
                await this.retryTask(taskId);
                break;
        }
    },

    async viewChunks(taskId) {
        try {
            const chunks = await api.getTaskChunks(taskId);
            this.showModal('Aperçu des chunks', this.formatChunksForDisplay(chunks), true);
        } catch (error) {
            showToast(`Erreur: ${error.message}`, 'error');
        }
    },

    async editChunks(taskId) {
        try {
            const chunks = await api.getTaskChunks(taskId);
            const content = JSON.stringify(chunks, null, 2);
            this.showModal('Modifier les chunks', content, false, async (newContent) => {
                try {
                    const newChunks = JSON.parse(newContent);
                    if (!Array.isArray(newChunks)) {
                        throw new Error('Le contenu doit être un tableau de chunks');
                    }
                    await api.updateTaskChunks(taskId, newChunks);
                    showToast('Chunks mis à jour avec succès', 'success');
                    this.loadTasks();
                } catch (error) {
                    showToast(`Erreur: ${error.message}`, 'error');
                }
            });
        } catch (error) {
            showToast(`Erreur: ${error.message}`, 'error');
        }
    },

    async validateTask(taskId) {
        if (!confirm('Valider les chunks et lancer l\'embedding ?')) return;
        try {
            await api.validateTask(taskId);
            showToast('Embedding lancé avec succès', 'success');
            this.loadTasks();
        } catch (error) {
            showToast(`Erreur: ${error.message}`, 'error');
        }
    },

    async cancelTask(taskId) {
        if (!confirm('Annuler cette tâche ?')) return;
        try {
            await api.cancelTask(taskId);
            showToast('Tâche annulée', 'success');
            this.loadTasks();
        } catch (error) {
            showToast(`Erreur: ${error.message}`, 'error');
        }
    },

    async retryTask(taskId) {
        if (!confirm('Relancer cette tâche ?')) return;
        try {
            await api.retryTask(taskId);
            showToast('Tâche relancée', 'success');
            this.loadTasks();
        } catch (error) {
            showToast(`Erreur: ${error.message}`, 'error');
        }
    },

    showModal(title, content, readOnly = false, onSave = null) {
        // Nettoyer l'ancien modal s'il existe
        const oldModal = document.querySelector('.modal-overlay');
        if (oldModal) oldModal.remove();
        
        const modal = document.createElement('div');
        modal.className = 'modal-overlay active';
        modal.innerHTML = `
            <div class="modal-box">
                <div class="modal-header">
                    <h3>${title}</h3>
                    <button class="modal-close">&times;</button>
                </div>
                <div class="modal-body">
                    ${readOnly ? `<pre style="white-space: pre-wrap; word-break: break-word;">${content}</pre>` : `<textarea>${content}</textarea>`}
                </div>
                <div class="modal-footer">
                    ${!readOnly && onSave ? `<button class="btn btn-success" id="modalSaveBtn">💾 Enregistrer</button>` : ''}
                    <button class="btn btn-secondary" id="modalCloseBtn">Fermer</button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        
        // Gestion des événements
        modal.querySelector('.modal-close').addEventListener('click', () => modal.remove());
        modal.querySelector('#modalCloseBtn').addEventListener('click', () => modal.remove());
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });
        
        if (!readOnly && onSave) {
            modal.querySelector('#modalSaveBtn').addEventListener('click', () => {
                const textarea = modal.querySelector('textarea');
                if (textarea) {
                    onSave(textarea.value);
                    modal.remove();
                }
            });
        }
    },

    formatChunksForDisplay(chunks) {
        // Pour l'affichage, on montre un extrait lisible
        return chunks.map((chunk, i) => 
            `Chunk ${i+1}:\n${chunk.page_content}\n---\n`
        ).join('\n');
    }
};

// Initialize tasks manager when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    tasksManager.init();
    window.tasksManager = tasksManager;
});