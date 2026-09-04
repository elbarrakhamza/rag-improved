<template>
  <div>
    <div class="d-flex align-center justify-space-between mb-4 flex-wrap gap-3">
      <h1 class="text-h4 font-weight-medium">Clés API</h1>
      <v-btn color="primary" variant="flat" @click="showGenerate = !showGenerate" prepend-icon="mdi-plus">
        Générer une clé
      </v-btn>
    </div>

    <v-card v-if="showGenerate" class="pa-4 mb-4" elevation="2">
      <v-form @submit.prevent="generateKey">
        <v-row align="center">
          <v-col cols="12" sm="4">
            <v-select v-model="newRole" :items="['admin','employee','public']" label="Rôle" variant="outlined" density="compact" prepend-inner-icon="mdi-account" />
          </v-col>
          <v-col cols="12" sm="6">
            <v-text-field v-model="newDesc" label="Description" variant="outlined" density="compact" prepend-inner-icon="mdi-text" />
          </v-col>
          <v-col cols="12" sm="2" class="d-flex align-center">
            <v-btn type="submit" color="success" block>Générer</v-btn>
          </v-col>
        </v-row>
      </v-form>
    </v-card>

    <v-card>
      <v-list v-if="keys.length" class="pa-0">
        <v-list-item v-for="k in keys" :key="k.id" class="key-item" border>
          <template v-slot:prepend>
            <v-avatar color="primary" size="36" variant="tonal">
              <v-icon size="20">mdi-key</v-icon>
            </v-avatar>
          </template>
          <v-list-item-title>
            <v-chip :color="k.role === 'admin' ? 'error' : k.role === 'employee' ? 'warning' : 'success'" size="small" class="mr-2">
              {{ k.role }}
            </v-chip>
            <span class="font-weight-medium">{{ k.description || 'Sans description' }}</span>
          </v-list-item-title>
          <v-list-item-subtitle>
            <span class="text-caption">Hash: {{ k.key_hash?.substring(0,20) }}...</span>
            <v-chip :color="k.is_active ? 'success' : 'grey'" size="x-small" class="ml-2">
              {{ k.is_active ? 'Active' : 'Inactive' }}
            </v-chip>
            <span class="text-caption ml-2">Créée: {{ new Date(k.created_at).toLocaleDateString() }}</span>
          </v-list-item-subtitle>
          <template v-slot:append>
            <v-btn
              size="small"
              :color="k.is_active ? 'error' : 'success'"
              variant="text"
              @click="toggleKey(k.id)"
              prepend-icon="mdi-power"
            >
              {{ k.is_active ? 'Désactiver' : 'Activer' }}
            </v-btn>
            <v-btn
              size="small"
              color="error"
              variant="text"
              @click="deleteKey(k.id)"
              prepend-icon="mdi-delete"
            />
          </template>
        </v-list-item>
      </v-list>
      <v-card-text v-else class="text-center text-medium-emphasis py-8">
        <v-icon size="48" color="grey-lighten-1">mdi-key-off</v-icon>
        <div class="mt-2">Aucune clé API</div>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { createApiClient } from '@/api/client'

const api = createApiClient()

const keys = ref([])
const showGenerate = ref(false)
const newRole = ref('public')
const newDesc = ref('')

const loadKeys = async () => {
  try {
    const res = await api.get('/admin/api-keys')
    keys.value = res.data || []
  } catch (e) { console.error(e) }
}

const generateKey = async () => {
  try {
    const formData = new URLSearchParams()
    formData.append('role', newRole.value)
    formData.append('description', newDesc.value)
    const res = await api.post('/admin/api-keys/generate', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    })
    alert('Clé générée : ' + res.data.api_key)
    showGenerate.value = false
    loadKeys()
  } catch (e) { alert(e.message) }
}

const toggleKey = async (id) => {
  try {
    await api.post(`/admin/api-keys/${id}/toggle`)
    loadKeys()
  } catch (e) { alert(e.message) }
}

const deleteKey = async (id) => {
  if (!confirm('Supprimer cette clé ?')) return
  try {
    await api.delete(`/admin/api-keys/${id}`)
    loadKeys()
  } catch (e) { alert(e.message) }
}

onMounted(loadKeys)
</script>

<style scoped>
.key-item {
  transition: background 0.1s;
}
.key-item:hover {
  background: #fafafa;
}
</style>