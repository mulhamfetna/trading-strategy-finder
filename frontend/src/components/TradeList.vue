<template>
  <div
    class="rounded border border-tv-border bg-tv-surface"
    data-testid="trade-list"
  >
    <div class="flex items-center justify-between border-b border-tv-border px-3 py-2">
      <span class="text-xs font-semibold text-tv-blue">Trades ({{ trades.length }})</span>
      <button
        v-if="trades.length"
        class="flex items-center gap-1 rounded bg-tv-tile px-2 py-0.5 text-xs text-tv-muted hover:bg-tv-border hover:text-tv-text focus:outline-none focus:ring-2 focus:ring-tv-blue"
        title="Export trades to CSV"
        aria-label="Export trades to CSV"
        @click="exportCsv"
      >
        <svg class="h-3 w-3" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
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
            <th class="px-3 py-1">Entry time</th>
            <th class="px-3 py-1">Exit time</th>
            <th class="px-3 py-1">Entry px</th>
            <th class="px-3 py-1">Exit px</th>
            <th class="px-3 py-1">Pts</th>
            <th class="px-3 py-1">$</th>
            <th class="px-3 py-1">Reason</th>
            <th class="px-3 py-1">Box signal</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(t, i) in displayed"
            :key="`${i}-${t.entry_idx}-${t.exit_idx}`"
            class="cursor-pointer border-t border-tv-border transition-colors"
            :class="rowClass(i)"
            :title="boxTooltip(t)"
            @click="onRowClick(t)"
          >
            <td class="px-3 py-1 text-tv-muted">{{ i + 1 }}</td>
            <td class="px-3 py-1">
              <span :class="t.direction === 'long' ? 'text-tv-green' : 'text-tv-red'">
                {{ t.direction.toUpperCase() }}
              </span>
            </td>
            <td class="px-3 py-1 text-tv-muted">{{ candleTime(t.entry_idx) }}</td>
            <td class="px-3 py-1 text-tv-muted tabular-nums">{{ exitTime(t) }}</td>
            <td
              class="px-3 py-1 tabular-nums"
              :class="entryPriceClass(t)"
              :title="entryPriceTooltip(t)"
            >{{ priceFmt.format(t.entry_signal_price) }}</td>
            <td
              class="px-3 py-1 tabular-nums"
              :class="exitPriceClass(t)"
              :title="exitPriceTooltip(t)"
            >{{ priceFmt.format(t.exit_close) }}</td>
            <td class="px-3 py-1 tabular-nums" :class="signColor(t.profit_points) ?? 'text-tv-muted'">
              {{ formatPoints(t.profit_points) }}
            </td>
            <td class="px-3 py-1 font-semibold tabular-nums" :class="signColor(t.profit_dollars) ?? 'text-tv-muted'">
              {{ formatDollar(t.profit_dollars) }}
            </td>
            <td class="px-3 py-1 text-tv-muted truncate max-w-[180px]" :title="t.exit_reason">{{ t.exit_reason }}</td>
            <td class="px-3 py-1 max-w-[200px] truncate" :title="boxCellTooltip(t)">
              <template v-if="t.box_signal">
                <!-- FIX-20: previous "weekly + monthly" rendering implied both
                     contributed. Single-box logic fires on weekly OR monthly
                     (weekly priority). Show only the firing side with a
                     priority/conflict badge when relevant. -->
                <div class="text-[10px] leading-tight">
                  <span class="font-mono text-tv-blue">{{ boxFiringLabel(t.box_signal) }}</span>
                  <span
                    v-if="t.box_signal.conflict"
                    class="ml-1 rounded bg-tv-red/20 px-1 text-[9px] text-tv-red"
                    title="Weekly fired despite monthly disagreement"
                  >conflict</span>
                </div>
                <div class="text-[9px] text-tv-muted leading-tight">
                  {{ boxStartLabel(t.box_signal) }}
                </div>
              </template>
              <span v-else class="text-tv-muted text-[10px]">—</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { ScalingTrade } from '../types';
import { useBacktestStore } from '../stores/backtest';
import { useReplayStore } from '../stores/replay';
import { formatDollar, signColor } from '../services/format';

const props = defineProps<{
  trades: ScalingTrade[];
}>();

const backtest = useBacktestStore();
const replay = useReplayStore();

const displayed = computed(() => props.trades);

// Price column formatter: thousands separator + 2 decimals.
const priceFmt = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

// Signed points: same zero-is-neutral rule as the dollar formatter.
function formatPoints(n: number): string {
  if (Math.abs(n) < 0.05) return '0.0';
  const sign = n > 0 ? '+' : '-';
  return `${sign}${Math.abs(n).toFixed(1)}`;
}

// "2025-01-03 18:00:00" → "2025-01-03 18:00"
function candleTime(idx: number): string {
  const c = backtest.candles[idx];
  if (!c) return '—';
  return c.t.replace('T', ' ').slice(0, 16);
}

function exitTime(t: ScalingTrade): string {
  // Dual-timeframe engine: exit_time is the ISO sub-bar timestamp where the
  // 1-min HARD / TP-target or 2-min SOFT / TRAIL fired. In 4h-only legacy
  // mode (unit tests) exit_time is null and we fall back to the 4h-bar
  // timestamp via exit_idx.
  if (t.exit_time) return t.exit_time.replace('T', ' ').slice(0, 16);
  return candleTime(t.exit_idx);
}

// The trade dict's `entry_signal_price` and `exit_close` are guaranteed to
// appear in the candle OHLC at the corresponding bar — the user can verify
// each trade against the chart. `avg_entry_price` and `exit_price` are the
// algorithm-effective prices used for PnL math (weighted leg avg / SL-TP
// line) and only matter when they DIFFER from the candle-grounded display.
const PRICE_EPSILON = 0.001;

function entryPriceTooltip(t: ScalingTrade): string {
  const diff = Math.abs(t.avg_entry_price - t.entry_signal_price);
  if (diff < PRICE_EPSILON) {
    return `Entry at signal-bar close ${priceFmt.format(t.entry_signal_price)} (single-leg fill).`;
  }
  return [
    `Entry display: ${priceFmt.format(t.entry_signal_price)} (signal-bar close, ${t.legs.length} legs)`,
    `PnL math uses avg fill: ${priceFmt.format(t.avg_entry_price)}`,
    `Legs: ${t.legs.map((l) => `${l.contracts}×${priceFmt.format(l.price)}`).join(', ')}`,
  ].join('\n');
}

function exitPriceTooltip(t: ScalingTrade): string {
  const diff = Math.abs(t.exit_price - t.exit_close);
  if (diff < PRICE_EPSILON) {
    return `Exit at bar close ${priceFmt.format(t.exit_close)} (matches algorithm fill).`;
  }
  return [
    `Exit display: ${priceFmt.format(t.exit_close)} (close of the bar that confirmed ${t.exit_reason})`,
    `PnL math uses algorithm line: ${priceFmt.format(t.exit_price)}`,
    `Diff: ${(t.exit_price - t.exit_close).toFixed(2)} points`,
  ].join('\n');
}

function entryPriceClass(t: ScalingTrade): string {
  // Subtle indicator when the displayed (candle) price differs from the
  // synthetic avg — i.e., a multi-leg trade where the avg blends real and
  // synthetic leg prices.
  return Math.abs(t.avg_entry_price - t.entry_signal_price) > PRICE_EPSILON
    ? 'underline decoration-dotted decoration-tv-muted'
    : '';
}

function exitPriceClass(t: ScalingTrade): string {
  return Math.abs(t.exit_price - t.exit_close) > PRICE_EPSILON
    ? 'underline decoration-dotted decoration-tv-muted'
    : '';
}

function boxTooltip(t: ScalingTrade): string {
  if (!t.box_signal) return `Click to jump to trade in replay`;
  const b = t.box_signal;
  const lines = [
    `Box signal: ${(b.signal ?? '—').toUpperCase()}`,
    `Weekly : ${b.weekly_level ?? '—'} (${(b.weekly_signal ?? '—').toUpperCase()})`,
    b.weekly_upper != null ? `  edges: ${b.weekly_upper.toFixed(2)} / ${b.weekly_lower?.toFixed(2)}` : '',
    `Monthly: ${b.monthly_level ?? '—'} (${(b.monthly_signal ?? '—').toUpperCase()})`,
    b.monthly_upper != null ? `  edges: ${b.monthly_upper.toFixed(2)} / ${b.monthly_lower?.toFixed(2)}` : '',
    `Weekly box start : ${b.weekly_box_start ?? '—'}`,
    `Monthly box start: ${b.monthly_box_start ?? '—'}`,
    b.conflict ? 'NOTE: weekly and monthly disagreed; aggregate uses weekly priority.' : '',
  ];
  return lines.filter(Boolean).join('\n');
}

// FIX-20: show only the firing side (weekly takes priority).
function boxFiringLabel(b: NonNullable<ScalingTrade['box_signal']>): string {
  if (b.weekly_signal && b.weekly_level) return `${b.weekly_level} (W)`;
  if (b.monthly_signal && b.monthly_level) return `${b.monthly_level} (M)`;
  return '—';
}

function boxStartLabel(b: NonNullable<ScalingTrade['box_signal']>): string {
  if (b.weekly_signal && b.weekly_box_start) return `since ${b.weekly_box_start}`;
  if (b.monthly_signal && b.monthly_box_start) return `since ${b.monthly_box_start}`;
  return '';
}

function boxCellTooltip(t: ScalingTrade): string {
  return boxTooltip(t);
}

function onRowClick(t: ScalingTrade) {
  replay.jumpToTrade(t.entry_idx);
}

function rowClass(i: number) {
  if (!replay.isActive) return 'hover:bg-tv-tile';
  if (replay.activeTrade === i) return 'bg-tv-tile ring-1 ring-inset ring-tv-blue';
  return 'hover:bg-tv-tile opacity-60';
}

function exportCsv() {
  // Both candle-grounded and algorithm-effective prices are exported so
  // analysts can verify trades against the chart AND see the PnL math.
  const headers = [
    '#', 'Direction', 'Entry Time', 'Exit Time',
    'Entry Price (signal close)', 'Exit Price (bar close)',
    'Avg Entry (algorithm)', 'Exit Line (algorithm)',
    'Contracts', 'Points', 'Dollars', 'Exit Reason',
    'Weekly Box', 'Monthly Box', 'W-Box Start', 'M-Box Start',
  ];
  const rows = props.trades.map((t, i) => [
    i + 1,
    t.direction.toUpperCase(),
    candleTime(t.entry_idx),
    exitTime(t),
    t.entry_signal_price.toFixed(2),
    t.exit_close.toFixed(2),
    t.avg_entry_price.toFixed(2),
    t.exit_price.toFixed(2),
    t.contracts,
    t.profit_points.toFixed(1),
    t.profit_dollars.toFixed(2),
    t.exit_reason,
    t.box_signal?.weekly_level ?? '',
    t.box_signal?.monthly_level ?? '',
    t.box_signal?.weekly_box_start ?? '',
    t.box_signal?.monthly_box_start ?? '',
  ]);

  const csv = [headers, ...rows]
    .map((row) => row.map((v) => `"${String(v).replace(/"/g, '""')}"`).join(','))
    .join('\n');

  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  // Filename includes HHMMSS so same-day exports don't overwrite each other.
  const now = new Date();
  const stamp =
    now.toISOString().slice(0, 10) +
    '_' +
    String(now.getHours()).padStart(2, '0') +
    String(now.getMinutes()).padStart(2, '0') +
    String(now.getSeconds()).padStart(2, '0');
  a.download = `trades_${stamp}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}
</script>
