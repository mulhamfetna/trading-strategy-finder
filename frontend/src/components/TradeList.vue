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
    <div v-else class="max-h-64 overflow-y-auto">
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
            class="border-t border-tv-border"
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
      <div v-if="trades.length > displayed.length" class="border-t border-tv-border px-3 py-1 text-center text-xs text-tv-muted">
        (showing first {{ displayed.length }} of {{ trades.length }})
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { ScalingTrade } from '../types';

const props = defineProps<{
  trades: ScalingTrade[];
}>();

const MAX_ROWS = 200;
const displayed = computed(() => props.trades.slice(0, MAX_ROWS));
</script>
