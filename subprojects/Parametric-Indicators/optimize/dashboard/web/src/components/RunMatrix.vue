<script setup>
import { computed } from 'vue'
import { store } from '../store.js'

function toggle(list, v) {
  const i = list.indexOf(v)
  if (i >= 0) list.splice(i, 1); else list.push(v)
}
const cells = computed(() => {
  const out = []
  for (const inst of store.cfg.instruments)
    for (const tf of store.cfg.timeframes) out.push(`${inst} · ${tf}`)
  return out
})
</script>

<template>
  <div>
    <h3>Instruments</h3>
    <div class="row">
      <label v-for="inst in store.config.instruments" :key="inst" class="tag">
        <input type="checkbox" :checked="store.cfg.instruments.includes(inst)"
               @change="toggle(store.cfg.instruments, inst)" /> {{ inst }}
      </label>
    </div>

    <h3>Timeframes</h3>
    <div class="row">
      <label v-for="tf in store.config.timeframes" :key="tf" class="tag">
        <input type="checkbox" :checked="store.cfg.timeframes.includes(tf)"
               @change="toggle(store.cfg.timeframes, tf)" /> {{ tf }}
      </label>
    </div>

    <h3>Studies to launch <span class="pill">{{ cells.length }}</span></h3>
    <div class="grid">
      <span v-for="c in cells" :key="c" class="cell mono">{{ c }}</span>
      <span v-if="!cells.length" class="muted">select ≥1 instrument and ≥1 timeframe</span>
    </div>
  </div>
</template>

<style scoped>
.tag { border: 1px solid var(--border); border-radius: 6px; padding: 3px 8px; font-size: 12px; }
.grid { display: flex; flex-wrap: wrap; gap: 6px; }
.cell { border: 1px solid var(--accent); border-radius: 6px; padding: 3px 8px; font-size: 11px; }
</style>
