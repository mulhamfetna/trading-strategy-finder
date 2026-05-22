<template>
  <div
    class="rounded border border-tv-border bg-tv-surface"
    data-testid="trade-list"
  >
    <div class="flex items-center justify-between border-b border-tv-border px-3 py-2">
      <span class="text-xs font-semibold text-tv-blue">Trades ({{ trades.length }})</span>
      <button
        v-if="trades.length"
        class="flex items-center gap-1 rounded bg-tv-tile px-2 py-0.5 text-xs text-tv-muted hover:bg-tv-border hover:text-tv-text"
        title="Export trades to CSV"
        @click="exportCsv"
      >
        <svg class="h-3 w-3" viewBox="0 0 16 16" fill="currentColor">
          <path d="M8 1v9m0 0-3-3m3 3 3-3M2 12v2a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1v-2" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        Save CSV
      </button>
    </div>
    <div v-if="trades.length === 0" class="p-4 text-center text-xs text-tv-muted">
      No trades yet. Run a backtest to see the trade list.
    </div>
    <div v-else class="max-h-96 overflow-y-auto">
      <table class="w-full text-xs">
        <thead class="sticky top-0 bg-tv-surface">
          <tr class="text-left text-tv-muted">
            <th class="px-3 py-1">#</th>
            <th class="px-3 py-1">Dir</th>
            <th class="px-3 py-1">Entry</th>
            <th class="px-3 py-1">Exit</th>
            <th class="px-3 py-1">Pts</th>
            <th class="px-3 py-1">$</th>
            <th class="px-3 py-1">Reason</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(t, i) in displayed"
            :key="`${t.entry_idx}-${t.exit_idx}`"
            class="cursor-pointer border-t border-tv-border transition-colors"
            :class="rowClass(i)"
            :title="`Click to jump to trade ${i + 1} in replay`"
            @click="onRowClick(t)"
          >
            <td class="px-3 py-1 text-tv-muted">{{ i + 1 }}</td>
            <td class="px-3 py-1">
              <span :class="t.direction === 'long' ? 'text-tv-green' : 'text-tv-red'">
                {{ t.direction.toUpperCase() }}
              </span>
            </td>
            <td class="px-3 py-1">{{ t.avg_entry_price.toFixed(2) }}</td>
            <td class="px-3 py-1">{{ t.exit_price.toFixed(2) }}</td>
            <td class="px-3 py-1" :class="t.profit_points >= 0 ? 'text-tv-green' : 'text-tv-red'">
              {{ t.profit_points >= 0 ? '+' : '' }}{{ t.profit_points.toFixed(1) }}
            </td>
            <td class="px-3 py-1 font-semibold" :class="t.profit_dollars >= 0 ? 'text-tv-green' : 'text-tv-red'">
              {{ t.profit_dollars >= 0 ? '+' : '' }}${{ t.profit_dollars.toFixed(2) }}
            </td>
            <td class="px-3 py-1 text-tv-muted">{{ t.exit_reason }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { ScalingTrade } from '../types';
import { useReplayStore } from '../stores/replay';

const props = defineProps<{
  trades: ScalingTrade[];
}>();

const replay = useReplayStore();

const displayed = computed(() => props.trades);

function onRowClick(t: ScalingTrade) {
  replay.jumpToTrade(t.entry_idx);
}

function rowClass(i: number) {
  if (!replay.isActive) return 'hover:bg-tv-tile';
  if (replay.activeTrade === i) return 'bg-tv-tile ring-1 ring-inset ring-tv-blue';
  return 'hover:bg-tv-tile opacity-60';
}

function exportCsv() {
  const headers = ['#', 'Direction', 'Avg Entry', 'Exit Price', 'Contracts', 'Points', 'Dollars', 'Exit Reason'];
  const rows = props.trades.map((t, i) => [
    i + 1,
    t.direction.toUpperCase(),
    t.avg_entry_price.toFixed(2),
    t.exit_price.toFixed(2),
    t.contracts,
    t.profit_points.toFixed(1),
    t.profit_dollars.toFixed(2),
    t.exit_reason,
  ]);

  const csv = [headers, ...rows]
    .map((row) => row.map((v) => `"${String(v).replace(/"/g, '""')}"`).join(','))
    .join('\n');

  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `trades_${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}
</script>
