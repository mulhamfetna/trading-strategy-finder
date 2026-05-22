<template>
  <div class="flex h-full flex-col bg-tv-bg text-tv-text">
    <header class="flex items-center justify-between border-b border-tv-border bg-tv-surface px-4 py-3">
      <div>
        <h1 class="text-lg font-semibold text-tv-blue">NQ 1-1-2 Scaling Strategy Dashboard</h1>
        <p class="text-xs text-tv-muted">FastAPI + Vue 3 + Lightweight Charts &middot; phase C</p>
      </div>
      <button
        class="rounded bg-tv-blue px-4 py-2 text-sm font-semibold text-white shadow disabled:opacity-50"
        :disabled="backtest.isRunning"
        data-testid="backtest-button"
        @click="backtest.run()"
      >
        {{ backtest.isRunning ? 'Running...' : 'Run Backtest' }}
      </button>
    </header>

    <div class="flex flex-1 overflow-hidden">
      <!-- Left: settings -->
      <aside class="w-96 shrink-0 overflow-y-auto border-r border-tv-border bg-tv-bg p-3">
        <SettingsPanel />
      </aside>

      <!-- Right: progress + chart + metrics + trades -->
      <main class="flex flex-1 flex-col gap-3 overflow-y-auto p-3">
        <ProgressBar />

        <section class="flex-shrink-0">
          <MetricsCards :metrics="backtest.metrics" />
        </section>

        <section class="min-h-[400px] flex-1 overflow-hidden rounded border border-tv-border bg-tv-surface">
          <ChartPane :candles="backtest.candles" :trades="backtest.trades" />
        </section>

        <section>
          <TradeList :trades="backtest.trades" />
        </section>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import ChartPane from './components/ChartPane.vue';
import MetricsCards from './components/MetricsCards.vue';
import ProgressBar from './components/ProgressBar.vue';
import SettingsPanel from './components/SettingsPanel.vue';
import TradeList from './components/TradeList.vue';
import { useBacktestStore } from './stores/backtest';

const backtest = useBacktestStore();
</script>
