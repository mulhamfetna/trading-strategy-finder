<script setup>
// Phase C fills this in (start/stop/resume, progress bar + ETA, health + logs).
import { store } from '../store.js'
</script>

<template>
  <section class="panel">
    <h2>Control</h2>
    <p class="muted">Run lifecycle, progress &amp; ETA, health and logs — built in Phase C.</p>
    <p class="mono muted">status: {{ store.status.ok ? 'reachable' : 'unknown' }}</p>
  </section>
</template>
