// tasks.js - Gestion des tâches d'ingestion (Phase 2)

const tasksManager = {
    currentPage: 1,
    totalPages: 0,
    currentTaskId: null,
    tasks: [],

    init() {
        this.loadTasks();
        
        // Rafraîchissement automatique toutes les 10 secondes
        setInterval(() => this.loadTasks(), 10000);
        
        document.getElementById('refreshTasksBtn').addEventListener('click', () => {
            this.loadTasks();
        });
        
        document.getElementById('taskFilter').addEventListener('change', () => {
            this.loadTasks();
        });
        
        // Modal
        document.getElementById('closeChunksModal').addEventListener('click', () => {
            this.closeModal();
        });
        document.getElementById('closeModalBtn').addEventListener('click', () => {
            this.closeModal();
        });
        document.getElementById('validateChunksBtn').addEventListener('click', () => {
            this.validateCurrentTask();
        });
        // Fermer en cliquant à l'extérieur
        document.getElementById('chunksModal').addEventListener('click', (e) => {
            if (e.target === e.currentTarget) this.closeModal();
        });
    },

    async loadTasks() {
        const container = document.getElementById('tasksList');
        const filter = document.getElementById('taskFilter').value;
        
        container.innerHTML = '<p class="loading-text">Chargement des tâches...</p>';
        
        try {
            const data = await api.getTasks(20, (this.currentPage - 1) * 20);
            this.tasks = data || [];
            
            // Filtrer si nécessaire
            let filtered = this.tasks;
            if (filter !== 'all') {
                filtered = this.tasks.filter(t => t.status === filter);
            }
            
            if (filtered.length === 0) {
                container.innerHTML = '<p class="loading-text">Aucune tâche trouvée</p>';
                return;
            }
            
            container.innerHTML = filtered.map(task => {
                const statusClass = this.getStatusClass(task.status);
                const statusLabel = this.getStatusLabel(task.status);
                const files = task.files ? JSON.parse(task.files) : [];
                const fileNames = files.map(f => f.split('/').pop()).join(', ');
                const mode = task.options ? JSON.parse(task.options).mode : 'auto';
                
                return `
                    <div class="task-item">
                        <div class="task-info">
                            <div class="task-id">ID: ${task.id.substring(0, 8)}...</div>
                            <div class="task-files">📄 ${fileNames || 'N/A'}</div>
                            <div class="task-meta">
                                <span class="task-status ${statusClass}">${statusLabel}</span>
                                <span class="task-mode">Mode: ${mode}</span>
                                <span class="task-date">${new Date(task.created_at).toLocaleString()}</span>
                            </div>
                            ${task.error_message ? `<div class="task-error">❌ ${task.error_message}</div>` : ''}
                        </div>
                        <div class="task-actions">
                            ${this.getActionButtons(task)}
                        </div>
                    </div>
                `;
            }).join('');
            
            // Gérer les boutons d'action
            container.querySelectorAll('[data-action]').forEach(el => {
                el.addEventListener('click', (e) => {
                    const action = e.target.dataset.action;
                    const taskId = e.target.dataset.taskId;
                    this.handleAction(action, taskId);
                });
            });
            
        } catch (error) {
            console.error('Error loading tasks:', error);
            container.innerHTML = `<p class="loading-text">Erreur de chargement: ${error.message}</p>`;
        }
    },

    getStatusClass(status) {
        const map = {
            'UPLOADED': 'status-uploaded',
            'GENERATING_CHUNKS': 'status-generating',
            'CHUNKS_GENERATED': 'status-chunks',
            'CHUNKS_MODIFIED': 'status-modified',
            'EMBEDDING_IN_PROGRESS': 'status-embedding',
            'COMPLETED': 'status-completed',
            'FAILED': 'status-failed',
            'CANCELLED': 'status-cancelled'
        };
        return map[status] || 'status-unknown';
    },

    getStatusLabel(status) {
        const map = {
            'UPLOADED': '📤 Uploadé',
            'GENERATING_CHUNKS': '⏳ Génération des chunks',
            'CHUNKS_GENERATED': '📝 Chunks générés',
            'CHUNKS_MODIFIED': '✏️ Chunks modifiés',
            'EMBEDDING_IN_PROGRESS': '🧠 Embedding en cours',
            'COMPLETED': '✅ Terminé',
            'FAILED': '❌ Échec',
            'CANCELLED': '⛔ Annulé'
        };
        return map[status] || status;
    },

    getActionButtons(task) {
        const status = task.status;
        const buttons = [];
        
        if (status === 'CHUNKS_GENERATED' || status === 'CHUNKS_MODIFIED') {
            buttons.push(`
                <button class="btn btn-primary" data-action="view" data-task-id="${task.id}">👁️ Voir chunks</button>
                <button class="btn btn-success" data-action="validate" data-task-id="${task.id}">✅ Valider</button>
            `);
        }
        
        if (status === 'FAILED') {
            buttons.push(`
                <button class="btn btn-warning" data-action="retry" data-task-id="${task.id}">🔄 Relancer</button>
            `);
        }
        
        if (status !== 'COMPLETED' && status !== 'CANCELLED' && status !== 'FAILED') {
            buttons.push(`
                <button class="btn btn-danger" data-action="cancel" data-task-id="${task.id}">⛔ Annuler</button>
            `);
        }
        
        return buttons.join(' ');
    },

    async handleAction(action, taskId) {
        try {
            switch(action) {
                case 'view':
                    await this.viewChunks(taskId);
                    break;
                case 'validate':
                    if (confirm('Valider ces chunks et lancer l\'embedding ?')) {
                        await api.validateTask(taskId);
                        showToast('✅ Embedding lancé !', 'success');
                        this.loadTasks();
                    }
                    break;
                case 'cancel':
                    if (confirm('Annuler cette tâche ?')) {
                        await api.cancelTask(taskId);
                        showToast('⛔ Tâche annulée', 'info');
                        this.loadTasks();
                    }
                    break;
                case 'retry':
                    await api.retryTask(taskId);
                    showToast('🔄 Tâche relancée', 'success');
                    this.loadTasks();
                    break;
                default:
                    console.warn('Action inconnue:', action);
            }
        } catch (error) {
            showToast(`Erreur: ${error.message}`, 'error');
        }
    },

    async viewChunks(taskId) {
        const modal = document.getElementById('chunksModal');
        const container = document.getElementById('chunksContainer');

        try {
            container.innerHTML = '<p>Chargement des chunks...</p>';
            modal.style.display = 'block';

            // Récupérer les chunks
            let chunks = await api.getTaskChunks(taskId);

            // Si c'est une chaîne JSON, la parser
            if (typeof chunks === 'string') {
                try {
                    chunks = JSON.parse(chunks);
                } catch (e) {
                    throw new Error('Format de chunks invalide');
                }
            }

            // Vérifier que c'est bien un tableau
            if (!Array.isArray(chunks)) {
                throw new Error('Les chunks ne sont pas au format attendu');
            }

            if (chunks.length === 0) {
                container.innerHTML = '<p>Aucun chunk disponible pour cette tâche.</p>';
                return;
            }

            // Afficher les chunks
            container.innerHTML = chunks.map((chunk, index) => `
                <div class="chunk-item" style="border:1px solid #ddd; padding:10px; margin:10px 0; border-radius:5px;">
                    <h4>Chunk ${index + 1}</h4>
                    <div style="margin-bottom:5px;">
                        <strong>Page :</strong> ${chunk.metadata?.page_number || 'N/A'}
                        &nbsp;|&nbsp;
                        <strong>Source :</strong> ${chunk.metadata?.source_file || 'Inconnu'}
                    </div>
                    <textarea class="chunk-content" data-index="${index}" style="width:100%; min-height:80px; padding:8px; font-family:monospace;">${chunk.page_content || ''}</textarea>
                </div>
            `).join('');

            // Stocker l'ID de la tâche pour validation ultérieure
            modal.dataset.taskId = taskId;

            // Ajouter un bouton "Sauvegarder les modifications" (optionnel)
            // On peut le faire via un écouteur global sur le modal

        } catch (error) {
            console.error('Erreur chargement chunks:', error);
            container.innerHTML = `<p class="error" style="color:#f44336;">Erreur : ${error.message}</p>`;
        }
    },

    displayChunks(chunks) {
        const container = document.getElementById('chunksContainer');
        if (!chunks || chunks.length === 0) {
            container.innerHTML = '<p>Aucun chunk disponible.</p>';
            return;
        }
        
        container.innerHTML = chunks.map((chunk, index) => `
            <div class="chunk-item">
                <div class="chunk-header">
                    <span class="chunk-index">Chunk #${index + 1}</span>
                    <span class="chunk-meta">
                        Page: ${chunk.metadata?.page_number || 'N/A'}
                        | Source: ${chunk.metadata?.source_file || 'N/A'}
                    </span>
                </div>
                <div class="chunk-content">
                    <textarea class="chunk-textarea" data-index="${index}">${chunk.page_content || ''}</textarea>
                </div>
                <div class="chunk-metadata">
                    <details>
                        <summary>Métadonnées</summary>
                        <pre>${JSON.stringify(chunk.metadata, null, 2)}</pre>
                    </details>
                </div>
            </div>
        `).join('');
        
        // Ajouter la possibilité de modifier les chunks
        document.querySelectorAll('.chunk-textarea').forEach(textarea => {
            textarea.addEventListener('change', (e) => {
                const index = parseInt(e.target.dataset.index);
                chunks[index].page_content = e.target.value;
                // Marquer que les chunks ont été modifiés
                document.getElementById('validateChunksBtn').dataset.modified = 'true';
            });
        });
        
        // Bouton de sauvegarde des modifications
        const saveBtn = document.createElement('button');
        saveBtn.className = 'btn btn-primary';
        saveBtn.textContent = '💾 Sauvegarder les modifications';
        saveBtn.style.marginTop = '16px';
        saveBtn.addEventListener('click', async () => {
            try {
                await api.updateTaskChunks(this.currentTaskId, chunks);
                showToast('✅ Chunks sauvegardés !', 'success');
                document.getElementById('validateChunksBtn').dataset.modified = 'false';
                this.loadTasks();
            } catch (error) {
                showToast(`Erreur: ${error.message}`, 'error');
            }
        });
        container.appendChild(saveBtn);
    },

    closeModal() {
        document.getElementById('chunksModal').style.display = 'none';
        this.currentTaskId = null;
    },

    async validateCurrentTask() {
        if (!this.currentTaskId) return;
        if (confirm('Valider ces chunks et lancer l\'embedding ?')) {
            try {
                await api.validateTask(this.currentTaskId);
                showToast('✅ Embedding lancé !', 'success');
                this.closeModal();
                this.loadTasks();
            } catch (error) {
                showToast(`Erreur: ${error.message}`, 'error');
            }
        }
    }
};

// Initialisation
document.addEventListener('DOMContentLoaded', () => {
    tasksManager.init();
    window.tasksManager = tasksManager;
});