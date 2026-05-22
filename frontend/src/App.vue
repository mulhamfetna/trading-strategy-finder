<template>
  <div class="flex h-full flex-col bg-tv-bg text-tv-text">
    <header class="flex items-center justify-between border-b border-tv-border bg-tv-surface px-4 py-3">
      <div>
        <h1 class="text-lg font-semibold text-tv-blue">NQ 1-1-2 Scaling Strategy Dashboard</h1>
        <p class="text-xs text-tv-muted">FastAPI + Vue 3 + Lightweight Charts &middot; phase D</p>
      </div>
      <div class="flex items-center gap-2">
        <button
          v-if="backtest.candles.length && !replay.isActive"
          class="rounded bg-tv-tile px-4 py-2 text-sm font-semibold text-tv-text shadow hover:bg-tv-border"
          data-testid="replay-button"
          @click="replay.activate()"
        >
          Replay
        </button>
        <button
          class="rounded bg-tv-blue px-4 py-2 text-sm font-semibold text-white shadow disabled:opacity-50"
          :disabled="backtest.isRunning"
          data-testid="backtest-button"
          @click="backtest.run()"
        >
          {{ backtest.isRunning ? 'Running...' : 'Run Backtest' }}
        </button>
      </div>
    </header>

    <div class="flex flex-1 overflow-hidden">
      <!-- Left: settings -->
      <aside class="w-96 shrink-0 overflow-y-auto border-r border-tv-border bg-tv-bg p-3">
        <SettingsPanel />
      </aside>

      <!-- Right: progress + replay + chart + metrics + trades -->
      <main class="flex flex-1 flex-col gap-3 overflow-y-auto p-3">
        <ProgressBar />

        <ReplayBar />

        <section class="flex-none">
          <div class="mb-2 flex items-center justify-between px-1 text-xs text-tv-muted">
            <span>Candles</span>
            <span>{{ backtest.candles.length ? `${backtest.candles.length} loaded` : 'No candles yet' }}</span>
          </div>
          <div class="min-h-[520px] overflow-hidden rounded border border-tv-border bg-tv-surface">
            <ChartPane :candles="backtest.candles" :trades="backtest.trades" />
          </div>
        </section>

        <section class="flex-shrink-0">
          <MetricsCards :metrics="backtest.metrics" />
        </section>

        <section>
          <TradeList :trades="backtest.trades" />
        </section>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onBeforeUnmount } from 'vue';
import ChartPane from './components/ChartPane.vue';
import MetricsCards from './components/MetricsCards.vue';
import ProgressBar from './components/ProgressBar.vue';
import ReplayBar from './components/ReplayBar.vue';
import SettingsPanel from './components/SettingsPanel.vue';
import TradeList from './components/TradeList.vue';
import { useBacktestStore } from './stores/backtest';
import { useReplayStore } from './stores/replay';

const backtest = useBacktestStore();
const replay = useReplayStore();

function onKey(e: KeyboardEvent) {
  if (!replay.isActive) return;
  if (e.target instanceof HTMLInputElement || e.target instanceof HTMLSelectElement) return;
  if (e.code === 'Space') {
    e.preventDefault();
    replay.isPlaying ? replay.pause() : replay.play();
  } else if (e.code === 'ArrowRight') {
    e.preventDefault();
    replay.stepForward();
  } else if (e.code === 'ArrowLeft') {
    e.preventDefault();
    replay.stepBack();
  }
}

onMounted(() => document.addEventListener('keydown', onKey));
onBeforeUnmount(() => document.removeEventListener('keydown', onKey));
</script>
