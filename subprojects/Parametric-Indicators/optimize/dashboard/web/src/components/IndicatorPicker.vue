<script setup>
import { computed, ref } from 'vue'
import { store } from '../store.js'

// Active selection list = only_indicators or exclude_indicators, chosen by mode.
const search = ref('')
const groupBy = ref('family')                       // 'family' | 'lead_lag'
const classOn = ref({ leading: true, lagging: true, filter: true })   // cadence filter (narrows the list)

const mode = computed({
  get: () => store.cfg.indicator_mode,
  set: (v) => { store.cfg.indicator_mode = v },
})
const activeList = computed(() =>
  mode.value === 'exclude' ? store.cfg.exclude_indicators : store.cfg.only_indicators)

const LL_LABEL = { leading: '🟢 Leading', lagging: '🔵 Lagging', filter: '⚙ Filter / Regime' }
const LL_ORDER = { leading: 0, lagging: 1, filter: 2 }

const groups = computed(() => {
  const q = search.value.trim().toLowerCase()
  const by = {}
  for (const ind of store.config.indicators) {
    const ll = ind.lead_lag || 'lagging'
    if (!classOn.value[ll]) continue                              // cadence filter
    if (q && !ind.key.toLowerCase().includes(q) && !(ind.family || '').includes(q)) continue
    const gkey = groupBy.value === 'lead_lag' ? ll : (ind.family || 'other')
    ;(by[gkey] ||= []).push(ind)
  }
  const entries = Object.entries(by)
  if (groupBy.value === 'lead_lag')
    entries.sort((a, b) => LL_ORDER[a[0]] - LL_ORDER[b[0]])
  else
    entries.sort((a, b) => a[0].localeCompare(b[0]))
  return entries
})
const groupLabel = (g) => (groupBy.value === 'lead_lag' ? (LL_LABEL[g] || g) : g)

const isSel = (k) => activeList.value.includes(k)
function toggle(k) {
  const l = activeList.value
  const i = l.indexOf(k)
  if (i >= 0) l.splice(i, 1); else l.push(k)
}
function familyState(members) {
  const keys = members.map((m) => m.key)
  const n = keys.filter(isSel).length
  return n === 0 ? 'none' : n === keys.length ? 'all' : 'some'
}
function toggleGroup(members) {
  const keys = members.map((m) => m.key)
  const l = activeList.value
  if (familyState(members) === 'all') {
    for (const k of keys) { const i = l.indexOf(k); if (i >= 0) l.splice(i, 1) }
  } else {
    for (const k of keys) if (!l.includes(k)) l.push(k)
  }
}
const selectedCount = computed(() => (mode.value === 'all' ? 0 : activeList.value.length))
</script>

<template>
  <div>
    <div class="row">
      <label><input type="radio" value="all" v-model="mode" /> all</label>
      <label><input type="radio" value="only" v-model="mode" /> only these</label>
      <label><input type="radio" value="exclude" v-model="mode" /> all except</label>
      <span class="pill" v-if="mode !== 'all'">{{ selectedCount }} selected</span>
    </div>

    <template v-if="mode !== 'all'">
      <div class="row">
        <input v-model="search" placeholder="search indicator / family…" style="flex:1" />
      </div>
      <div class="row">
        <label class="muted">group by</label>
        <label><input type="radio" value="family" v-model="groupBy" /> family</label>
        <label><input type="radio" value="lead_lag" v-model="groupBy" /> cadence</label>
        <span class="sep"></span>
        <label class="ll leading"><input type="checkbox" v-model="classOn.leading" /> leading</label>
        <label class="ll lagging"><input type="checkbox" v-model="classOn.lagging" /> lagging</label>
        <label class="ll filter"><input type="checkbox" v-model="classOn.filter" /> filter</label>
      </div>

      <div class="picker">
        <details v-for="[g, members] in groups" :key="g" open>
          <summary>
            <label @click.prevent="toggleGroup(members)">
              <input type="checkbox" :checked="familyState(members) === 'all'"
                     :indeterminate.prop="familyState(members) === 'some'" />
              <b>{{ groupLabel(g) }}</b> <span class="muted">({{ members.length }})</span>
            </label>
          </summary>
          <label v-for="ind in members" :key="ind.key" class="ind">
            <input type="checkbox" :checked="isSel(ind.key)" @change="toggle(ind.key)" />
            <span class="mono">{{ ind.key }}</span>
            <span class="badge" :class="ind.lead_lag">{{ (ind.lead_lag || 'lagging')[0].toUpperCase() }}</span>
          </label>
        </details>
      </div>
    </template>
    <p v-else class="muted">All {{ store.config.indicators.length }} indicators are in the search
      (optimizer decides which to enable).</p>
  </div>
</template>

<style scoped>
.picker { max-height: 320px; overflow: auto; border: 1px solid var(--border); border-radius: 6px; padding: 8px; }
summary { cursor: pointer; padding: 3px 0; }
.ind { display: flex; gap: 6px; align-items: center; padding: 1px 0 1px 20px; font-size: 12px; }
.sep { width: 1px; height: 16px; background: var(--border); margin: 0 4px; }
.ll { font-size: 12px; }
.ll.leading { color: var(--ok); } .ll.lagging { color: var(--accent); } .ll.filter { color: var(--warn); }
.badge { margin-left: auto; font-size: 10px; width: 15px; height: 15px; line-height: 15px; text-align: center;
  border-radius: 3px; border: 1px solid var(--border); color: var(--muted); }
.badge.leading { color: var(--ok); border-color: var(--ok); }
.badge.lagging { color: var(--accent); border-color: var(--accent); }
.badge.filter { color: var(--warn); border-color: var(--warn); }
</style>
