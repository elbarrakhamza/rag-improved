<template>
  <v-navigation-drawer
    v-model="drawer"
    :permanent="isDesktop"
    :temporary="!isDesktop"
    app
    class="sidebar-fixed"
    width="250"
  >
    <!-- En-tête fixe -->
    <div class="sidebar-header">
      <v-icon size="32" color="primary" class="mr-2">mdi-elevator</v-icon>
      <div>
        <div class="text-h6 font-weight-bold" style="line-height:1.2;">RAG Admin</div>
        <div class="text-caption" style="color: #888;">v2.0</div>
      </div>
    </div>

    <v-divider class="my-2" />

    <v-list class="nav-list" density="compact">
      <v-list-item
        v-for="item in menuItems"
        :key="item.to"
        :to="item.to"
        :prepend-icon="item.icon"
        :title="item.title"
        :active="route.path === item.to"
        exact
        class="nav-item-static"
      />
    </v-list>

    <v-divider class="my-2" />

    <v-list class="nav-list">
      <v-list-item
        prepend-icon="mdi-logout"
        title="Déconnexion"
        @click="logout"
        class="nav-item-static"
      />
    </v-list>
  </v-navigation-drawer>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'

const drawer = ref(false)
const isDesktop = ref(true)

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const menuItems = [
  { icon: 'mdi-view-dashboard', title: 'Dashboard', to: '/' },
  { icon: 'mdi-cloud-upload', title: 'Upload', to: '/upload' },
  { icon: 'mdi-format-list-bulleted', title: 'Tâches', to: '/tasks' },
  { icon: 'mdi-file-document', title: 'Documents', to: '/documents' },
  { icon: 'mdi-key', title: 'Clés API', to: '/apikeys' },
  { icon: 'mdi-message-reply', title: 'Feedback', to: '/feedback' },
  { icon: 'mdi-cached', title: 'Cache', to: '/cache' },
  { icon: 'mdi-history', title: 'Historique', to: '/history' }
]

const logout = () => {
  authStore.logout()
  router.push('/login')
}

const handleResize = () => {
  isDesktop.value = window.innerWidth > 768
  if (isDesktop.value) {
    drawer.value = true
  } else {
    drawer.value = false
  }
}

const handleToggle = () => {
  if (!isDesktop.value) {
    drawer.value = !drawer.value
  }
}

onMounted(() => {
  handleResize()
  window.addEventListener('resize', handleResize)
  window.addEventListener('toggle-sidebar', handleToggle)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  window.removeEventListener('toggle-sidebar', handleToggle)
})
</script>

<style scoped>
.sidebar-fixed {
  transition: none !important;
  background: #1a1a2e !important;
  color: #eee;
}

.sidebar-fixed .v-navigation-drawer__content {
  background: #1a1a2e !important;
}

.sidebar-header {
  display: flex;
  align-items: center;
  padding: 16px 16px 8px 16px;
  color: #fff;
}

.nav-list .v-list-item {
  color: #ccc;
  border-radius: 0;
  transition: none !important;
  background: transparent !important;
}

.nav-list .v-list-item:hover {
  background: transparent !important;
  color: #fff !important;
}

.nav-list .v-list-item--active {
  background: rgba(255, 152, 0, 0.15) !important;
  color: #FF9800 !important;
  border-right: 3px solid #FF9800;
}

.nav-list .v-list-item--active .v-list-item__prepend .v-icon {
  color: #FF9800 !important;
}

.v-list-item {
  transition: none !important;
}

.v-list-item__overlay {
  display: none !important;
}
</style>