<template>
  <div
    v-if="metrics"
    class="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4"
    data-testid="metrics-cards"
  >
    <MetricCard label="Net Profit" :value="formatDollar(metrics.total_profit)" :color="metrics.total_profit >= 0 ? 'text-tv-green' : 'text-tv-red'" />
    <MetricCard label="Total Trades" :value="String(metrics.total_trades)" />
    <MetricCard label="Win Rate" :value="`${metrics.win_rate.toFixed(1)}%`" />
    <MetricCard label="Profit Factor" :value="metrics.profit_factor.toFixed(2)" />
    <MetricCard label="Sharpe" :value="metrics.sharpe_ratio.toFixed(2)" />
    <MetricCard label="Max DD" :value="formatDollar(-metrics.max_drawdown)" color="text-tv-red" />
    <MetricCard label="Avg Win" :value="formatDollar(metrics.avg_profit ?? 0)" color="text-tv-green" />
    <MetricCard label="Avg Loss" :value="formatDollar(metrics.avg_loss ?? 0)" color="text-tv-red" />
  </div>
</template>

<script setup lang="ts">
import type { Metrics } from '../types';
import MetricCard from './MetricCard.vue';

defineProps<{
  metrics: Metrics | null;
}>();

function formatDollar(n: number): string {
  const sign = n >= 0 ? '+' : '';
  return `${sign}$${n.toFixed(2)}`;
}
</script>
