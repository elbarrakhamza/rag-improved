<!-- src/components/StatCard.vue -->
<template>
  <v-card class="stat-card" elevation="1" rounded="lg">
    <v-card-text>
      <div class="d-flex align-center">
        <v-avatar color="primary" size="48" variant="tonal" class="mr-3">
          <v-icon :icon="icon" size="24" color="primary" />
        </v-avatar>
        <div>
          <div class="text-h4 font-weight-bold">{{ value }}</div>
          <div class="text-caption text-medium-emphasis">{{ label }}</div>
        </div>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup>
defineProps({
  icon: String,
  label: String,
  value: [String, Number]
})
</script>

<style scoped>
.stat-card {
  transition: transform 0.2s, box-shadow 0.2s;
}
.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0,0,0,0.08);
}
</style>