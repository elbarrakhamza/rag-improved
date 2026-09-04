<template>
  <v-app>
    <Sidebar />
    <v-main>
      <AppHeader />
      <v-container fluid class="px-6 py-4 main-content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </v-container>
    </v-main>
    <NotificationBell />
  </v-app>
</template>

<script setup>
import Sidebar from '@/components/Sidebar.vue'
import AppHeader from '@/components/AppHeader.vue'
import NotificationBell from '@/components/NotificationBell.vue'
</script>

<style scoped>
.main-content {
  max-width: 1400px;
  margin: 0 auto;
}
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>