<template>
  <v-menu offset-y>
    <template v-slot:activator="{ props }">
      <v-btn icon v-bind="props" size="small">
        <v-badge :content="unreadCount" color="error" overlap>
          <v-icon>mdi-bell</v-icon>
        </v-badge>
      </v-btn>
    </template>
    <v-list width="380" max-height="450" class="overflow-y-auto">
      <v-list-item>
        <v-list-item-title class="font-weight-bold">Notifications</v-list-item-title>
        <template v-slot:append>
          <v-btn variant="text" size="small" @click="markAllRead" color="primary">
            Tout marquer lu
          </v-btn>
        </template>
      </v-list-item>
      <v-divider />
      <v-list-item v-for="n in notifications" :key="n.id" :class="{ 'bg-blue-lighten-5': !n.is_read }" lines="two">
        <v-list-item-title>{{ n.title }}</v-list-item-title>
        <v-list-item-subtitle>{{ n.message }}</v-list-item-subtitle>
        <v-list-item-subtitle class="text-caption text-medium-emphasis mt-1">
          {{ new Date(n.created_at).toLocaleString() }}
        </v-list-item-subtitle>
        <template v-slot:append>
          <v-btn icon size="x-small" variant="text" @click="markRead(n.id)" v-if="!n.is_read">
            <v-icon size="small">mdi-check</v-icon>
          </v-btn>
        </template>
      </v-list-item>
      <v-list-item v-if="!notifications.length">
        <v-list-item-title class="text-center text-medium-emphasis py-4">
          Aucune notification
        </v-list-item-title>
      </v-list-item>
    </v-list>
  </v-menu>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { createApiClient } from '@/api/client'

const api = createApiClient()

const notifications = ref([])
const unreadCount = ref(0)
let interval = null

const load = async () => {
  try {
    const res = await api.get('/admin/notifications?limit=20')
    notifications.value = res.data.notifications || []
    unreadCount.value = res.data.unread_count || 0
  } catch (e) {
    console.error(e)
  }
}

const markRead = async (id) => {
  try {
    await api.post(`/admin/notifications/${id}/read`)
    await load()
  } catch (e) { console.error(e) }
}

const markAllRead = async () => {
  try {
    await api.post('/admin/notifications/read-all')
    await load()
  } catch (e) { console.error(e) }
}

onMounted(() => {
  load()
  interval = setInterval(load, 30000)
})

onUnmounted(() => {
  if (interval) clearInterval(interval)
})
</script>