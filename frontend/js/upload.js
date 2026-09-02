// upload.js - Gestion complète de l'upload avec mode auto/manual
// Version sans polling intensif : redirige vers l'onglet Tâches après upload

const uploadManager = {
    files: [],
    currentTaskId: null,

    init() {
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        
        // Drag & Drop
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });

        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            this.handleFiles(e.dataTransfer.files);
        });

        fileInput.addEventListener('change', (e) => {
            this.handleFiles(e.target.files);
            fileInput.value = ''; // Reset
        });

        // Form submission
        document.getElementById('metadataForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.uploadFiles();
        });
    },

    handleFiles(fileList) {
        for (const file of fileList) {
            if (file.name.endsWith('.zip') || 
                file.name.endsWith('.pdf') || 
                file.name.endsWith('.txt') || 
                file.name.endsWith('.md') || 
                file.name.endsWith('.markdown')) {
                this.files.push(file);
            } else {
                showToast(`Fichier ${file.name} non supporté`, 'warning');
            }
        }
        this.renderFileList();
        this.detectMetadata();
    },

    detectMetadata() {
        if (this.files.length === 0) {
            document.getElementById('metaBrand').value = '';
            document.getElementById('metaModel').value = '';
            document.getElementById('metaVersion').value = '';
            return;
        }

        const firstFile = this.files[0];
        const fileName = firstFile.name;
        
        // Détection de la marque (brand)
        const brandPatterns = [
            { pattern: /otis/i, brand: 'OTIS' },
            { pattern: /hyundai/i, brand: 'Hyundai' },
            { pattern: /schindler/i, brand: 'Schindler' },
            { pattern: /kone/i, brand: 'KONE' },
            { pattern: /thyssen/i, brand: 'ThyssenKrupp' },
            { pattern: /mitubishi/i, brand: 'Mitsubishi' },
            { pattern: /toshiba/i, brand: 'Toshiba' },
            { pattern: /fujitec/i, brand: 'Fujitec' },
            { pattern: /hitachi/i, brand: 'Hitachi' },
            { pattern: /spelev/i, brand: 'SPELEV' },
            { pattern: /orona/i, brand: 'ORONA' },
            { pattern: /savaria/i, brand: 'Savaria' },
            { pattern: /garier/i, brand: 'Garier' }
        ];
        
        let detectedBrand = '';
        for (const bp of brandPatterns) {
            if (bp.pattern.test(fileName)) {
                detectedBrand = bp.brand;
                break;
            }
        }
        
        if (!detectedBrand && this.files.length > 1) {
            const secondFile = this.files[1];
            if (secondFile) {
                const secondName = secondFile.name;
                for (const bp of brandPatterns) {
                    if (bp.pattern.test(secondName)) {
                        detectedBrand = bp.brand;
                        break;
                    }
                }
            }
        }
        
        // Détection du modèle
        const modelPatterns = [
            { pattern: /gen2/i, model: 'Gen2' },
            { pattern: /gen3/i, model: 'Gen3' },
            { pattern: /nexiez/i, model: 'NEXIEZ' },
            { pattern: /lc[bc]ii/i, model: 'LCBII' },
            { pattern: /2000/i, model: '2000' },
            { pattern: /3000/i, model: '3000' },
            { pattern: /up900/i, model: 'UP900' },
            { pattern: /mrl/i, model: 'MRL' },
            { pattern: /panoramic/i, model: 'Panoramique' },
            { pattern: /hydraulic/i, model: 'Hydraulique' },
            { pattern: /traction/i, model: 'Traction' }
        ];
        
        let detectedModel = '';
        for (const mp of modelPatterns) {
            if (mp.pattern.test(fileName)) {
                detectedModel = mp.model;
                break;
            }
        }
        
        // Détection de la version
        const versionPattern = /v?(\d+[\.\-_]\d+[\.\-_]?\d*)/i;
        const versionMatch = fileName.match(versionPattern);
        const detectedVersion = versionMatch ? versionMatch[1] : '';
        
        // Détection du type de document
        const typePatterns = [
            { pattern: /maintenance/i, type: 'maintenance_manual' },
            { pattern: /install/i, type: 'installation_manual' },
            { pattern: /troubleshoot|diagnostic/i, type: 'troubleshooting_guide' },
            { pattern: /user|guide|manuel utilisateur/i, type: 'user_manual' },
            { pattern: /spec|technical/i, type: 'technical_spec' },
            { pattern: /training|formation/i, type: 'training_document' }
        ];
        
        let detectedType = 'maintenance_manual';
        for (const tp of typePatterns) {
            if (tp.pattern.test(fileName)) {
                detectedType = tp.type;
                break;
            }
        }
        
        // Remplir les champs
        document.getElementById('metaBrand').value = detectedBrand || 'Inconnue (à définir)';
        document.getElementById('metaModel').value = detectedModel || 'Inconnu (à définir)';
        document.getElementById('metaVersion').value = detectedVersion || 'Inconnue (à définir)';
        document.getElementById('metaType').value = detectedType;
        
        if (detectedBrand || detectedModel || detectedVersion) {
            const summary = [];
            if (detectedBrand) summary.push(`Marque: ${detectedBrand}`);
            if (detectedModel) summary.push(`Modèle: ${detectedModel}`);
            if (detectedVersion) summary.push(`Version: ${detectedVersion}`);
            showToast(`📋 Métadonnées détectées: ${summary.join(' | ')}`, 'info', 5000);
        }
    },

    renderFileList() {
        const container = document.getElementById('fileList');
        if (this.files.length === 0) {
            container.innerHTML = '';
            return;
        }
        
        container.innerHTML = this.files.map((file, index) => `
            <div class="file-item">
                <span class="file-name">${file.name}</span>
                <span class="file-size">(${(file.size / 1024).toFixed(1)} KB)</span>
                <span class="file-remove" data-index="${index}">✕</span>
            </div>
        `).join('');

        container.querySelectorAll('.file-remove').forEach(el => {
            el.addEventListener('click', (e) => {
                const index = parseInt(e.target.dataset.index);
                this.files.splice(index, 1);
                this.renderFileList();
                this.detectMetadata();
            });
        });
    },

    async uploadFiles() {
        if (this.files.length === 0) {
            showToast('Veuillez sélectionner des fichiers', 'warning');
            return;
        }

        const formData = new FormData();
        
        // Ajouter les fichiers
        for (const file of this.files) {
            formData.append('files', file);
        }

        // Métadonnées
        let brand = document.getElementById('metaBrand').value;
        let model = document.getElementById('metaModel').value;
        let version = document.getElementById('metaVersion').value;
        
        if (brand === 'Inconnue (à définir)' || !brand) brand = 'unknown';
        if (model === 'Inconnu (à définir)' || !model) model = 'unknown';
        if (version === 'Inconnue (à définir)' || !version) version = 'unknown';
        
        formData.append('brand', brand);
        formData.append('elevator_model', model);
        formData.append('document_type', document.getElementById('metaType').value);
        formData.append('document_version', version);
        formData.append('visibility', document.getElementById('metaVisibility').value);
        formData.append('use_smart_pdf', document.getElementById('optSmartPDF').checked);
        formData.append('use_vision_llm', document.getElementById('optVisionLLM').checked);
        formData.append('skip_embedding', document.getElementById('optSkipEmbedding').checked);
        
        // Mode de traitement (auto/manual)
        const mode = document.getElementById('ingestionMode').value;
        formData.append('mode', mode);

        // Désactiver le bouton et afficher un message de chargement
        const uploadBtn = document.getElementById('uploadBtn');
        uploadBtn.disabled = true;
        uploadBtn.textContent = '⏳ Upload en cours...';

        try {
            const result = await api.upload(formData);
            this.currentTaskId = result.task_id;
            
            showToast(`✅ Upload réussi (mode ${result.mode}) : ${result.files_count} fichiers`, 'success');
            
            // Réinitialiser le formulaire
            this.files = [];
            this.renderFileList();
            document.getElementById('uploadProgress').style.display = 'none';
            
            // Rediriger vers l'onglet Tâches
            this.switchToTasksTab();
            
        } catch (error) {
            showToast(`❌ Upload échoué: ${error.message}`, 'error');
        } finally {
            uploadBtn.disabled = false;
            uploadBtn.textContent = '🚀 Upload & Traitement';
        }
    },

    switchToTasksTab() {
        // Trouver l'élément du menu "Tâches" et simuler un clic
        const tasksNavItem = document.querySelector('.nav-item[data-tab="tasks"]');
        if (tasksNavItem) {
            tasksNavItem.click();
        } else {
            // Fallback : recharger la page pour afficher les tâches
            window.location.reload();
        }
    }
};

// Initialisation au chargement du DOM
document.addEventListener('DOMContentLoaded', () => {
    uploadManager.init();
});