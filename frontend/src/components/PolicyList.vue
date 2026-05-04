<template>
  <div class="card">
    <h2>Active Policies</h2>

    <p v-if="loading">Loading policies...</p>
    <p v-else-if="error" class="error">{{ error }}</p>

    <ul v-else-if="policies.length">
      <li v-for="p in policies" :key="p.id">
        <span>{{ p.rule }}</span>
        <button @click="remove(p.id)">Remove</button>
      </li>
    </ul>

    <p v-else>No policies yet</p>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { apiRequest } from '../api'

const policies = ref([])
const loading = ref(true)
const error = ref('')

async function load() {
  try {
    const data = await apiRequest('/policies')
    policies.value = Array.isArray(data) ? data : []
    error.value = ''
  } catch (err) {
    console.error('Failed to load policies:', err)
    error.value = 'Unable to load policies.'
  } finally {
    loading.value = false
  }
}

onMounted(load)

async function remove(id) {
  try {
    await apiRequest(`/policies/${id}`, {
      method: 'DELETE'
    })
    await load()
  } catch (err) {
    console.error('Failed to remove policy:', err)
    error.value = 'Unable to remove the selected policy.'
  }
}
</script>
