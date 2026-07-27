<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { store } from '../store.js'
import { api } from '../api.js'

const study = ref(null)       // active run's study name
const summary = ref(null)     // /api/study/{name} result
const champs = ref([])        // champion leaderboard
const expanded = ref(null)    // expanded champion row key
let timer = null

async function refresh() {
  try {
    const st = await api.runState()
    study.value = st.study
    if (st.study) summary.value = await api.study(st.study)
    else summary.value = null
  } catch { /* keep last */ }
}
async function loadChampions() {
  try { champs.value = (await api.champions()).champions || [] } catch { /* ignore */ }
}
onMounted(() => { refresh(); loadChampions(); timer = setInterval(refresh, 4000) })
onUnmounted(() => timer && clearInterval(timer))

const rowKey = (c) => `${c.instrument}_${c.tf}`
const toggle = (c) => { expanded.value = expanded.value === rowKey(c) ? null : rowKey(c) }

// Use the SAME host the page was loaded from (LAN IP, VPN IP, or localhost) so the link works from
// any device / tunnel — optuna-dashboard binds the same host as the control plane, just a different port.
const optunaHost = computed(() => window.location.hostname || 'localhost')
const optunaUrl = computed(() => `http://${optunaHost.value}:${store.config.optuna_port || 8082}/dashboard/`)
const isLocal = computed(() => ['localhost', '127.0.0.1'].includes(optunaHost.value))
const feas = (f) => (f === true ? '✓' : f === false ? '✗' : '—')
</script>

<template>
  <section class="panel">
    <h2>Reporting</h2>

    <h3>Live graphs (optuna-dashboard)</h3>
    <p class="muted" style="font-size:12px">Pareto front, optimization history &amp; param importance for every study.</p>
    <div class="row">
      <a class="btn" :href="optunaUrl" target="_blank" rel="noopener">Open optuna-dashboard ↗</a>
    </div>
    <pre v-if="isLocal" class="tip mono">via localhost — tunnel the optuna port first:
ssh -L {{ store.config.optuna_port || 8082 }}:127.0.0.1:{{ store.config.optuna_port || 8082 }} amd-trading</pre>

    <h3>Active run result <span v-if="study" class="pill">{{ study }}</span></h3>
    <template v-if="summary && summary.ok">
      <div class="row mono" style="font-size:12px">
        <span class="pill">{{ summary.complete }} complete</span>
        <span class="pill">{{ summary.pruned }} pruned</span>
        <span class="pill" :class="summary.feasible_count ? 'ok' : ''">{{ summary.feasible_count }} feasible</span>
      </div>
      <div v-if="summary.best_feasible" class="best">
        <b>Best feasible</b> · trial {{ summary.best_feasible.trial }} ·
        P/L <b>${{ summary.best_feasible.pnl.toLocaleString() }}</b> ·
        DD ${{ summary.best_feasible.dd?.toLocaleString() }} · win {{ summary.best_feasible.win }}%
      </div>
      <p v-else class="muted" style="font-size:12px">No feasible champion yet
        (DD ≤ cap·P/L) — needs more trials.</p>

      <h3>Top trials by P/L</h3>
      <table class="tt mono">
        <thead><tr><th>#</th><th>P/L</th><th>DD</th><th>win%</th><th>feas</th></tr></thead>
        <tbody>
          <tr v-for="r in summary.top" :key="r.trial" :class="{ feas: r.feasible }">
            <td>{{ r.trial }}</td><td>{{ r.pnl?.toLocaleString() }}</td>
            <td>{{ r.dd?.toLocaleString() }}</td><td>{{ r.win }}</td><td>{{ feas(r.feasible) }}</td>
          </tr>
        </tbody>
      </table>
    </template>
    <p v-else-if="study" class="muted">loading results…</p>
    <p v-else class="muted">Run a study to see its results here.</p>

    <h3>Champion leaderboard <span class="pill">{{ champs.length }}</span></h3>
    <p v-if="!champs.length" class="muted" style="font-size:12px">no champions found in optimize/results.</p>
    <table v-else class="tt mono">
      <thead><tr><th>inst</th><th>tf</th><th>P/L</th><th>DD</th><th>win%</th><th>#ind</th><th></th></tr></thead>
      <tbody>
        <template v-for="c in champs" :key="rowKey(c)">
          <tr class="crow" @click="toggle(c)">
            <td>{{ c.instrument }}</td><td>{{ c.tf }}</td>
            <td>{{ c.pnl?.toLocaleString() }}</td><td>{{ c.dd?.toLocaleString() }}</td>
            <td>{{ c.win }}</td><td>{{ c.n_indicators }}</td>
            <td>{{ expanded === rowKey(c) ? '▾' : '▸' }}</td>
          </tr>
          <tr v-if="expanded === rowKey(c)" class="cdetail">
            <td colspan="7">
              <div><b>median P/L</b> ${{ c.median_pnl?.toLocaleString() }} · <b>deployed</b> {{ c.deployed ? '✓' : '—' }}</div>
              <div><b>indicators:</b> {{ c.indicators.join(', ') || '(none)' }}</div>
              <div><b>box:</b> SL {{ c.box.sl_soft?.toFixed?.(0) }}/{{ c.box.sl_hard?.toFixed?.(0) }}
                · TP {{ c.box.tp?.toFixed?.(0) }} · gate {{ c.box.gate_pct?.toFixed?.(0) }}%
                · cooldown {{ c.box.cooldown }} · K {{ c.box.k }} · cap {{ c.box.cap_mode }}/{{ c.box.cap_1min }}</div>
            </td>
          </tr>
        </template>
      </tbody>
    </table>
  </section>
</template>

<style scoped>
.btn { display: inline-block; padding: 6px 12px; border: 1px solid var(--accent); border-radius: 6px;
  color: var(--accent); text-decoration: none; font-size: 13px; }
.btn:hover { background: var(--panel-2); }
.tip { background: var(--bg); border: 1px solid var(--border); border-radius: 6px; padding: 6px 8px;
  font-size: 11px; color: var(--muted); margin: 6px 0; white-space: pre-wrap; word-break: break-all; }
.pill.ok { color: var(--ok); border-color: var(--ok); }
.best { border: 1px solid var(--ok); border-radius: 6px; padding: 8px; margin: 8px 0; font-size: 12px; }
.tt { width: 100%; border-collapse: collapse; font-size: 11px; }
.tt th, .tt td { text-align: right; padding: 2px 6px; border-bottom: 1px solid var(--border); }
.tt th:first-child, .tt td:first-child { text-align: left; }
.tt tr.feas td { color: var(--ok); }
.crow { cursor: pointer; }
.crow:hover td { background: var(--panel-2); }
.cdetail td { text-align: left; color: var(--muted); font-size: 11px; padding: 6px 8px; line-height: 1.6; }
</style>
