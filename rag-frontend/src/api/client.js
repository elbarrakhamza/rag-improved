import axios from 'axios'
import { useAuthStore } from '@/store/auth'

export function apiClient(baseURL, apiKey) {
  const client = axios.create({
    baseURL,
    headers: {
      'X-API-Key': apiKey,
      'Content-Type': 'application/json'
    }
  })

  client.interceptors.response.use(
    response => response,
    error => {
      if (error.response?.status === 401 || error.response?.status === 403) {
        const authStore = useAuthStore()
        authStore.logout()
        window.location.href = '/login'
      }
      return Promise.reject(error)
    }
  )

  return client
}

export const createApiClient = () => {
  const authStore = useAuthStore()
  return apiClient(authStore.apiBase, authStore.apiKey)
}