<template>
  <div>
    <div class="d-flex align-center justify-space-between mb-4 flex-wrap gap-3">
      <h1 class="text-h4 font-weight-medium">Documents indexés</h1>
      <div class="d-flex gap-2 align-center flex-wrap">
        <v-text-field
          v-model="search"
          label="Rechercher"
          density="compact"
          variant="outlined"
          hide-details
          style="width:180px"
          prepend-inner-icon="mdi-magnify"
        />
        <v-text-field
          v-model="brandFilter"
          label="Marque"
          density="compact"
          variant="outlined"
          hide-details
          style="width:120px"
        />
        <v-text-field
          v-model="modelFilter"
          label="Modèle"
          density="compact"
          variant="outlined"
          hide-details
          style="width:120px"
        />
        <v-select
          v-model="visibilityFilter"
          :items="['','public','private']"
          label="Visibilité"
          density="compact"
          variant="outlined"
          hide-details
          style="width:130px"
        />
        <v-menu v-model="dateMenu" :close-on-content-click="false">
          <template v-slot:activator="{ props }">
            <v-text-field
              v-bind="props"
              :model-value="dateRange ? `${dateRange[0].toLocaleDateString()} - ${dateRange[1].toLocaleDateString()}` : ''"
              label="Période"
              density="compact"
              variant="outlined"
              readonly
              hide-details
              style="width:180px"
              prepend-inner-icon="mdi-calendar"
            />
          </template>
          <v-date-picker v-model="dateRange" range />
        </v-menu>
        <v-btn color="primary" variant="tonal" @click="loadDocuments" :loading="loading">
          <v-icon left>mdi-refresh</v-icon> Actualiser
        </v-btn>
        <v-btn color="accent" variant="outlined" @click="exportData('json')">
          <v-icon left>mdi-export</v-icon> Export JSON
        </v-btn>
        <v-btn color="accent" variant="outlined" @click="exportData('csv')">
          <v-icon left>mdi-export</v-icon> Export CSV
        </v-btn>
        <v-btn color="primary" variant="outlined" @click="$refs.importInput.click()">
          <v-icon left>mdi-import</v-icon> Import
        </v-btn>
        <input ref="importInput" type="file" accept=".json" style="display:none" @change="importMetadata($event)" />
      </div>
    </div>

    <v-card>
      <v-list v-if="documents.length" class="pa-0">
        <v-list-item v-for="doc in documents" :key="doc.source_file" class="doc-item" border>
          <v-list-item-title class="font-weight-medium">
            <v-icon left color="primary">mdi-file-pdf</v-icon>
            {{ doc.source_file }}
          </v-list-item-title>
          <v-list-item-subtitle class="mt-1">
            <v-chip size="x-small" variant="tonal" class="mr-1">🏷️ {{ doc.brand }}</v-chip>
            <v-chip size="x-small" variant="tonal" class="mr-1">📦 {{ doc.model }}</v-chip>
            <v-chip size="x-small" variant="tonal" class="mr-1">📄 {{ doc.type }}</v-chip>
            <v-chip size="x-small" variant="tonal" class="mr-1">📌 {{ doc.version }}</v-chip>
            <v-chip :color="doc.visibility === 'private' ? 'error' : 'success'" size="x-small" class="ml-1">
              {{ doc.visibility }}
            </v-chip>
          </v-list-item-subtitle>
          <template v-slot:append>
            <v-btn
              size="small"
              color="accent"
              variant="text"
              @click="toggleVisibility(doc)"
              prepend-icon="mdi-eye"
            >
              {{ doc.visibility === 'private' ? 'Rendre public' : 'Rendre privé' }}
            </v-btn>
            <v-btn
              size="small"
              color="error"
              variant="text"
              @click="deleteDoc(doc.source_file)"
              prepend-icon="mdi-delete"
            />
          </template>
        </v-list-item>
      </v-list>
      <v-card-text v-else class="text-center text-medium-emphasis py-8">
        <v-icon size="48" color="grey-lighten-1">mdi-file-document-outline</v-icon>
        <div class="mt-2">Aucun document trouvé</div>
      </v-card-text>
    </v-card>

    <div class="d-flex justify-center mt-4" v-if="totalPages > 1">
      <v-pagination v-model="page" :length="totalPages" @update:modelValue="loadDocuments" />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { createApiClient } from '@/api/client'

const api = createApiClient()

const documents = ref([])
const loading = ref(false)
const search = ref('')
const brandFilter = ref('')
const modelFilter = ref('')
const visibilityFilter = ref('')
const dateRange = ref(null)
const dateMenu = ref(false)
const page = ref(1)
const total = ref(0)
const totalPages = ref(1)

const loadDocuments = async () => {
  loading.value = true
  try {
    const params = {
      page: page.value,
      limit: 50,
      search: search.value,
      brand: brandFilter.value,
      model: modelFilter.value,
      visibility: visibilityFilter.value
    }
    if (dateRange.value && dateRange.value.length === 2) {
      params.start_date = dateRange.value[0].toISOString()
      params.end_date = dateRange.value[1].toISOString()
    }
    const res = await api.get('/admin/documents', { params })
    documents.value = res.data.documents || []
    total.value = res.data.total || 0
    totalPages.value = Math.ceil(total.value / 50)
  } catch (e) { console.error(e) }
  finally { loading.value = false }
}

const exportData = async (format) => {
  try {
    const res = await api.get(`/admin/export?format=${format}&type=documents`, { responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `documents_export.${format === 'csv' ? 'csv' : 'json'}`)
    document.body.appendChild(link)
    link.click()
    link.remove()
  } catch (e) { alert(e.message) }
}

const importMetadata = async (e) => {
  const file = e.target.files[0]
  if (!file) return
  const formData = new FormData()
  formData.append('file', file)
  try {
    const res = await api.post('/admin/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    alert(`Importé : ${res.data.updated} documents mis à jour`)
    loadDocuments()
  } catch (e) { alert(e.message) }
  e.target.value = ''
}

const toggleVisibility = async (doc) => {
  const newVis = doc.visibility === 'public' ? 'private' : 'public'
  if (!confirm(`Passer "${doc.source_file}" en ${newVis} ?`)) return
  try {
    const formData = new URLSearchParams()
    formData.append('visibility', newVis)
    await api.patch(`/admin/documents/${encodeURIComponent(doc.source_file)}/visibility`, formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    })
    loadDocuments()
  } catch (e) { alert(e.message) }
}

const deleteDoc = async (sourceFile) => {
  if (!confirm(`Supprimer "${sourceFile}" ?`)) return
  try {
    await api.delete(`/admin/documents/${encodeURIComponent(sourceFile)}`)
    loadDocuments()
  } catch (e) { alert(e.message) }
}

watch([search, brandFilter, modelFilter, visibilityFilter, dateRange], () => { page.value = 1; loadDocuments() }, { deep: true })
onMounted(loadDocuments)
</script>