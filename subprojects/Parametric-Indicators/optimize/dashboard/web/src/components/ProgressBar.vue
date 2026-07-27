<script setup>
import { computed } from 'vue'

const props = defineProps({
  done: { type: Number, default: 0 },
  target: { type: Number, default: 0 },
  ratePerMin: { type: Number, default: 0 },
  etaSeconds: { type: Number, default: null },
  feasible: { type: Number, default: null },
  elapsedSeconds: { type: Number, default: 0 },
})

const pct = computed(() => {
  if (!props.target) return 0
  return Math.min(100, Math.round((props.done / props.target) * 1000) / 10)
})

function humanize(s) {
  if (s == null) return '—'
  s = Math.max(0, Math.round(s))
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60
  if (h) return `${h}h ${m}m`
  if (m) return `${m}m ${sec}s`
  return `${sec}s`
}
const eta = computed(() => humanize(props.etaSeconds))
const elapsed = computed(() => humanize(props.elapsedSeconds))
</script>

<template>
  <div class="pb">
    <div class="pb-track"><div class="pb-fill" :style="{ width: pct + '%' }"></div></div>
    <div class="pb-meta mono">
      <span>{{ done }}<span class="muted"> / {{ target || '?' }}</span> ({{ pct }}%)</span>
      <span class="muted">·</span>
      <span>{{ ratePerMin ? ratePerMin.toFixed(1) : '0' }}/min</span>
      <span class="muted">·</span>
      <span>ETA <b>{{ eta }}</b></span>
      <span class="muted">·</span>
      <span>elapsed {{ elapsed }}</span>
      <span v-if="feasible != null" class="muted">·</span>
      <span v-if="feasible != null">{{ feasible }} feasible</span>
    </div>
  </div>
</template>

<style scoped>
.pb-track { height: 10px; background: var(--panel-2); border: 1px solid var(--border);
  border-radius: 999px; overflow: hidden; }
.pb-fill { height: 100%; background: var(--accent); transition: width .4s ease; }
.pb-meta { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; margin-top: 6px; }
</style>
