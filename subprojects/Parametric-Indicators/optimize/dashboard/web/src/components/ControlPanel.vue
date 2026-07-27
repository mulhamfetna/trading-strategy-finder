<script setup>
import { computed, onUnmounted, ref, watch } from 'vue'
import { store } from '../store.js'
import { api, streamRunLogs } from '../api.js'
import ProgressBar from './ProgressBar.vue'
import HealthStrip from './HealthStrip.vue'

const busy = ref(false)
const msg = ref('')
const run = ref({ running: false, study: null, tf: null, pid: null, returncode: null, target: 0,
                  progress: { done: 0, target: 0, rate_per_min: 0, eta_seconds: null, elapsed_seconds: 0 } })
const logLines = ref([])
let stateTimer = null
let logEs = null

const missing = computed(() => store.runMissing())
const canRun = computed(() => missing.value.length === 0 && !run.value.running && !busy.value)

async function pollState() {
  try { run.value = await api.runState() } catch { /* keep last */ }
}

async function start() {
  // Big-run guard: an auto run is the FULL search (can be ~47k trials ≈ days). Confirm first.
  if (store.cfg.trials_mode === 'auto') {
    try {
      const plan = await api.plan(store.runCfg())
      const n = plan?.recommended_trials || 0
      if (n > 20000 && !confirm(
        `Auto mode runs the FULL search: ~${n.toLocaleString()} trials (${plan.dims} dims). ` +
        `At ~200 trials/min that's roughly ${Math.round(n / 200 / 60)} h — it can take days. ` +
        `Use "one count" for a short run instead.\n\nLaunch the full ${n.toLocaleString()}-trial run anyway?`)) {
        return
      }
    } catch { /* if the plan call fails, don't block the run */ }
  }
  busy.value = true; msg.value = ''
  try {
    const r = await api.run(store.runCfg())
    if (!r.ok) { msg.value = r.detail || 'could not start'; return }
    msg.value = `started ${r.study} (pid ${r.pid}) → target ${r.target}`
    logLines.value = []
    if (logEs) logEs.close()
    logEs = streamRunLogs(
      (ln) => { logLines.value.push(ln); if (logLines.value.length > 500) logLines.value.splice(0, 200) },
      (rc) => { msg.value += ` — finished (rc ${rc})`; pollState() },
    )
    await pollState()
  } catch (e) { msg.value = `start failed: ${e.message}` }
  finally { busy.value = false }
}

async function stop() {
  busy.value = true
  try { const r = await api.stop(); msg.value = r.detail || 'stopped'; await pollState() }
  catch (e) { msg.value = `stop failed: ${e.message}` }
  finally { busy.value = false }
}

// poll owned-run state every 2s
stateTimer = setInterval(pollState, 2000)
pollState()
onUnmounted(() => { if (stateTimer) clearInterval(stateTimer); if (logEs) logEs.close() })

const shownLog = computed(() => logLines.value.slice(-200).join('\n') || '(no output yet)')
</script>

<template>
  <section class="panel">
    <h2>Control</h2>

    <div class="row">
      <button class="primary" :disabled="!canRun" @click="start">▶ Run</button>
      <button class="danger" :disabled="busy || !run.running" @click="stop">■ Stop</button>
      <span v-if="run.running" class="pill run">running</span>
    </div>

    <p v-if="run.detached" class="detached">
      ⚠ A run is still active from before a restart (detached): <b>{{ run.study }}</b>
      — reconnected from the process table. Hit <b>Stop</b> to clear it.
    </p>
    <p v-if="missing.length && !run.detached" class="missing">
      ⚠ Select before running: <b>{{ missing.join(', ') }}</b>
    </p>
    <p v-if="msg" class="mono muted" style="word-break:break-word">{{ msg }}</p>

    <template v-if="run.study">
      <h3>Progress <span class="pill">{{ run.study }}</span></h3>
      <ProgressBar
        :done="run.progress?.done || 0" :target="run.progress?.target || run.target"
        :rate-per-min="run.progress?.rate_per_min || 0" :eta-seconds="run.progress?.eta_seconds"
        :elapsed-seconds="run.progress?.elapsed_seconds || 0" />
      <p class="mono muted" v-if="!run.running && run.returncode != null">exited (rc {{ run.returncode }})</p>
    </template>

    <h3>Health</h3>
    <HealthStrip />

    <h3>Live output</h3>
    <pre class="log mono">{{ shownLog }}</pre>
  </section>
</template>

<style scoped>
.missing { color: var(--warn); font-size: 13px; margin: 6px 0; }
.detached { color: var(--warn); font-size: 12px; margin: 6px 0; border: 1px solid var(--warn);
  border-radius: 6px; padding: 6px 8px; }
.pill.run { color: var(--ok); border-color: var(--ok); }
.log { background: var(--bg); border: 1px solid var(--border); border-radius: 6px; padding: 8px;
  height: 240px; overflow: auto; white-space: pre-wrap; word-break: break-word; font-size: 11px;
  color: var(--muted); margin: 6px 0 0; }
</style>
