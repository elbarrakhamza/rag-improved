<template>
  <div>
    <div class="d-flex align-center justify-space-between mb-4 flex-wrap gap-3">
      <h1 class="text-h4 font-weight-medium">Gestion du cache</h1>
      <v-btn color="error" variant="flat" @click="clearCache" prepend-icon="mdi-delete">
        Vider le cache
      </v-btn>
    </div>

    <v-row>
      <v-col v-for="stat in stats" :key="stat.label" cols="12" sm="3">
        <StatCard :icon="stat.icon" :label="stat.label" :value="stat.value" />
      </v-col>
    </v-row>

    <v-card class="mt-4">
      <v-card-text class="d-flex align-center justify-space-between">
        <div class="d-flex align-center">
          <v-icon :color="stats[0].value === '🟢 En ligne' ? 'success' : 'error'" size="32">mdi-circle</v-icon>
          <span class="ml-2 font-weight-medium">{{ stats[0].value }}</span>
        </div>
        <v-btn color="primary" variant="tonal" @click="loadStats" prepend-icon="mdi-refresh">
          Actualiser
        </v-btn>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { createApiClient } from '@/api/client'
import StatCard from '@/components/StatCard.vue'

const api = createApiClient()

const stats = ref([
  { icon: 'mdi-server', label: 'Statut', value: 'Vérification...' },
  { icon: 'mdi-database', label: 'Embeddings cachés', value: 0 },
  { icon: 'mdi-message-reply', label: 'Réponses cachées', value: 0 },
  { icon: 'mdi-counter', label: 'Total', value: 0 }
])

const loadStats = async () => {
  try {
    const res = await api.get('/admin/cache/stats')
    const data = res.data
    stats.value[0].value = data.enabled ? '🟢 En ligne' : '🔴 Hors ligne'
    stats.value[1].value = data.cached_embeddings || 0
    stats.value[2].value = data.cached_answers || 0
    stats.value[3].value = data.total_cached || 0
  } catch (e) { console.error(e) }
}

const clearCache = async () => {
  if (!confirm('Vider tout le cache ?')) return
  try {
    await api.delete('/admin/cache/clear')
    loadStats()
    alert('Cache vidé avec succès')
  } catch (e) { alert(e.message) }
}

onMounted(loadStats)
</script>