<template>
  <div>
    <h1 class="text-h4 font-weight-medium mb-4">Historique des actions</h1>
    <v-card>
      <v-list v-if="entries.length">
        <v-list-item v-for="entry in entries" :key="entry.id" border class="mb-1">
          <v-list-item-title>
            <v-icon :color="entry.type === 'error' ? 'error' : 'primary'" size="small" class="mr-2">
              {{ entry.type === 'error' ? 'mdi-alert-circle' : 'mdi-check-circle' }}
            </v-icon>
            {{ entry.title }}
          </v-list-item-title>
          <v-list-item-subtitle>
            {{ entry.message }}
            <span class="text-caption ml-3">{{ new Date(entry.created_at).toLocaleString() }}</span>
          </v-list-item-subtitle>
        </v-list-item>
      </v-list>
      <v-card-text v-else class="text-center text-medium-emphasis py-8">
        <v-icon size="48" color="grey-lighten-1">mdi-history</v-icon>
        <div class="mt-2">Aucun historique</div>
      </v-card-text>
    </v-card>
    <div class="d-flex justify-center mt-4">
      <v-btn color="primary" variant="tonal" @click="loadHistory" :loading="loading">
        <v-icon left>mdi-refresh</v-icon> Actualiser
      </v-btn>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { createApiClient } from '@/api/client'

const api = createApiClient()
const entries = ref([])
const loading = ref(false)

const loadHistory = async () => {
  loading.value = true
  try {
    const res = await api.get('/admin/history?limit=50')
    entries.value = res.data || []
  } catch (e) { console.error(e) }
  finally { loading.value = false }
}

onMounted(loadHistory)
</script>