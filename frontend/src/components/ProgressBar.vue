<template>
  <div
    class="rounded border border-tv-border bg-tv-surface p-3"
    data-testid="progress-panel"
  >
    <div class="mb-2 flex items-center justify-between text-xs">
      <span class="font-semibold text-tv-blue">
        <span v-if="isRunning">Running backtest...</span>
        <span v-else-if="error" class="text-tv-red">Error</span>
        <span v-else-if="hasResults">Backtest complete{{ elapsedMs !== null ? ` (${formatElapsed(elapsedMs)})` : '' }}</span>
        <span v-else class="text-tv-muted">Idle</span>
      </span>
      <span class="text-tv-muted">{{ percentText }}</span>
    </div>
    <div class="h-2 overflow-hidden rounded bg-tv-tile">
      <div
        class="h-full bg-tv-blue transition-all"
        :style="{ width: barWidth }"
      ></div>
    </div>

    <!-- Live status row -->
    <div
      v-if="progress"
      class="mt-3 grid grid-cols-2 gap-x-4 gap-y-1 text-xs sm:grid-cols-4"
    >
      <StatusItem label="Candle" :value="`${progress.current_idx + 1} / ${progress.total}`" />
      <StatusItem label="Trades" :value="String(progress.trades_so_far)" />
      <StatusItem
        label="PnL"
        :value="formatDollar(progress.pnl_so_far)"
        :color="signColor(progress.pnl_so_far)"
      />
      <StatusItem
        label="Win rate"
        :value="`${progress.win_rate_so_far.toFixed(1)}%`"
      />
      <StatusItem
        label="Position"
        :value="progress.current_position.toUpperCase()"
        :color="
          progress.current_position === 'long'
            ? 'text-tv-green'
            : progress.current_position === 'short'
            ? 'text-tv-red'
            : 'text-tv-muted'
        "
      />
      <StatusItem
        v-if="progress.current_legs_filled !== undefined"
        label="Legs filled"
        :value="`${progress.current_legs_filled} / ${maxLegs}`"
      />
    </div>

    <div v-if="error" class="mt-2 rounded bg-tv-red/10 p-2 text-xs text-tv-red">
      {{ error }}
    </div>

    <!-- BUG-017: non-fatal SSE warnings -->
    <div
      v-if="warnings.length"
      class="mt-2 space-y-1 rounded bg-tv-blue/10 p-2 text-xs text-tv-blue"
      data-testid="progress-warnings"
    >
      <div v-for="(w, i) in warnings" :key="i">{{ w }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useBacktestStore } from '../stores/backtest';
import { useSettingsStore } from '../stores/settings';
import { formatDollar, formatElapsed, signColor } from '../services/format';
import StatusItem from './StatusItem.vue';

const store = useBacktestStore();
const settings = useSettingsStore();

const isRunning = computed(() => store.isRunning);
const progress = computed(() => store.progress);
const error = computed(() => store.error);
const warnings = computed(() => store.warnings);
const elapsedMs = computed(() => store.elapsedMs);
const hasResults = computed(() => store.hasResults);

const maxLegs = computed(
  () => settings.params.leg1_contracts + settings.params.leg2_contracts + settings.params.leg3_contracts,
);

const percentText = computed(() => `${store.percent.toFixed(1)}%`);
const barWidth = computed(() => `${Math.min(100, store.percent)}%`);
</script>
