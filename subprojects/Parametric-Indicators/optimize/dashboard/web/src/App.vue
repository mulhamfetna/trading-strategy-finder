<script setup>
import { onMounted, onUnmounted } from 'vue'
import { store } from './store.js'
import ControlPanel from './components/ControlPanel.vue'
import SettingsPanel from './components/SettingsPanel.vue'
import ReportingPanel from './components/ReportingPanel.vue'

let poll = null
onMounted(async () => {
  await store.loadConfig()
  poll = setInterval(() => store.refreshStatus(), 5000)
})
onUnmounted(() => poll && clearInterval(poll))
</script>

<template>
  <div class="topbar">
    <h1>Optimizer Control Center</h1>
    <span class="pill">{{ store.config.indicators.length }} indicators</span>
    <span class="pill">{{ store.config.instruments.length }} instruments</span>
    <div class="spacer"></div>
    <span class="conn" :class="store.conn">{{ store.conn }}</span>
  </div>

  <div class="columns">
    <ControlPanel />
    <SettingsPanel />
    <ReportingPanel />
  </div>
</template>
