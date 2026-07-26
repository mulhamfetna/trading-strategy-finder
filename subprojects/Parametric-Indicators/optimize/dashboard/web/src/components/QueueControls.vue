<script setup>
import { onMounted, ref } from 'vue'
import { store } from '../store.js'
import { api } from '../api.js'

const items = ref([])
const busy = ref(false)
const msg = ref('')

async function refresh() {
  try { const r = await api.queueState(); items.value = r.queue || [] } catch { /* ignore */ }
}
onMounted(refresh)

async function launch() {
  busy.value = true; msg.value = ''
  try {
    const cfg = store.launchCfg()
    if (store.cfg.max_trials) cfg.max_trials = Number(store.cfg.max_trials)     // budget guard (enforced)
    const r = await api.queueLaunch(cfg)
    items.value = r.queue || []
    msg.value = `launched ${items.value.length} studies`
    await store.refreshStatus()
  } catch (e) { msg.value = `launch failed: ${e.message}` }
  finally { busy.value = false }
}
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
    <p class="muted" style="font-size:11px">Max-trials is enforced (each study is capped &amp; de-auto’d).
      Wall-clock is advisory in P1 — surfaced, not yet auto-stopped by the watchdog.</p>

    <div class="row">
      <button class="primary" :disabled="busy" @click="launch">⇉ Launch matrix</button>
      <button :disabled="busy" @click="refresh">↻ Refresh</button>
    </div>
    <p v-if="msg" class="mono muted">{{ msg }}</p>

    <div class="row" v-for="(it, i) in items" :key="i">
      <span class="mono" style="flex:1">{{ it.instrument }} · {{ it.timeframe }}</span>
      <span class="pill" :class="it.state === 'launched' ? 'ok' : it.state === 'failed' ? 'bad' : ''">{{ it.state }}</span>
    </div>
  </div>
</template>

<style scoped>
.pill.ok { color: var(--ok); border-color: var(--ok); }
.pill.bad { color: var(--bad); border-color: var(--bad); }
</style>
