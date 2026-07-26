<script setup>
import { computed, ref, watch } from 'vue'
import { store } from '../store.js'
import { api } from '../api.js'

const plan = ref(null)
const err = ref('')
const copied = ref(false)
let deb = null

// Preview the FIRST (instrument, tf) of the matrix — one representative command; the queue launches
// one per cell. Includes the current selections so the command reflects the whole cfg.
const previewCfg = computed(() => {
  const c = store.launchCfg()
  c.instrument = (store.cfg.instruments[0]) || 'NQ'
  c.timeframes = store.cfg.timeframes.length ? [store.cfg.timeframes[0]] : ['4h']
  return c
})

function refresh() {
  clearTimeout(deb)
  deb = setTimeout(async () => {
    try { plan.value = await api.plan(previewCfg.value); err.value = '' }
    catch (e) { err.value = e.message }
  }, 300)
}
watch(previewCfg, refresh, { immediate: true, deep: true })

async function copy() {
  try { await navigator.clipboard.writeText(plan.value.command); copied.value = true
    setTimeout(() => (copied.value = false), 1200) } catch { /* ignore */ }
}
const dims = computed(() => plan.value?.dims ?? '—')
const trials = computed(() => plan.value?.recommended_trials ?? '—')
</script>

<template>
  <div>
    <div class="row">
      <span class="pill">{{ dims }} dims</span>
      <span class="pill">~{{ trials }} trials (auto)</span>
      <button v-if="plan?.command" @click="copy">{{ copied ? 'copied ✓' : 'copy' }}</button>
    </div>
    <pre class="cmd mono">{{ err ? ('error: ' + err) : (plan?.command || '…') }}</pre>
    <p class="muted" style="font-size:11px">Representative of the first study; the queue runs one command per matrix cell.</p>
  </div>
</template>

<style scoped>
.cmd { background: var(--bg); border: 1px solid var(--border); border-radius: 6px; padding: 8px;
  white-space: pre-wrap; word-break: break-all; font-size: 11px; color: var(--fg); margin: 6px 0 4px; }
</style>
