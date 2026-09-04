<template>
  <div>
    <h1 class="text-h4 font-weight-medium mb-4">Upload de documents</h1>

    <!-- 1. Zone de dépôt -->
    <v-card
      class="upload-zone"
      :class="{ 'dragover': isDragging }"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @drop.prevent="handleDrop"
      elevation="1"
      rounded="lg"
    >
      <v-icon size="48" color="primary" class="mb-2">mdi-cloud-upload</v-icon>
      <h3 class="text-h6">Glissez‑déposez vos fichiers ici</h3>
      <p class="text-caption text-medium-emphasis">ou</p>
      <v-btn color="primary" variant="flat" @click="$refs.fileInput.click()">
        Parcourir
      </v-btn>
      <input
        ref="fileInput"
        type="file"
        multiple
        accept=".pdf,.txt,.md,.markdown,.zip"
        style="display:none"
        @change="handleFiles($event.target.files)"
      />
    </v-card>

    <!-- 2. Liste des fichiers -->
    <v-list v-if="files.length" class="mt-3" density="compact" lines="one">
      <v-list-subheader>Fichiers sélectionnés ({{ files.length }})</v-list-subheader>
      <v-list-item v-for="(file, i) in files" :key="i">
        <template v-slot:prepend>
          <v-icon color="primary" size="small">mdi-file</v-icon>
        </template>
        <v-list-item-title>{{ file.name }}</v-list-item-title>
        <template v-slot:append>
          <v-btn icon size="x-small" color="error" variant="text" @click="files.splice(i,1)">
            <v-icon size="small">mdi-close</v-icon>
          </v-btn>
        </template>
      </v-list-item>
    </v-list>

    <!-- 3. Métadonnées – organisées en sections -->
    <v-card class="pa-4 mt-4" elevation="2" rounded="lg">
      <v-form @submit.prevent="upload">
        <h3 class="text-h6 font-weight-medium mb-3">📋 Métadonnées du document</h3>

        <!-- Section 1 : Informations générales -->
        <v-expansion-panels variant="accordion" class="mb-3">
          <v-expansion-panel>
            <v-expansion-panel-title expand-icon="mdi-chevron-down">
              <v-icon left size="small" color="primary" class="mr-2">mdi-information</v-icon>
              Informations générales
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <v-row dense>
                <v-col cols="12" sm="6">
                  <v-text-field
                    v-model="brand"
                    label="Marque"
                    variant="outlined"
                    density="compact"
                    prepend-inner-icon="mdi-tag"
                    hint="Détectée automatiquement depuis le nom du fichier"
                    persistent-hint
                  />
                </v-col>
                <v-col cols="12" sm="6">
                  <v-text-field
                    v-model="model"
                    label="Modèle"
                    variant="outlined"
                    density="compact"
                    prepend-inner-icon="mdi-archive"
                    hint="Détecté automatiquement depuis le nom du fichier"
                    persistent-hint
                  />
                </v-col>
                <v-col cols="12" sm="6">
                  <v-select
                    v-model="docType"
                    :items="docTypes"
                    label="Type de document"
                    variant="outlined"
                    density="compact"
                    prepend-inner-icon="mdi-file-document-outline"
                    hint="Choisissez le type de document"
                    persistent-hint
                  />
                </v-col>
                <v-col cols="12" sm="6">
                  <v-text-field
                    v-model="version"
                    label="Version"
                    variant="outlined"
                    density="compact"
                    prepend-inner-icon="mdi-source-branch"
                    hint="Détectée automatiquement depuis le nom du fichier"
                    persistent-hint
                  />
                </v-col>
              </v-row>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>

        <!-- Section 2 : Visibilité et mode (paramètres importants) -->
        <v-expansion-panels variant="accordion" class="mb-3">
          <v-expansion-panel>
            <v-expansion-panel-title expand-icon="mdi-chevron-down">
              <v-icon left size="small" color="warning" class="mr-2">mdi-star</v-icon>
              Visibilité et mode de traitement
              <v-chip size="x-small" color="warning" class="ml-2">Important</v-chip>
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <v-row dense>
                <v-col cols="12" sm="6">
                  <v-select
                    v-model="visibility"
                    :items="['private','public']"
                    label="Visibilité"
                    variant="outlined"
                    density="compact"
                    prepend-inner-icon="mdi-eye"
                    hint="Public = accessible à tous, Privé = réservé aux employés"
                    persistent-hint
                  />
                </v-col>
                <v-col cols="12" sm="6">
                  <v-select
                    v-model="mode"
                    :items="['manual','auto']"
                    label="Mode de traitement"
                    variant="outlined"
                    density="compact"
                    prepend-inner-icon="mdi-cog"
                    hint="Auto = tout enchaîné, Manuel = validation des chunks avant embedding"
                    persistent-hint
                  />
                </v-col>
              </v-row>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>

        <!-- Section 3 : Options avancées -->
        <v-expansion-panels variant="accordion" class="mb-3">
          <v-expansion-panel>
            <v-expansion-panel-title expand-icon="mdi-chevron-down">
              <v-icon left size="small" color="accent" class="mr-2">mdi-settings</v-icon>
              Options avancées
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <v-row dense>
                <v-col cols="12" sm="4">
                  <v-checkbox
                    v-model="smartPdf"
                    label="Smart PDF"
                    hide-details
                    density="compact"
                    hint="Active la détection automatique des tableaux, images, et OCR"
                    persistent-hint
                  />
                </v-col>
                <v-col cols="12" sm="4">
                  <v-checkbox
                    v-model="visionLlm"
                    label="Vision LLM"
                    hide-details
                    density="compact"
                    hint="Utilise un modèle de vision pour décrire les images"
                    persistent-hint
                  />
                </v-col>
                <v-col cols="12" sm="4">
                  <v-checkbox
                    v-model="skipEmbedding"
                    label="🧪 Mode test"
                    hide-details
                    density="compact"
                    hint="Ne génère pas les embeddings (utile pour tester l'extraction)"
                    persistent-hint
                  />
                </v-col>
              </v-row>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>

        <v-btn
          type="submit"
          color="primary"
          block
          class="mt-3"
          :loading="loading"
          :disabled="!files.length"
          size="large"
        >
          <v-icon left>mdi-upload</v-icon> Upload & Traitement
        </v-btn>
      </v-form>
    </v-card>

    <!-- 4. Progression (affichée si une tâche est en cours) -->
    <v-row v-if="taskId" class="mt-4">
      <v-col>
        <v-card>
          <v-card-text>
            <v-progress-linear :model-value="progress" color="primary" height="8" striped />
            <div class="d-flex justify-space-between mt-2">
              <span>{{ statusMessage }}</span>
              <span class="font-weight-medium">{{ progress }}%</span>
            </div>
            <v-chip v-if="taskStatus" :color="taskStatus === 'COMPLETED' ? 'success' : 'primary'" size="small" class="mt-2">
              {{ taskStatus }}
            </v-chip>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Dialog de confirmation après upload -->
    <v-dialog v-model="showConfirmDialog" max-width="600">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon color="success" size="32" class="mr-2">mdi-check-circle</v-icon>
          Upload réussi !
        </v-card-title>
        <v-divider />
        <v-card-text class="pt-4">
          <p>Votre document a été uploadé avec les paramètres suivants :</p>
          <v-list density="compact" class="bg-grey-lighten-4 rounded">
            <v-list-item>
              <v-list-item-title><strong>Marque :</strong> {{ brand || 'Non spécifiée' }}</v-list-item-title>
            </v-list-item>
            <v-list-item>
              <v-list-item-title><strong>Modèle :</strong> {{ model || 'Non spécifié' }}</v-list-item-title>
            </v-list-item>
            <v-list-item>
              <v-list-item-title><strong>Type :</strong> {{ docType }}</v-list-item-title>
            </v-list-item>
            <v-list-item>
              <v-list-item-title><strong>Version :</strong> {{ version || 'Non spécifiée' }}</v-list-item-title>
            </v-list-item>
            <v-list-item>
              <v-list-item-title>
                <strong>Visibilité :</strong>
                <v-chip :color="visibility === 'public' ? 'success' : 'error'" size="x-small" class="ml-1">
                  {{ visibility }}
                </v-chip>
              </v-list-item-title>
            </v-list-item>
            <v-list-item>
              <v-list-item-title><strong>Mode :</strong> {{ mode }}</v-list-item-title>
            </v-list-item>
            <v-list-item>
              <v-list-item-title><strong>Options :</strong>
                <span v-if="smartPdf">Smart PDF, </span>
                <span v-if="visionLlm">Vision LLM, </span>
                <span v-if="skipEmbedding">Mode test, </span>
                <span v-if="!smartPdf && !visionLlm && !skipEmbedding">Aucune</span>
              </v-list-item-title>
            </v-list-item>
            <v-list-item>
              <v-list-item-title><strong>ID de la tâche :</strong> {{ taskId?.substring(0,8) }}...</v-list-item-title>
            </v-list-item>
          </v-list>
          <p class="mt-3 text-caption text-medium-emphasis">Le traitement est en cours en arrière-plan. Vous pouvez suivre l'avancement dans la page des tâches.</p>
        </v-card-text>
        <v-card-actions class="pa-4">
          <v-btn color="secondary" variant="text" @click="showConfirmDialog = false">Fermer</v-btn>
          <v-btn color="primary" variant="flat" @click="goToTasks" prepend-icon="mdi-format-list-bulleted">
            Voir les tâches
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { createApiClient } from '@/api/client'

const api = createApiClient()
const router = useRouter()

const files = ref([])
const isDragging = ref(false)
const loading = ref(false)

// Métadonnées
const brand = ref('')
const model = ref('')
const docType = ref('maintenance_manual')
const version = ref('')
const visibility = ref('private')
const mode = ref('manual')
const smartPdf = ref(true)
const visionLlm = ref(false)
const skipEmbedding = ref(false)

const docTypes = [
  'maintenance_manual', 'installation_manual', 'troubleshooting_guide',
  'user_manual', 'technical_spec', 'training_document', 'other'
]

// Suivi tâche et progression
const taskId = ref(null)
const taskStatus = ref(null)
const progress = ref(0)
const statusMessage = ref('')
let pollInterval = null

// Dialog de confirmation
const showConfirmDialog = ref(false)

// Détection automatique des métadonnées depuis le nom du fichier
const detectMetadata = (fileName) => {
  const brandPatterns = [
    { pattern: /otis/i, brand: 'OTIS' },
    { pattern: /hyundai/i, brand: 'Hyundai' },
    { pattern: /schindler/i, brand: 'Schindler' },
    { pattern: /kone/i, brand: 'KONE' },
    { pattern: /spelev/i, brand: 'SPELEV' },
    { pattern: /orona/i, brand: 'ORONA' }
  ]
  for (const bp of brandPatterns) {
    if (bp.pattern.test(fileName)) {
      brand.value = bp.brand
      break
    }
  }
  const modelPatterns = [
    { pattern: /gen2/i, model: 'Gen2' },
    { pattern: /gen3/i, model: 'Gen3' },
    { pattern: /nexiez/i, model: 'NEXIEZ' },
    { pattern: /lc[bc]ii/i, model: 'LCBII' },
    { pattern: /2000/i, model: '2000' },
    { pattern: /up900/i, model: 'UP900' }
  ]
  for (const mp of modelPatterns) {
    if (mp.pattern.test(fileName)) {
      model.value = mp.model
      break
    }
  }
  const versionMatch = fileName.match(/v?(\d+[\.\-_]\d+[\.\-_]?\d*)/i)
  version.value = versionMatch ? versionMatch[1] : ''
}

// Gestion des fichiers
const handleDrop = (e) => {
  isDragging.value = false
  handleFiles(e.dataTransfer.files)
}

const handleFiles = (fileList) => {
  for (const file of fileList) {
    if (file.name.match(/\.(pdf|txt|md|markdown|zip)$/i)) {
      files.value.push(file)
      if (files.value.length === 1) detectMetadata(file.name)
    }
  }
}

// Upload
const upload = async () => {
  if (!files.value.length) return
  loading.value = true
  const formData = new FormData()
  files.value.forEach(f => formData.append('files', f))
  formData.append('brand', brand.value || 'unknown')
  formData.append('elevator_model', model.value || 'unknown')
  formData.append('document_type', docType.value)
  formData.append('document_version', version.value || 'unknown')
  formData.append('visibility', visibility.value)
  formData.append('use_smart_pdf', String(smartPdf.value))
  formData.append('use_vision_llm', String(visionLlm.value))
  formData.append('skip_embedding', String(skipEmbedding.value))
  formData.append('mode', mode.value)

  try {
    const res = await api.post('/admin/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    taskId.value = res.data.task_id
    taskStatus.value = 'UPLOADED'
    progress.value = 0
    statusMessage.value = 'Upload réussi, traitement en cours...'

    // Ouvrir le dialog de confirmation avec les paramètres
    showConfirmDialog.value = true

    // Démarrer le polling pour suivre la progression
    pollTask()
  } catch (err) {
    console.error(err)
    alert('Erreur upload : ' + err.message)
  } finally {
    loading.value = false
  }
}

// Polling de la tâche
const pollTask = () => {
  if (pollInterval) clearInterval(pollInterval)
  pollInterval = setInterval(async () => {
    try {
      const res = await api.get(`/admin/task/${taskId.value}`)
      const status = res.data
      taskStatus.value = status.status
      progress.value = Math.min(100, (status.progress || 0) / (status.total || 1) * 100)
      statusMessage.value = status.message || status.status
      if (['COMPLETED', 'FAILED', 'CANCELLED'].includes(status.status)) {
        clearInterval(pollInterval)
        pollInterval = null
        // Si terminé, on met à jour le statut
        if (status.status === 'COMPLETED') {
          // On pourrait afficher un message dans le dialog, mais on laisse l'utilisateur naviguer
        }
      }
    } catch (e) {
      console.error(e)
    }
  }, 3000)
}

// Redirection vers la page des tâches
const goToTasks = () => {
  showConfirmDialog.value = false
  router.push('/tasks')
}

// Nettoyage
onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
})
</script>

<style scoped>
.upload-zone {
  border: 2px dashed #ddd;
  border-radius: 12px;
  padding: 32px 24px;
  text-align: center;
  transition: border-color 0.3s, background 0.3s;
  background: #fafafa;
  min-height: 160px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.upload-zone.dragover {
  border-color: #FF9800;
  background: #fff3e0;
}
</style>