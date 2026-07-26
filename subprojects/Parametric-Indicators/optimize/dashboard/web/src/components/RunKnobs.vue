<script setup>
import { computed } from 'vue'
import { store } from '../store.js'

const cfg = store.cfg
// per-(inst,tf) trial cells, shown only in 'per' mode — keyed exactly as queue.expand expects (`inst:tf`).
const perCells = computed(() => {
  const out = []
  for (const inst of cfg.instruments) for (const tf of cfg.timeframes) out.push(`${inst}:${tf}`)
  return out
})
</script>

<template>
  <div>
    <h3>Trials</h3>
    <div class="row">
      <label><input type="radio" value="auto" v-model="cfg.trials_mode" /> auto (∝ dimensions)</label>
      <label><input type="radio" value="one" v-model="cfg.trials_mode" /> one count</label>
      <label><input type="radio" value="per" v-model="cfg.trials_mode" /> per study</label>
    </div>
    <div class="row" v-if="cfg.trials_mode === 'one'">
      <label>trials <input type="number" min="0" step="500" v-model.number="cfg.trials" style="width:110px" /></label>
    </div>
    <div v-if="cfg.trials_mode === 'per'">
      <div class="row" v-for="k in perCells" :key="k">
        <label class="mono" style="width:120px">{{ k }}</label>
        <input type="number" min="0" step="500" v-model.number="cfg.per_trials[k]" style="width:110px" />
      </div>
      <p v-if="!perCells.length" class="muted">pick instruments × timeframes first.</p>
    </div>

    <h3>Warm / cold start</h3>
    <div class="row">
      <label><input type="radio" :value="false" v-model="cfg.cold_start" /> warm (from champion)</label>
      <label><input type="radio" :value="true" v-model="cfg.cold_start" /> cold (fresh)</label>
    </div>

    <h3>Indicator frame</h3>
    <div class="row">
      <label><input type="radio" :value="true" v-model="cfg.ind_1min" /> 1-minute indicators</label>
      <label><input type="radio" :value="false" v-model="cfg.ind_1min" /> decision-TF</label>
    </div>

    <h3>Engine &amp; sampler</h3>
    <div class="row">
      <label>engine
        <select v-model="cfg.engine">
          <option v-for="e in store.config.engines" :key="e" :value="e">{{ e }}</option>
        </select>
      </label>
      <label>sampler
        <select v-model="cfg.sampler">
          <option v-for="s in store.config.samplers" :key="s" :value="s">{{ s }}</option>
        </select>
      </label>
    </div>
    <div class="row" v-if="cfg.engine === 'two_stage'">
      <label>stage-B
        <select v-model="cfg.stage_b">
          <option value="">—</option>
          <option v-for="s in store.config.stage_b" :key="s" :value="s">{{ s }}</option>
        </select>
      </label>
    </div>

    <h3>Search knobs</h3>
    <div class="row">
      <label><input type="checkbox" v-model="cfg.split_sltp" /> split long/short SL·TP</label>
    </div>
    <div class="row">
      <label>reference
        <select v-model="cfg.reference">
          <option value="">none</option>
          <option v-for="i in store.config.instruments" :key="i" :value="i">{{ i }}</option>
        </select>
      </label>
      <label>K-cap (max enabled)
        <input type="number" min="0" v-model.number="cfg.max_enabled" style="width:80px" />
      </label>
    </div>
    <div class="row">
      <label>DD·P/L cap
        <input type="number" min="0" step="0.05" v-model.number="cfg.dd_cap" style="width:90px" placeholder="default" />
      </label>
    </div>
  </div>
</template>
