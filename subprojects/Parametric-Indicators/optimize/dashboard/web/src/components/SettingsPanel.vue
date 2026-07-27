<script setup>
import IndicatorPicker from './IndicatorPicker.vue'
import RunMatrix from './RunMatrix.vue'
import RunKnobs from './RunKnobs.vue'
import CommandPreview from './CommandPreview.vue'
import Presets from './Presets.vue'
import QueueControls from './QueueControls.vue'
</script>

<template>
  <section class="panel">
    <h2>Settings</h2>

    <details open><summary class="sec">Indicators &amp; families</summary><IndicatorPicker /></details>
    <details open><summary class="sec">Instruments × timeframes</summary><RunMatrix /></details>
    <details><summary class="sec">Run knobs</summary><RunKnobs /></details>
    <details open><summary class="sec">Command preview</summary><CommandPreview /></details>
    <details><summary class="sec">Presets</summary><Presets /></details>
    <details><summary class="sec">Run queue</summary><QueueControls /></details>
  </section>
</template>

<style scoped>
details { border-top: 1px solid var(--border); padding: 8px 0; }
.sec { cursor: pointer; font-size: 12px; text-transform: uppercase; letter-spacing: .5px;
  color: var(--muted); font-weight: 600; margin-bottom: 6px; }
</style>
