<template>
  <div>
    <h1 class="text-h4 font-weight-medium mb-4">Dashboard</h1>

    <v-row>
      <v-col v-for="stat in stats" :key="stat.label" cols="12" sm="6" md="3">
        <StatCard :icon="stat.icon" :label="stat.label" :value="stat.value" />
      </v-col>
    </v-row>

    <v-row>
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>Activité des tâches (30 derniers jours)</v-card-title>
          <v-card-text>
            <canvas ref="taskChartCanvas"></canvas>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>Répartition par type de document</v-card-title>
          <v-card-text>
            <canvas ref="docChartCanvas"></canvas>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { createApiClient } from '@/api/client'
import StatCard from '@/components/StatCard.vue'
import { Chart, registerables } from 'chart.js'
Chart.register(...registerables)

const api = createApiClient()
const taskChartCanvas = ref(null)
const docChartCanvas = ref(null)

const stats = ref([
  { icon: 'mdi-file-document', label: 'Documents', value: 0 },
  { icon: 'mdi-puzzle', label: 'Chunks', value: 0 },
  { icon: 'mdi-message-reply', label: 'Feedback', value: 0 },
  { icon: 'mdi-cached', label: 'Cache', value: 0 }
])

let taskChart = null
let docChart = null

onMounted(async () => {
  try {
    const [docs, cache, feedback, tasks] = await Promise.all([
      api.get('/admin/documents?page=1&limit=1'),
      api.get('/admin/cache/stats'),
      api.get('/feedback/top-questions?limit=1'),
      api.get('/tasks/?limit=100')
    ])
    stats.value[0].value = docs.data.total || 0
    stats.value[3].value = cache.data.total_cached || 0
    stats.value[2].value = feedback.data.length || 0

    const taskList = tasks.data || []
    const statusCounts = taskList.reduce((acc, t) => {
      acc[t.status] = (acc[t.status] || 0) + 1
      return acc
    }, {})

    await nextTick()

    if (taskChartCanvas.value) {
      const ctx = taskChartCanvas.value.getContext('2d')
      taskChart = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: Object.keys(statusCounts),
          datasets: [{
            label: 'Nombre de tâches',
            data: Object.values(statusCounts),
            backgroundColor: '#FF9800',
            borderRadius: 4
          }]
        },
        options: {
          responsive: true,
          plugins: { legend: { display: false } }
        }
      })
    }

    const docTypes = await api.get('/admin/documents?limit=100')
    const types = docTypes.data.documents || []
    const typeCounts = types.reduce((acc, d) => {
      acc[d.type] = (acc[d.type] || 0) + 1
      return acc
    }, {})

    if (docChartCanvas.value) {
      const ctx = docChartCanvas.value.getContext('2d')
      docChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
          labels: Object.keys(typeCounts),
          datasets: [{
            data: Object.values(typeCounts),
            backgroundColor: ['#FF9800', '#1a73e8', '#4CAF50', '#f44336', '#9C27B0']
          }]
        },
        options: { responsive: true }
      })
    }
  } catch (e) { console.error(e) }
})
</script>