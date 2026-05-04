<template>
  <div class="card">
    <h2>Devices</h2>

    <p v-if="loading">Loading devices...</p>
    <p v-else-if="error" class="error">{{ error }}</p>

    <ul v-else-if="devices.length">
      <li v-for="d in devices" :key="d.id">
        <span>
          {{ d.name }}
          <span class="badge">{{ d.type }}</span>
        </span>
      </li>
    </ul>

    <p v-else>No devices found</p>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { apiRequest } from '../api'

const devices = ref([])
const loading = ref(true)
const error = ref('')

onMounted(async () => {
  try {
    const data = await apiRequest('/devices')
    devices.value = Array.isArray(data) ? data : []
  } catch (err) {
    console.error('Failed to load devices:', err)
    error.value = 'Unable to load devices. Check the Flask server and Vite proxy.'
  } finally {
    loading.value = false
  }
})
</script>
