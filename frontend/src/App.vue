<template>
  <div class="container">
    <h1>🌐 NetSys Home</h1>
    <p class="subtitle">
      Intent-based network control for home users
    </p>

    <DeviceList />
    <IntentForm />
    <PolicyList />
  </div>
</template>

<script setup>
import DeviceList from './components/DeviceList.vue'
import IntentForm from './components/IntentForm.vue'
import PolicyList from './components/PolicyList.vue'
</script>