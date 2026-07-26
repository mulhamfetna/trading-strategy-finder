<script setup>
import { computed, onUnmounted, ref, watch } from 'vue'
import { streamLogs } from '../api.js'

const props = defineProps({ tf: { type: String, default: '4h' } })

const lines = ref([])
const filter = ref('all')
const MAX = 400
let es = null

const FILTERS = {
  all: () => true,
  errors: (l) => /error|exception|traceback|fail/i.test(l),
  pruned: (l) => /prune/i.test(l),
  feasible: (l) => /feasible/i.test(l),
}
const shown = computed(() => lines.value.filter(FILTERS[filter.value] || FILTERS.all).slice(-200))

function subscribe(tf) {
  if (es) es.close()
  lines.value = []
  es = streamLogs(tf, (line) => {
    lines.value.push(line)
    if (lines.value.length > MAX) lines.value.splice(0, lines.value.length - MAX)
  })
}
watch(() => props.tf, (tf) => subscribe(tf), { immediate: true })
onUnmounted(() => es && es.close())
</script>

<template>
  <div class="logtail">
    <div class="row">
      <label>filter</label>
      <select v-model="filter">
        <option value="all">all</option>
        <option value="errors">errors</option>
        <option value="pruned">pruned</option>
        <option value="feasible">feasible</option>
      </select>
      <span class="muted mono">{{ shown.length }} lines · {{ tf }}</span>
    </div>
    <pre class="log mono">{{ shown.join('\n') || '(no log output yet)' }}</pre>
  </div>
</template>

<style scoped>
.log { background: var(--bg); border: 1px solid var(--border); border-radius: 6px;
  padding: 8px; height: 220px; overflow: auto; white-space: pre-wrap; word-break: break-word;
  font-size: 11px; color: var(--muted); margin: 6px 0 0; }
</style>
