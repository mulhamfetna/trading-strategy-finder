<script setup>
// Live + final reporting (leaderboard, Pareto, champion detail) is P2/P3.
// P1 keeps a minimal live view so the column isn't empty.
import { store } from '../store.js'
</script>

<template>
  <section class="panel">
    <h2>Reporting</h2>
    <p class="muted">Live figures, Pareto front, and champion leaderboard arrive in P2/P3.</p>
    <div v-if="store.status.studies && store.status.studies.length">
      <h3>Studies</h3>
      <div v-for="s in store.status.studies" :key="s.tf || s.name" class="row mono">
        <span class="pill">{{ s.tf || s.name }}</span>
        <span class="muted">{{ s.complete ?? s.done ?? '?' }} trials</span>
      </div>
    </div>
  </section>
</template>
