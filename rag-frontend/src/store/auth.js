import { defineStore } from 'pinia'
import { apiClient } from '@/api/client'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    apiKey: localStorage.getItem('apiKey') || '',
    apiBase: localStorage.getItem('apiBase') || 'https://api-rag.stage.enset.top',
    userRole: null
  }),

  getters: {
    isAuthenticated: (state) => !!state.apiKey
  },

  actions: {
    async login(apiKey, apiBase) {
      try {
        this.apiKey = apiKey
        this.apiBase = apiBase
        localStorage.setItem('apiKey', apiKey)
        localStorage.setItem('apiBase', apiBase)

        // Vérifier la validité de la clé
        const client = apiClient(apiBase, apiKey)
        await client.get('/admin/cache/stats')

        // Récupérer le rôle (via /admin/api-keys ou autre)
        const keys = await client.get('/admin/api-keys')
        const currentKey = keys.data.find(k => k.key_hash === apiKey)
        this.userRole = currentKey?.role || 'admin'

        return { success: true }
      } catch (error) {
        this.logout()
        return { success: false, error: error.message }
      }
    },

    logout() {
      this.apiKey = ''
      this.userRole = null
      localStorage.removeItem('apiKey')
      localStorage.removeItem('apiBase')
    }
  }
})