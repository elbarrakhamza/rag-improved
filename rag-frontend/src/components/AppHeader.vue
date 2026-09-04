<template>
  <v-app-bar color="surface" elevation="1" density="comfortable">
    <!-- Bouton hamburger visible uniquement sur mobile -->
    <v-app-bar-nav-icon
      v-if="!isDesktop"
      @click="toggleDrawer"
    />
    <v-app-bar-title class="font-weight-medium">{{ pageTitle }}</v-app-bar-title>
    <v-spacer />
    <v-btn icon @click="toggleTheme" size="small">
      <v-icon>{{ themeIcon }}</v-icon>
    </v-btn>
    <NotificationBell />
    <v-chip color="primary" text-color="white" size="small" class="ml-2">
      {{ authStore.userRole || 'Admin' }}
    </v-chip>
  </v-app-bar>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useTheme } from 'vuetify'
import { useAuthStore } from '@/store/auth'
import NotificationBell from './NotificationBell.vue'

const route = useRoute()
const theme = useTheme()
const authStore = useAuthStore()

const isDesktop = ref(true)

const pageTitle = computed(() => route.meta.title || route.name || 'Dashboard')
const themeIcon = computed(() =>
  theme.global.name.value === 'dark' ? 'mdi-weather-sunny' : 'mdi-weather-night'
)

const toggleTheme = () => {
  theme.global.name.value = theme.global.name.value === 'dark' ? 'light' : 'dark'
}

const toggleDrawer = () => {
  if (!isDesktop.value) {
    window.dispatchEvent(new CustomEvent('toggle-sidebar'))
  }
}

const handleResize = () => {
  isDesktop.value = window.innerWidth > 768
}

onMounted(() => {
  handleResize()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})
</script>