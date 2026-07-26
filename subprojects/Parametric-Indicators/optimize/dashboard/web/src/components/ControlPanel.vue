<script setup>
import { computed, onUnmounted, ref, watch } from 'vue'
import { store } from '../store.js'
import { api } from '../api.js'
import ProgressBar from './ProgressBar.vue'
import HealthStrip from './HealthStrip.vue'
import LogTail from './LogTail.vue'

const busy = ref(false)
const msg = ref('')
const prog = ref({ done: 0, target: 0, rate_per_min: 0, eta_seconds: null, feasible: null, elapsed_seconds: 0 })
let progTimer = null

const running = computed(() => !!store.status.running)
// Progress + logs follow the first selected timeframe (P1 control panel tracks one study; the
// full per-study matrix lives in the reporting column in P2).
const tf = computed(() => (store.cfg.timeframes && store.cfg.timeframes[0]) || '4h')

async function act(fn, label) {
  busy.value = true; msg.value = ''
  try {
    const r = await fn()
    msg.value = r && r.detail ? `${label}: ${r.detail.slice(-160)}` : `${label} ok`
    await store.refreshStatus()
  } catch (e) {
    msg.value = `${label} failed: ${e.message}`
  } finally {
    busy.value = false
  }
}
const start = () => act(() => api.run(store.launchCfg()), 'start')
const resume = () => act(() => api.resume(store.launchCfg()), 'resume')
const stop = () => act(() => api.stop(), 'stop')

async function pollProgress() {
  try { prog.value = await api.liveProgress(tf.value, 0) } catch { /* keep last */ }
}
watch(running, (on) => {
  if (on && !progTimer) { pollProgress(); progTimer = setInterval(pollProgress, 3000) }
  if (!on && progTimer) { clearInterval(progTimer); progTimer = null; pollProgress() }
}, { immediate: true })
onUnmounted(() => progTimer && clearInterval(progTimer))
</script>

<template>
  <section class="panel">
    <h2>Control</h2>

    <div class="row">
      <button class="primary" :disabled="busy || running" @click="start">▶ Start</button>
      <button :disabled="busy || running" @click="resume">⤴ Resume</button>
      <button class="danger" :disabled="busy || !running" @click="stop">■ Stop</button>
    </div>
    <p v-if="msg" class="mono muted" style="word-break:break-word">{{ msg }}</p>

    <h3>Progress <span class="pill">{{ tf }}</span></h3>
    <ProgressBar
      :done="prog.done" :target="prog.target" :rate-per-min="prog.rate_per_min"
      :eta-seconds="prog.eta_seconds" :feasible="prog.feasible" :elapsed-seconds="prog.elapsed_seconds" />

    <h3>Health</h3>
    <HealthStrip />

    <h3>Logs</h3>
    <LogTail :tf="tf" />
  </section>
</template>
