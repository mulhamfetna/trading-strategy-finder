<template>
  <div class="flex h-full flex-col bg-tv-bg text-tv-text">
    <header class="border-b border-tv-border bg-tv-surface p-4">
      <h1 class="text-lg font-semibold text-tv-blue">NQ Trading Dashboard</h1>
      <p class="text-xs text-tv-muted">FastAPI + Vue 3 + Lightweight Charts</p>
    </header>

    <main class="flex flex-1 flex-col gap-4 p-4">
      <div class="flex items-center gap-3">
        <button
          class="rounded bg-tv-blue px-3 py-1 text-sm font-semibold text-white disabled:opacity-50"
          :disabled="store.loading"
          @click="reload"
        >
          {{ store.loading ? 'Loading...' : 'Load 2025-09-01 to 2025-09-30 (test split)' }}
        </button>
        <span v-if="store.range" class="text-xs text-tv-muted">
          {{ store.candles.length }} candles &middot; {{ store.range.start }} to {{ store.range.end }}
        </span>
        <span v-if="store.error" class="text-xs text-tv-red">{{ store.error }}</span>
      </div>

      <div class="flex-1 overflow-hidden rounded border border-tv-border bg-tv-surface">
        <ChartPane :candles="store.candles" />
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue';
import ChartPane from './components/ChartPane.vue';
import { useCandlesStore } from './stores/candles';

const store = useCandlesStore();

async function reload() {
  await store.load('2025-09-01', '2025-09-30', 'test');
}

onMounted(reload);
</script>
