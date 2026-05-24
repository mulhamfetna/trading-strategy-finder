<template>
  <!-- CSS variables sourced from CHART_THEME so scoped CSS doesn't
       need to repeat any hex literals. -->
  <div
    class="chart-shell"
    data-testid="chart-pane"
    :style="{
      '--chart-muted': CHART_THEME.muted,
      '--chart-ema-fast': CHART_THEME.emaFast,
    }"
  >
    <div ref="containerRef" class="chart-container" />
    <div v-if="hoveredCandle" class="chart-tooltip" data-testid="candle-tooltip">
      <div class="ct-time">
        <span class="ct-date">{{ hoveredCandle.t.split('T')[0] }}</span>
        {{ ' ' }}
        <span class="ct-hr">{{ hoveredCandle.t.split('T')[1]?.substring(0, 5) }}</span>
      </div>
      <div class="ct-row">
        <span class="ct-lbl">O</span>{{ hoveredCandle.o.toLocaleString() }}
        <span class="ct-lbl">H</span><span class="ct-bull">{{ hoveredCandle.h.toLocaleString() }}</span>
      </div>
      <div class="ct-row">
        <span class="ct-lbl">L</span><span class="ct-bear">{{ hoveredCandle.l.toLocaleString() }}</span>
        <span class="ct-lbl">C</span>{{ hoveredCandle.c.toLocaleString() }}
      </div>
      <div class="ct-row">
        <span class="ct-lbl">V</span>{{ hoveredCandle.v.toLocaleString() }}
      </div>
    </div>
    <div v-if="!candles.length" class="chart-empty">
      No candles loaded yet.
    </div>
    <!-- QC-CP-4: explain when an EMA disappears for lack of candles -->
    <div
      v-if="emaWarning"
      class="chart-warning"
      data-testid="ema-warning"
    >
      {{ emaWarning }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, watch, ref, toRefs, nextTick } from 'vue';
import {
  createChart,
  createSeriesMarkers,
  CandlestickSeries,
  LineSeries,
  HistogramSeries,
  LineStyle,
  type IChartApi,
  type ISeriesApi,
  type ISeriesMarkersPluginApi,
  type LineData,
  type HistogramData,
  type MouseEventParams,
  type SeriesMarker,
  type Time,
} from 'lightweight-charts';
import type { BoxRect, Candle, ScalingTrade } from '../types';
import { BoxesPrimitive } from './BoxesPrimitive';
import {
  computeEMA,
  computeRSI,
  toLwcData,
  toUTCTimestamp,
} from '../services/chart_helpers';
import { CHART_THEME } from '../services/chart_theme';
import { useSettingsStore } from '../stores/settings';
import { useReplayStore } from '../stores/replay';

const props = withDefaults(
  defineProps<{
    candles: Candle[];
    trades?: ScalingTrade[];
    boxes?: BoxRect[];
  }>(),
  { trades: () => [], boxes: () => [] },
);

const { candles, trades, boxes } = toRefs(props);
const settings = useSettingsStore();
const replay = useReplayStore();

const containerRef = ref<HTMLDivElement | null>(null);
const hoveredCandle = ref<Candle | null>(null);

// QC-CP-4: explain to the user when an EMA goes blank because there
// aren't enough candles loaded for its warmup period.
const emaWarning = computed(() => {
  const n = candles.value.length;
  if (n === 0) return '';
  const missing: string[] = [];
  if (settings.indicators.emaFast > n) missing.push(`EMA${settings.indicators.emaFast}`);
  if (settings.indicators.emaSlow > n) missing.push(`EMA${settings.indicators.emaSlow}`);
  if (!missing.length) return '';
  return `${missing.join(' / ')} hidden — only ${n} candles loaded.`;
});

let chart: IChartApi | null = null;
let candleSeries: ISeriesApi<'Candlestick'> | null = null;
let markersApi: ISeriesMarkersPluginApi<Time> | null = null;
let emaFastSeries: ISeriesApi<'Line'> | null = null;
let emaSlowSeries: ISeriesApi<'Line'> | null = null;
let volSeries: ISeriesApi<'Histogram'> | null = null;
let rsiSeries: ISeriesApi<'Line'> | null = null;
let boxesPrimitive: BoxesPrimitive | null = null;

function toMarkers(
  rows: Candle[],
  tradeRows: ScalingTrade[],
  viewTo = Infinity,
): SeriesMarker<Time>[] {
  if (!rows.length || !tradeRows.length) return [];
  const markers: SeriesMarker<Time>[] = [];
  for (const t of tradeRows) {
    const entry = rows[t.entry_idx];
    if (entry) {
      markers.push({
        time: toUTCTimestamp(entry.t),
        position: t.direction === 'long' ? 'belowBar' : 'aboveBar',
        color: t.direction === 'long' ? CHART_THEME.bull : CHART_THEME.bear,
        shape: t.direction === 'long' ? 'arrowUp' : 'arrowDown',
        text: t.direction === 'long' ? 'B' : 'S',
      });
    }
    // Only show exit marker once the exit candle is in view.
    if (t.exit_idx <= viewTo) {
      const exit = rows[t.exit_idx];
      if (exit) {
        markers.push({
          time: toUTCTimestamp(exit.t),
          position: t.direction === 'long' ? 'aboveBar' : 'belowBar',
          color: t.profit_dollars >= 0 ? CHART_THEME.bull : CHART_THEME.bear,
          shape: 'square',
          text: `${t.profit_dollars >= 0 ? '+' : ''}${t.profit_points.toFixed(0)}`,
        });
      }
    }
  }
  // Sort numerically (UTCTimestamp numbers, not strings)
  return markers.sort((a, b) => (a.time as number) - (b.time as number));
}

// ---- apply data to all series ----

// FIX-17: track the candles array identity so we only call `fitContent()`
// when the underlying dataset actually changes (new backtest result),
// NOT on every replay scrub tick or indicator-period change. Calling
// fitContent on every tick destroys any manual pan/zoom the user did.
let lastCandlesRef: typeof candles.value | null = null;

function applyData() {
  if (!candleSeries) return;
  // In replay mode, show only candles up to the current replay index.
  const viewTo = replay.isActive ? replay.currentIdx : candles.value.length - 1;
  const rows = candles.value.slice(0, viewTo + 1);
  const closes = rows.map((r) => r.c);
  const times = rows.map((r) => toUTCTimestamp(r.t));
  const candlesChanged = candles.value !== lastCandlesRef;
  lastCandlesRef = candles.value;

  // candles
  candleSeries.setData(toLwcData(rows));

  // EMA overlays
  const buildLineData = (vals: (number | null)[]): LineData<Time>[] =>
    vals.reduce<LineData<Time>[]>((acc, v, i) => {
      if (v !== null) acc.push({ time: times[i], value: v });
      return acc;
    }, []);

  emaFastSeries?.setData(buildLineData(computeEMA(closes, settings.indicators.emaFast)));
  emaSlowSeries?.setData(buildLineData(computeEMA(closes, settings.indicators.emaSlow)));

  // Volume
  if (settings.indicators.showVolume) {
    const volData: HistogramData<Time>[] = rows.map((r, i) => ({
      time: times[i],
      value: r.v,
      color: r.c >= r.o ? CHART_THEME.bullTinted : CHART_THEME.bearTinted,
    }));
    volSeries?.setData(volData);
  } else {
    volSeries?.setData([]);
  }

  // RSI
  if (settings.indicators.showRSI) {
    rsiSeries?.setData(buildLineData(computeRSI(closes, settings.indicators.rsiPeriod)));
  } else {
    rsiSeries?.setData([]);
  }

  // trade markers — in replay mode filter to trades that have at least started
  const visibleTrades = replay.isActive
    ? trades.value.filter((t) => t.entry_idx <= viewTo)
    : trades.value;
  const m = toMarkers(rows, visibleTrades, viewTo);
  if (markersApi) {
    markersApi.setMarkers(m);
  } else if (candleSeries) {
    markersApi = createSeriesMarkers(candleSeries, m);
  }

  // boxes overlay — always sync bar times so x-coordinates snap to real bars
  if (boxesPrimitive) {
    const barTimes = rows.map((r) => (toUTCTimestamp(r.t) as unknown as number));
    boxesPrimitive.setBarTimes(barTimes);
    boxesPrimitive.setBoxes(boxes.value);
  }

  // Only fit on a real data reload — preserve user pan/zoom during replay.
  if (candlesChanged) {
    chart?.timeScale().fitContent();
  }
}

async function rebuildChart() {
  const range = chart?.timeScale().getVisibleLogicalRange() ?? null;
  initChart();
  if (range) {
    await nextTick();
    chart?.timeScale().setVisibleLogicalRange(range);
  }
}

// ---- chart init/teardown ----

function initChart() {
  if (chart) {
    markersApi = null;
    boxesPrimitive = null;
    chart.remove();
    chart = null;
    candleSeries = null;
    emaFastSeries = null;
    emaSlowSeries = null;
    volSeries = null;
    rsiSeries = null;
  }
  lastCandlesRef = null;  // ensure the first applyData() call triggers a fit
  if (!containerRef.value) return;

  chart = createChart(containerRef.value, {
    layout: { background: { color: CHART_THEME.bg }, textColor: CHART_THEME.text },
    grid: { vertLines: { color: CHART_THEME.border }, horzLines: { color: CHART_THEME.border } },
    timeScale: { borderColor: CHART_THEME.border },
    rightPriceScale: { borderColor: CHART_THEME.border },
    autoSize: true,
  });

  // pane 0: candlesticks
  candleSeries = chart.addSeries(CandlestickSeries, {
    upColor: CHART_THEME.bull,
    downColor: CHART_THEME.bear,
    borderUpColor: CHART_THEME.bull,
    borderDownColor: CHART_THEME.bear,
    wickUpColor: CHART_THEME.bull,
    wickDownColor: CHART_THEME.bear,
  });

  // box overlay primitive (draws behind candles)
  boxesPrimitive = new BoxesPrimitive();
  candleSeries.attachPrimitive(boxesPrimitive);

  // EMA overlays (pane 0)
  emaFastSeries = chart.addSeries(
    LineSeries,
    {
      color: CHART_THEME.emaFast,
      lineWidth: 1,
      title: `EMA${settings.indicators.emaFast}`,
      priceLineVisible: false,
      lastValueVisible: false,
    },
    0,
  );
  emaSlowSeries = chart.addSeries(
    LineSeries,
    {
      color: CHART_THEME.emaSlow,
      lineWidth: 1,
      title: `EMA${settings.indicators.emaSlow}`,
      priceLineVisible: false,
      lastValueVisible: false,
    },
    0,
  );

  // pane 1: volume histogram — only when enabled
  if (settings.indicators.showVolume) {
    volSeries = chart.addSeries(
      HistogramSeries,
      {
        priceFormat: { type: 'volume' },
        priceScaleId: 'vol',
      },
      1,
    );
  }

  // RSI pane — only when enabled; index = 1 if no vol, 2 if vol exists
  if (settings.indicators.showRSI) {
    const rsiPane = settings.indicators.showVolume ? 2 : 1;
    rsiSeries = chart.addSeries(
      LineSeries,
      {
        color: CHART_THEME.rsi,
        lineWidth: 1,
        title: 'RSI',
        priceLineVisible: false,
        lastValueVisible: true,
      },
      rsiPane,
    );
    rsiSeries.createPriceLine({
      price: 70,
      color: CHART_THEME.bearThreshold,
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      axisLabelVisible: true,
      title: '70',
    });
    rsiSeries.createPriceLine({
      price: 30,
      color: CHART_THEME.bullThreshold,
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      axisLabelVisible: true,
      title: '30',
    });
  }

  chart.subscribeCrosshairMove((param: MouseEventParams<Time>) => {
    if (!param.time || !candles.value.length) {
      hoveredCandle.value = null;
      return;
    }
    const ts = param.time as number;
    hoveredCandle.value =
      candles.value.find((c) => (toUTCTimestamp(c.t) as number) === ts) ?? null;
  });

  applyData();
}

onMounted(initChart);

watch([candles, trades, boxes], applyData, { deep: false });
// Visibility toggles → rebuild panes so they actually appear/disappear
watch(
  () => [settings.indicators.showVolume, settings.indicators.showRSI],
  rebuildChart,
);

// Period changes → recompute data + refresh pane titles only (no rebuild)
// (BUG-023: titles are baked at addSeries time and don't update on period change)
watch(
  () => [
    settings.indicators.emaFast,
    settings.indicators.emaSlow,
    settings.indicators.rsiPeriod,
  ],
  () => {
    emaFastSeries?.applyOptions({ title: `EMA${settings.indicators.emaFast}` });
    emaSlowSeries?.applyOptions({ title: `EMA${settings.indicators.emaSlow}` });
    applyData();
  },
);
// replay scrubbing → re-slice
watch(() => replay.currentIdx, applyData);
watch(() => replay.isActive, applyData);

onBeforeUnmount(() => {
  hoveredCandle.value = null;
  markersApi = null;
  boxesPrimitive = null;
  chart?.remove();
  chart = null;
  candleSeries = null;
  emaFastSeries = null;
  emaSlowSeries = null;
  volSeries = null;
  rsiSeries = null;
});
</script>

<style scoped>
/* Responsive chart height: floor of 360px (still useful on mobile),
 * 55% of the viewport at the comfort zone, ceiling of 720px so the
 * chart doesn't dominate on ultrawide displays.
 */
.chart-container {
  width: 100%;
  height: 100%;
  min-height: clamp(360px, 55vh, 720px);
}

.chart-shell {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: clamp(360px, 55vh, 720px);
}

.chart-empty {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--chart-muted);
  font-size: 12px;
  pointer-events: none;
}

.chart-tooltip {
  position: absolute;
  top: 8px;
  left: 8px;
  background: rgba(30, 34, 45, 0.92);
  border: 1px solid #2a2e39;
  border-radius: 4px;
  padding: 6px 10px;
  font-family: monospace;
  font-size: 11px;
  line-height: 1.6;
  pointer-events: none;
  z-index: 10;
  color: #d1d4dc;
  min-width: 140px;
}
.ct-time  { margin-bottom: 2px; }
.ct-date  { color: #787b86; }
.ct-hr    { color: #c3c3c3; }
.ct-lbl   { color: #787b86; margin-right: 4px; }
.ct-bull  { color: #26a69a; }
.ct-bear  { color: #ef5350; }
.ct-row   { display: flex; gap: 10px; }

.chart-warning {
  position: absolute;
  top: 6px;
  right: 8px;
  padding: 2px 6px;
  border-radius: 3px;
  /* 15% alpha background built from the same hex token. */
  background: color-mix(in srgb, var(--chart-ema-fast) 15%, transparent);
  color: var(--chart-ema-fast);
  font-size: 11px;
  pointer-events: none;
}
</style>
