<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import { api } from '../api.js'

const h = ref({ cpu_pct: null, mem_pct: null, workers: null, n_studies: 0, running: false })
let timer = null

async function poll() {
  try { h.value = await api.health() } catch { /* keep last */ }
}
onMounted(() => { poll(); timer = setInterval(poll, 5000) })
onUnmounted(() => timer && clearInterval(timer))

const fmt = (v, suffix = '') => (v == null ? '—' : v + suffix)
</script>

<template>
  <div class="health mono">
    <span class="chip" :class="{ hot: h.cpu_pct > 90 }">cpu {{ fmt(h.cpu_pct, '%') }}</span>
    <span class="chip" :class="{ hot: h.mem_pct > 90 }">mem {{ fmt(h.mem_pct, '%') }}</span>
    <span class="chip">workers {{ fmt(h.workers) }}</span>
    <span class="chip">studies {{ h.n_studies }}</span>
    <span class="chip" :class="h.running ? 'run' : ''">{{ h.running ? 'running' : 'idle' }}</span>
  </div>
</template>

<style scoped>
.health { display: flex; gap: 6px; flex-wrap: wrap; }
.chip { padding: 2px 8px; border-radius: 6px; border: 1px solid var(--border);
  background: var(--panel-2); font-size: 11px; }
.chip.hot { color: var(--bad); border-color: var(--bad); }
.chip.run { color: var(--ok); border-color: var(--ok); }
</style>
