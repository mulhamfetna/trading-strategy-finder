<script setup>
import { onUnmounted, onMounted, ref } from 'vue'
import { store } from '../store.js'
import { api } from '../api.js'

const items = ref([])
const busy = ref(false)
const msg = ref('')
let poll = null

async function refresh() {
  try { const r = await api.queueState(); items.value = r.queue || [] } catch { /* ignore */ }
}
onMounted(() => { refresh(); poll = setInterval(refresh, 3000) })
onUnmounted(() => poll && clearInterval(poll))

async function launch() {
  busy.value = true; msg.value = ''
  try {
    const cfg = store.launchCfg()
    if (store.cfg.max_trials) cfg.max_trials = Number(store.cfg.max_trials)   // budget guard (enforced in expand)
    const r = await api.queueLaunch(cfg)
    items.value = r.queue || []
    const running = items.value.filter(i => i.state === 'running').length
    const deferred = items.value.filter(i => i.state === 'deferred').length
    msg.value = `launched ${running} owned run(s)` + (deferred ? ` · ${deferred} deferred (worker cap)` : '')
  } catch (e) { msg.value = `launch failed: ${e.message}` }
  finally { busy.value = false }
}

async function stopAll() {
  busy.value = true
  try { const r = await api.queueStop(); msg.value = `stopped ${r.stopped} run(s)`; await refresh() }
  catch (e) { msg.value = `stop failed: ${e.message}` }
  finally { busy.value = false }
}

const pct = (it) => (it.target ? Math.min(100, Math.round((it.done || 0) / it.target * 100)) : 0)
const anyRunning = () => items.value.some(i => i.running)
</script>

<template>
  <div>
    <h3>Budget guard</h3>
    <div class="row">
      <label>max trials / study
        <input type="number" min="0" step="1000" v-model.number="store.cfg.max_trials" style="width:110px" placeholder="none" />
      </label>
      <label>max wall-clock (min)
        <input type="number" min="0" v-model.number="store.cfg.max_wallclock_min" style="width:90px" placeholder="none" />
        <span class="pill">advisory</span>
      </label>
    </div>
    <p class="muted" style="font-size:11px">Each matrix cell launches its OWN optimizer subprocess (capped at
      cores−2; extra cells are deferred, not dropped). Max-trials is enforced; wall-clock is advisory in P1.</p>

    <div class="row">
      <button class="primary" :disabled="busy" @click="launch">⇉ Launch matrix</button>
      <button class="danger" :disabled="busy || !anyRunning()" @click="stopAll">■ Stop all</button>
      <button :disabled="busy" @click="refresh">↻</button>
    </div>
    <p v-if="msg" class="mono muted">{{ msg }}</p>

    <div v-for="(it, i) in items" :key="i" class="qitem">
      <div class="row" style="margin:2px 0">
        <span class="mono" style="flex:1">{{ it.instrument }} · {{ it.timeframe }}</span>
        <span class="pill" :class="it.state">{{ it.state }}</span>
        <span v-if="it.target" class="muted mono">{{ it.done || 0 }}/{{ it.target }}</span>
      </div>
      <div v-if="it.state === 'running'" class="bar"><div class="fill" :style="{ width: pct(it) + '%' }"></div></div>
    </div>
    <p v-if="!items.length" class="muted">no matrix launched yet</p>
  </div>
</template>

<style scoped>
.qitem { border-top: 1px solid var(--border); padding: 4px 0; }
.pill.running { color: var(--ok); border-color: var(--ok); }
.pill.finished { color: var(--accent); border-color: var(--accent); }
.pill.failed, .pill.stopped { color: var(--bad); border-color: var(--bad); }
.pill.deferred { color: var(--warn); border-color: var(--warn); }
.bar { height: 5px; background: var(--panel-2); border-radius: 999px; overflow: hidden; margin-top: 2px; }
.fill { height: 100%; background: var(--accent); transition: width .4s ease; }
</style>
