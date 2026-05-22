<template>
  <div
    class="rounded border border-tv-border bg-tv-surface"
    data-testid="trade-list"
  >
    <div class="border-b border-tv-border px-3 py-2 text-xs font-semibold text-tv-blue">
      Trades ({{ trades.length }})
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
import type { ScalingTrade } from '../types';
import { useReplayStore } from '../stores/replay';

const props = defineProps<{
  trades: ScalingTrade[];
}>();

const replay = useReplayStore();

const displayed = props.trades; // all trades — 646 rows is trivial for the browser

function onRowClick(t: ScalingTrade) {
  replay.jumpToTrade(t.entry_idx);
}

function rowClass(i: number) {
  if (!replay.isActive) return 'hover:bg-tv-tile';
  if (replay.activeTrade === i) return 'bg-tv-tile ring-1 ring-inset ring-tv-blue';
  return 'hover:bg-tv-tile opacity-60';
}
</script>
