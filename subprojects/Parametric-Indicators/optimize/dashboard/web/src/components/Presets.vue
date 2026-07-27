<script setup>
import { onMounted, ref } from 'vue'
import { store } from '../store.js'
import { api } from '../api.js'

const names = ref([])
const presets = ref({})
const name = ref('')
const msg = ref('')

async function load() {
  try { const r = await api.presets(); names.value = r.names || []; presets.value = r.presets || {} }
  catch (e) { msg.value = e.message }
}
onMounted(load)

async function save() {
  const n = name.value.trim()
  if (!n) return
  // Persist the full UI cfg so Apply restores the panel exactly (not just the launch subset).
  await api.presetSave(n, JSON.parse(JSON.stringify(store.cfg)))
  msg.value = `saved "${n}"`; name.value = ''
  await load()
}
function apply(n) {
  const c = presets.value[n]
  if (!c) return
  Object.assign(store.cfg, c)
  msg.value = `applied "${n}"`
}
async function del(n) {
  await api.presetDelete(n)
  msg.value = `deleted "${n}"`
  await load()
}
</script>

<template>
  <div>
    <div class="row">
      <input v-model="name" placeholder="preset name" style="flex:1" @keyup.enter="save" />
      <button class="primary" @click="save" :disabled="!name.trim()">Save current</button>
    </div>
    <div class="row" v-for="n in names" :key="n">
      <span class="mono" style="flex:1">{{ n }}</span>
      <button @click="apply(n)">Apply</button>
      <button class="danger" @click="del(n)">✕</button>
    </div>
    <p v-if="!names.length" class="muted">no saved presets yet</p>
    <p v-if="msg" class="muted mono">{{ msg }}</p>
  </div>
</template>
