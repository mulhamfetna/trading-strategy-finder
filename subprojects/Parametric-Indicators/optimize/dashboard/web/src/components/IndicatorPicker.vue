<script setup>
import { computed, ref } from 'vue'
import { store } from '../store.js'

// The active selection list is `only_indicators` or `exclude_indicators`, chosen by the mode.
// mode 'all' = search over everything (no restriction); 'only' = restrict; 'exclude' = all-except.
const search = ref('')
const mode = computed({
  get: () => store.cfg.indicator_mode,
  set: (v) => { store.cfg.indicator_mode = v },
})
const activeList = computed(() =>
  mode.value === 'exclude' ? store.cfg.exclude_indicators : store.cfg.only_indicators)

const groups = computed(() => {
  const q = search.value.trim().toLowerCase()
  const by = {}
  for (const ind of store.config.indicators) {
    if (q && !ind.key.toLowerCase().includes(q) && !(ind.family || '').includes(q)) continue
    ;(by[ind.family || 'other'] ||= []).push(ind)
  }
  return Object.entries(by).sort((a, b) => a[0].localeCompare(b[0]))
})

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
function toggleFamily(members) {
  const keys = members.map((m) => m.key)
  const state = familyState(members)
  const l = activeList.value
  if (state === 'all') {
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
    <div class="row" v-if="mode !== 'all'">
      <input v-model="search" placeholder="search indicator / family…" style="flex:1" />
    </div>

    <div class="picker" v-if="mode !== 'all'">
      <details v-for="[fam, members] in groups" :key="fam" open>
        <summary>
          <label @click.prevent="toggleFamily(members)">
            <input type="checkbox"
                   :checked="familyState(members) === 'all'"
                   :indeterminate.prop="familyState(members) === 'some'" />
            <b>{{ fam }}</b> <span class="muted">({{ members.length }})</span>
          </label>
        </summary>
        <label v-for="ind in members" :key="ind.key" class="ind">
          <input type="checkbox" :checked="isSel(ind.key)" @change="toggle(ind.key)" />
          <span class="mono">{{ ind.key }}</span>
        </label>
      </details>
    </div>
    <p v-else class="muted">All {{ store.config.indicators.length }} indicators are in the search
      (optimizer decides which to enable).</p>
  </div>
</template>

<style scoped>
.picker { max-height: 320px; overflow: auto; border: 1px solid var(--border); border-radius: 6px; padding: 8px; }
summary { cursor: pointer; padding: 3px 0; }
.ind { display: flex; gap: 6px; align-items: center; padding: 1px 0 1px 20px; font-size: 12px; }
</style>
