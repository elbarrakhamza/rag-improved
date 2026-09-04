<template>
  <v-container fill-height>
    <v-row justify="center" align="center">
      <v-col cols="12" sm="8" md="4">
        <v-card class="pa-6" elevation="12" rounded="lg">
          <div class="text-center mb-6">
            <v-icon size="60" color="primary">mdi-elevator</v-icon>
            <h1 class="text-h4 font-weight-bold">RAG Admin</h1>
            <p class="text-medium-emphasis">Système de maintenance d'ascenseurs</p>
          </div>
          <v-form @submit.prevent="login" ref="form">
            <v-text-field
              v-model="apiKey"
              label="Clé API"
              type="password"
              required
              prepend-inner-icon="mdi-key"
              :rules="[v => !!v || 'Clé API requise']"
            />
            <v-text-field
              v-model="apiBase"
              label="URL de l'API"
              placeholder="https://api-rag.stage.enset.top"
              prepend-inner-icon="mdi-link"
              :rules="[v => !!v || 'URL requise']"
            />
            <v-btn
              type="submit"
              color="primary"
              block
              size="large"
              :loading="loading"
            >
              Se connecter
            </v-btn>
            <v-alert v-if="error" type="error" class="mt-4" dense>
              {{ error }}
            </v-alert>
          </v-form>
          <div class="text-center mt-4 text-caption text-medium-emphasis">
            Version 2.0 • Connexion sécurisée
          </div>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'

const authStore = useAuthStore()
const router = useRouter()
const apiKey = ref('')
const apiBase = ref('https://api-rag.stage.enset.top')
const loading = ref(false)
const error = ref(null)

const login = async () => {
  loading.value = true
  error.value = null
  const result = await authStore.login(apiKey.value, apiBase.value)
  loading.value = false
  if (result.success) {
    router.push('/')
  } else {
    error.value = result.error || 'Clé API invalide'
  }
}
</script>