<template>
  <div>
    <h1 class="text-h4 font-weight-medium mb-4">Feedback utilisateurs</h1>

    <v-row>
      <v-col v-for="stat in stats" :key="stat.label" cols="12" sm="4">
        <StatCard :icon="stat.icon" :label="stat.label" :value="stat.value" />
      </v-col>
    </v-row>

    <v-row>
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>
            <v-icon left>mdi-star</v-icon> Top Questions
          </v-card-title>
          <v-divider />
          <v-list>
            <v-list-item v-for="q in topQuestions" :key="q.question_hash">
              <v-list-item-title>{{ q.question_text || 'N/A' }}</v-list-item-title>
              <template v-slot:append>
                <v-chip size="x-small" color="primary" variant="tonal">
                  {{ q.frequency }}x
                </v-chip>
                <v-chip
                  :color="q.avg_feedback_score >= 4 ? 'success' : q.avg_feedback_score >= 2 ? 'warning' : 'error'"
                  size="x-small"
                  class="ml-1"
                >
                  {{ q.avg_feedback_score?.toFixed(1) || 0 }}
                </v-chip>
              </template>
            </v-list-item>
            <v-list-item v-if="!topQuestions.length">
              <v-list-item-title class="text-center text-medium-emphasis">Aucune question</v-list-item-title>
            </v-list-item>
          </v-list>
        </v-card>
      </v-col>

      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>
            <v-icon left>mdi-alert</v-icon> Questions à améliorer
          </v-card-title>
          <v-divider />
          <v-list>
            <v-list-item v-for="q in lowPerforming" :key="q.question_hash">
              <v-list-item-title>{{ q.question_text || 'N/A' }}</v-list-item-title>
              <template v-slot:append>
                <v-chip color="error" size="x-small">
                  {{ q.avg_feedback_score?.toFixed(1) || 0 }}
                </v-chip>
              </template>
            </v-list-item>
            <v-list-item v-if="!lowPerforming.length">
              <v-list-item-title class="text-center text-medium-emphasis">Aucune question à améliorer</v-list-item-title>
            </v-list-item>
          </v-list>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { createApiClient } from '@/api/client'
import StatCard from '@/components/StatCard.vue'

const api = createApiClient()

const stats = ref([
  { icon: 'mdi-message-text', label: 'Total feedback', value: 0 },
  { icon: 'mdi-star', label: 'Score moyen', value: 0 },
  { icon: 'mdi-thumb-up', label: 'Utiles %', value: '75%' }
])
const topQuestions = ref([])
const lowPerforming = ref([])

const loadData = async () => {
  try {
    const [topRes, lowRes] = await Promise.all([
      api.get('/feedback/top-questions?limit=5'),
      api.get('/feedback/low-performing-questions?min_frequency=2&max_avg_score=3')
    ])
    topQuestions.value = topRes.data || []
    const low = lowRes.data?.questions || []
    lowPerforming.value = low

    const total = topRes.data.length + low.length
    stats.value[0].value = total
    const avg = total ? topRes.data.reduce((s, q) => s + (q.avg_feedback_score || 0), 0) / total : 0
    stats.value[1].value = avg.toFixed(1)
  } catch (e) { console.error(e) }
}

onMounted(loadData)
</script>