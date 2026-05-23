<template>
  <div data-testid="metrics-cards">
    <div class="mb-2 flex items-center justify-between px-1 text-xs text-tv-muted">
      <span>Report</span>
      <span>{{ metrics ? `${metrics.total_trades} trades` : 'No report yet' }}</span>
    </div>
    <div
      v-if="metrics"
      class="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4"
    >
      <MetricCard label="Net Profit" :value="formatDollar(metrics.total_profit)" :color="signColor(metrics.total_profit)" />
      <MetricCard label="Total Trades" :value="String(metrics.total_trades)" />
      <MetricCard label="Win Rate" :value="`${metrics.win_rate.toFixed(1)}%`" />
      <MetricCard label="Profit Factor" :value="formatRatio(metrics.profit_factor)" />
      <MetricCard label="Sharpe" :value="formatRatio(metrics.sharpe_ratio)" />
      <MetricCard label="Max DD" :value="formatDrawdown(metrics.max_drawdown)" :color="metrics.max_drawdown > 0 ? 'text-tv-red' : undefined" />
      <MetricCard label="Avg Win" :value="formatDollar(metrics.avg_profit ?? 0)" :color="signColor(metrics.avg_profit ?? 0)" />
      <MetricCard label="Avg Loss" :value="formatDollar(metrics.avg_loss ?? 0)" :color="signColor(metrics.avg_loss ?? 0)" />
    </div>
    <div
      v-else
      class="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4"
      data-testid="metrics-cards-placeholder"
    >
      <MetricCard v-for="label in placeholderLabels" :key="label" :label="label" value="—" />
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Metrics } from '../types';
import MetricCard from './MetricCard.vue';
import { formatDollar, formatDrawdown, formatRatio, signColor } from '../services/format';

defineProps<{
  metrics: Metrics | null;
}>();

const placeholderLabels = [
  'Net Profit', 'Total Trades', 'Win Rate', 'Profit Factor',
  'Sharpe', 'Max DD', 'Avg Win', 'Avg Loss',
];
</script>
