<template>
  <div>
    <div class="d-flex align-center justify-space-between mb-4 flex-wrap gap-3">
      <h1 class="text-h4 font-weight-medium">Tâches d'ingestion</h1>
      <div class="d-flex gap-2 align-center">
        <v-select
          v-model="filter"
          :items="statusOptions"
          label="Filtrer"
          density="compact"
          variant="outlined"
          style="width:180px"
          prepend-inner-icon="mdi-filter"
        />
        <v-btn color="primary" variant="tonal" @click="loadTasks" :loading="loading">
          <v-icon left>mdi-refresh</v-icon> Actualiser
        </v-btn>
        <!-- Bulk actions -->
        <v-btn
          v-if="selectedTasks.length > 0"
          color="success"
          variant="flat"
          @click="bulkAction('validate')"
          prepend-icon="mdi-check-all"
        >
          Valider ({{ selectedTasks.length }})
        </v-btn>
        <v-btn
          v-if="selectedTasks.length > 0"
          color="error"
          variant="flat"
          @click="bulkAction('cancel')"
          prepend-icon="mdi-cancel"
        >
          Annuler ({{ selectedTasks.length }})
        </v-btn>
        <v-btn
          v-if="selectedTasks.length > 0"
          color="error"
          variant="flat"
          @click="bulkAction('delete')"
          prepend-icon="mdi-delete"
        >
          Supprimer ({{ selectedTasks.length }})
        </v-btn>
      </div>
    </div>

    <v-card>
      <v-list v-if="tasks.length" class="pa-0">
        <v-list-item
          v-for="task in filteredTasks"
          :key="task.id"
          class="task-item"
          border
        >
          <template v-slot:prepend>
            <v-checkbox
              v-model="selectedTasks"
              :value="task.id"
              hide-details
              density="compact"
            />
          </template>
          <v-chip :color="statusColor(task.status)" size="small" class="mr-2 font-weight-medium">
            {{ statusLabel(task.status) }}
          </v-chip>

          <v-list-item-title class="font-weight-medium">
            <span>{{ task.id.substring(0,8) }}</span>
            <span class="text-caption text-medium-emphasis ml-2">
              <v-icon size="small">mdi-cog</v-icon> {{ task.options ? JSON.parse(task.options).mode : 'auto' }}
            </span>
          </v-list-item-title>

          <v-list-item-subtitle class="mt-1">
            <v-icon size="small" class="mr-1">mdi-file</v-icon>
            {{ task.files ? JSON.parse(task.files).map(f => f.split('/').pop()).join(', ') : 'N/A' }}
            <span class="ml-3">
              <v-icon size="small">mdi-clock</v-icon> {{ new Date(task.created_at).toLocaleString() }}
            </span>
            <span v-if="task.error_message" class="text-error ml-3">
              <v-icon size="small" color="error">mdi-alert-circle</v-icon> {{ task.error_message }}
            </span>
          </v-list-item-subtitle>

          <template v-slot:append>
            <div class="d-flex gap-1 flex-wrap">
              <v-btn
                v-if="['CHUNKS_GENERATED','CHUNKS_MODIFIED'].includes(task.status)"
                size="small"
                color="primary"
                variant="text"
                @click="viewChunks(task.id)"
                prepend-icon="mdi-eye"
              >
                Voir
              </v-btn>
              <v-btn
                v-if="['CHUNKS_GENERATED','CHUNKS_MODIFIED'].includes(task.status)"
                size="small"
                color="success"
                variant="flat"
                @click="validate(task.id)"
                prepend-icon="mdi-check"
              >
                Valider
              </v-btn>
              <v-btn
                v-if="task.status === 'FAILED'"
                size="small"
                color="warning"
                variant="flat"
                @click="retry(task.id)"
                prepend-icon="mdi-restart"
              >
                Relancer
              </v-btn>
              <v-btn
                v-if="!['COMPLETED','CANCELLED','FAILED'].includes(task.status)"
                size="small"
                color="error"
                variant="text"
                @click="cancel(task.id)"
                prepend-icon="mdi-cancel"
              >
                Annuler
              </v-btn>
            </div>
          </template>
        </v-list-item>
      </v-list>
      <v-card-text v-else class="text-center text-medium-emphasis py-8">
        <v-icon size="48" color="grey-lighten-1">mdi-inbox</v-icon>
        <div class="mt-2">Aucune tâche trouvée</div>
      </v-card-text>
    </v-card>

    <!-- Modal chunks -->
    <v-dialog v-model="showChunksModal" max-width="960">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon left>mdi-code-json</v-icon> Visualisation des chunks
        </v-card-title>
        <v-divider />
        <v-card-text class="pa-4">
          <div v-if="chunksLoading" class="text-center pa-8">
            <v-progress-circular indeterminate color="primary" />
          </div>
          <div v-else-if="!chunks.length" class="text-center pa-8 text-medium-emphasis">
            Aucun chunk disponible
          </div>
          <div v-else>
            <div
              v-for="(chunk, idx) in chunks"
              :key="idx"
              class="chunk-card pa-3 mb-3"
              style="border:1px solid #e0e0e0; border-radius:8px;"
            >
              <div class="d-flex justify-space-between align-center">
                <span class="font-weight-medium">Chunk #{{ idx+1 }}</span>
                <v-chip size="x-small" color="primary" variant="tonal">
                  Page {{ chunk.metadata?.page_number || 'N/A' }}
                </v-chip>
              </div>
              <v-textarea
                v-model="chunk.page_content"
                variant="outlined"
                density="compact"
                rows="3"
                class="mt-2"
                hide-details
              />
              <div class="text-caption text-medium-emphasis mt-1">
                <v-icon size="small">mdi-file</v-icon> {{ chunk.metadata?.source_file || 'Inconnu' }}
              </div>
            </div>
          </div>
        </v-card-text>
        <v-card-actions class="pa-4">
          <v-btn color="secondary" variant="text" @click="showChunksModal = false">Fermer</v-btn>
          <v-btn
            color="primary"
            variant="flat"
            @click="validateChunks(currentTaskId)"
            :disabled="!chunks.length"
            prepend-icon="mdi-check"
          >
            Valider et lancer l'embedding
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { createApiClient } from '@/api/client'

const api = createApiClient()

const tasks = ref([])
const loading = ref(false)
const filter = ref('all')
const statusOptions = ['all','UPLOADED','GENERATING_CHUNKS','CHUNKS_GENERATED','CHUNKS_MODIFIED','EMBEDDING_IN_PROGRESS','COMPLETED','FAILED','CANCELLED']
const selectedTasks = ref([])

const filteredTasks = computed(() => {
  if (filter.value === 'all') return tasks.value
  return tasks.value.filter(t => t.status === filter.value)
})

const loadTasks = async () => {
  loading.value = true
  try {
    const res = await api.get('/tasks/?limit=50')
    tasks.value = res.data || []
  } catch (e) { console.error(e) }
  finally { loading.value = false }
}

const statusLabel = (s) => ({
  'UPLOADED':'Uploadé','GENERATING_CHUNKS':'Génération','CHUNKS_GENERATED':'Chunks générés',
  'CHUNKS_MODIFIED':'Modifiés','EMBEDDING_IN_PROGRESS':'Embedding','COMPLETED':'Terminé',
  'FAILED':'Échec','CANCELLED':'Annulé'
})[s] || s

const statusColor = (s) => ({
  'UPLOADED':'info','GENERATING_CHUNKS':'warning','CHUNKS_GENERATED':'success','CHUNKS_MODIFIED':'accent',
  'EMBEDDING_IN_PROGRESS':'purple','COMPLETED':'success','FAILED':'error','CANCELLED':'grey'
})[s] || 'grey'

// Bulk actions
const bulkAction = async (action) => {
  if (!selectedTasks.value.length) return
  if (!confirm(`Effectuer l'action "${action}" sur ${selectedTasks.value.length} tâches ?`)) return
  try {
    await api.post('/admin/tasks/bulk', { task_ids: selectedTasks.value, action })
    selectedTasks.value = []
    loadTasks()
  } catch (e) { alert(e.message) }
}

// Modal chunks
const showChunksModal = ref(false)
const chunks = ref([])
const chunksLoading = ref(false)
const currentTaskId = ref(null)

const viewChunks = async (taskId) => {
  currentTaskId.value = taskId
  chunksLoading.value = true
  showChunksModal.value = true
  try {
    const res = await api.get(`/tasks/${taskId}/chunks`)
    let data = res.data
    if (typeof data === 'string') data = JSON.parse(data)
    chunks.value = Array.isArray(data) ? data : []
  } catch (e) { console.error(e); chunks.value = [] }
  finally { chunksLoading.value = false }
}

const validateChunks = async (taskId) => {
  if (!taskId) return
  try {
    await api.post(`/tasks/${taskId}/validate`)
    showChunksModal.value = false
    loadTasks()
  } catch (e) { alert(e.message) }
}

const validate = async (taskId) => {
  if (!confirm('Valider et lancer l\'embedding ?')) return
  try {
    await api.post(`/tasks/${taskId}/validate`)
    loadTasks()
  } catch (e) { alert(e.message) }
}

const cancel = async (taskId) => {
  if (!confirm('Annuler cette tâche ?')) return
  try {
    await api.post(`/tasks/${taskId}/cancel`)
    loadTasks()
  } catch (e) { alert(e.message) }
}

const retry = async (taskId) => {
  try {
    await api.post(`/tasks/${taskId}/retry`)
    loadTasks()
  } catch (e) { alert(e.message) }
}

onMounted(loadTasks)
</script>

<style scoped>
.task-item {
  transition: background 0.1s;
}
.task-item:hover {
  background: #fafafa;
}
.chunk-card {
  background: #fafafa;
}
</style>