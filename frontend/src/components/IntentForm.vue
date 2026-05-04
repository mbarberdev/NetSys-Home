<template>
  <div class="card">
    <h2>Create Intent</h2>

    <label>Device</label>
    <select v-model="device_id">
      <option v-for="d in devices" :value="d.id">
        {{ d.name }}
      </option>
    </select>

    <label>Action</label>
    <select v-model="action">
      <option value="block">Block Device</option>
      <option value="isolate">Isolate Device</option>
      <option value="guest_network">Create Guest Network</option>
      <option value="schedule_block">Schedule Block</option>
    </select>

    <div v-if="action === 'schedule_block'">
      <label>Time</label>
      <input v-model="time" placeholder="e.g. 10PM" />
    </div>

    <button @click="submit">Apply Intent</button>

    <p v-if="error" class="error">{{ error }}</p>

    <div v-if="lastPolicy" style="margin-top: 12px;">
      <span class="badge">Generated Policy</span>
      <p>{{ lastPolicy.rule }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { apiRequest } from '../api'

const devices = ref([])
const device_id = ref(null)
const action = ref('block')
const time = ref('')
const lastPolicy = ref(null)
const error = ref('')

onMounted(async () => {
  try {
    const data = await apiRequest('/devices')
    devices.value = Array.isArray(data) ? data : []

    if (devices.value.length) {
      device_id.value = devices.value[0].id
    }
  } catch (err) {
    console.error('Failed to load devices for intent form:', err)
    error.value = 'Unable to load devices for the intent form.'
  }
})

async function submit() {
  error.value = ''

  try {
    lastPolicy.value = await apiRequest('/intent', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        device_id: device_id.value,
        action: action.value,
        time: time.value
      })
    })
  } catch (err) {
    console.error('Failed to submit intent:', err)
    error.value = 'Unable to apply the intent right now.'
  }
}
</script>
