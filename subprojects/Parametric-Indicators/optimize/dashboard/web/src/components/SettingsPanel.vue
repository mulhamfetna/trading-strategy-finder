<script setup>
// Phase D fills this in (indicator+family picker, instruments×tf matrix, run knobs,
// command preview, presets, run queue + budget guard).
import { store } from '../store.js'
</script>

<template>
  <section class="panel">
    <h2>Settings</h2>
    <p class="muted">Indicator/family selection, instruments × timeframes, run knobs,
      command preview, presets, and the run queue — built in Phase D.</p>
    <p class="mono muted">{{ store.config.indicators.length }} indicators across
      {{ new Set(store.config.indicators.map(i => i.family)).size }} families loaded.</p>
  </section>
</template>
