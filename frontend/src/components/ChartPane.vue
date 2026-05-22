<template>
  <div class="chart-shell" data-testid="chart-pane">
    <div ref="containerRef" class="chart-container" />
    <div v-if="!candles.length" class="chart-empty">
      No candles loaded yet.
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onBeforeUnmount, watch, ref, toRefs } from 'vue';
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
  type CandlestickData,
  type LineData,
  type HistogramData,
  type SeriesMarker,
  type Time,
} from 'lightweight-charts';
import type { Candle, ScalingTrade } from '../types';
import { useSettingsStore } from '../stores/settings';
import { useReplayStore } from '../stores/replay';

const props = withDefaults(
  defineProps<{
    candles: Candle[];
    trades?: ScalingTrade[];
  }>(),
  { trades: () => [] },
);

const { candles, trades } = toRefs(props);
const settings = useSettingsStore();
const replay = useReplayStore();

const containerRef = ref<HTMLDivElement | null>(null);

let chart: IChartApi | null = null;
let candleSeries: ISeriesApi<'Candlestick'> | null = null;
let markersApi: ISeriesMarkersPluginApi<Time> | null = null;
let emaFastSeries: ISeriesApi<'Line'> | null = null;
let emaSlowSeries: ISeriesApi<'Line'> | null = null;
let volSeries: ISeriesApi<'Histogram'> | null = null;
let rsiSeries: ISeriesApi<'Line'> | null = null;

// ---- indicator math ----

function computeEMA(prices: number[], period: number): (number | null)[] {
  if (prices.length < period) return prices.map(() => null);
  const k = 2 / (period + 1);
  const out: (number | null)[] = new Array(period - 1).fill(null);
  let ema = prices.slice(0, period).reduce((s, v) => s + v, 0) / period;
  out.push(ema);
  for (let i = period; i < prices.length; i++) {
    ema = prices[i] * k + ema * (1 - k);
    out.push(ema);
  }
  return out;
}

function computeRSI(prices: number[], period: number): (number | null)[] {
  if (prices.length < period + 1) return prices.map(() => null);
  const out: (number | null)[] = new Array(period).fill(null);
  let avgGain = 0;
  let avgLoss = 0;
  for (let i = 1; i <= period; i++) {
    const d = prices[i] - prices[i - 1];
    if (d > 0) avgGain += d; else avgLoss -= d;
  }
  avgGain /= period;
  avgLoss /= period;
  out.push(avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss));
  for (let i = period + 1; i < prices.length; i++) {
    const d = prices[i] - prices[i - 1];
    const gain = d > 0 ? d : 0;
    const loss = d < 0 ? -d : 0;
    avgGain = (avgGain * (period - 1) + gain) / period;
    avgLoss = (avgLoss * (period - 1) + loss) / period;
    out.push(avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss));
  }
  return out;
}

// ---- data converters ----

/**
 * Convert a candle timestamp string to a LWC UTCTimestamp (seconds since epoch).
 *
 * The 4h CSV produces "YYYY-MM-DD HH:MM:SS" (space separator). LWC intraday
 * charts require a numeric UTCTimestamp — passing a string causes the chart
 * to silently render nothing.
 */
function toUTCTimestamp(t: string): Time {
  // Accept both "2025-01-01 18:00:00" and "2025-01-01T18:00:00"
  const iso = t.replace(' ', 'T');
  const ms = new Date(iso + (iso.endsWith('Z') ? '' : 'Z')).getTime();
  return (ms / 1000) as unknown as Time;
}

function toLwcData(rows: Candle[]): CandlestickData<Time>[] {
  return rows.map((row) => ({
    time: toUTCTimestamp(row.t),
    open: row.o,
    high: row.h,
    low: row.l,
    close: row.c,
  }));
}

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
        color: t.direction === 'long' ? '#00c853' : '#ff5252',
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
          color: t.profit_dollars >= 0 ? '#00c853' : '#ff5252',
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

function applyData() {
  if (!candleSeries) return;
  // In replay mode, show only candles up to the current replay index.
  const viewTo = replay.isActive ? replay.currentIdx : candles.value.length - 1;
  const rows = candles.value.slice(0, viewTo + 1);
  const closes = rows.map((r) => r.c);
  const times = rows.map((r) => toUTCTimestamp(r.t));

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
      color: r.c >= r.o ? '#00c85344' : '#ff525244',
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

  chart?.timeScale().fitContent();
}

// ---- chart init/teardown ----

function initChart() {
  if (chart) {
    markersApi = null;
    chart.remove();
    chart = null;
    candleSeries = null;
    emaFastSeries = null;
    emaSlowSeries = null;
    volSeries = null;
    rsiSeries = null;
  }
  if (!containerRef.value) return;

  chart = createChart(containerRef.value, {
    layout: { background: { color: '#131722' }, textColor: '#d1d4dc' },
    grid: { vertLines: { color: '#363a45' }, horzLines: { color: '#363a45' } },
    timeScale: { borderColor: '#363a45' },
    rightPriceScale: { borderColor: '#363a45' },
    autoSize: true,
  });

  // pane 0: candlesticks
  candleSeries = chart.addSeries(CandlestickSeries, {
    upColor: '#00c853',
    downColor: '#ff5252',
    borderUpColor: '#00c853',
    borderDownColor: '#ff5252',
    wickUpColor: '#00c853',
    wickDownColor: '#ff5252',
  });

  // EMA overlays (pane 0)
  emaFastSeries = chart.addSeries(
    LineSeries,
    {
      color: '#f7931a',
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
      color: '#2962ff',
      lineWidth: 1,
      title: `EMA${settings.indicators.emaSlow}`,
      priceLineVisible: false,
      lastValueVisible: false,
    },
    0,
  );

  // pane 1: volume histogram
  volSeries = chart.addSeries(
    HistogramSeries,
    {
      priceFormat: { type: 'volume' },
      priceScaleId: 'vol',
    },
    1,
  );

  // pane 2: RSI
  rsiSeries = chart.addSeries(
    LineSeries,
    {
      color: '#9c27b0',
      lineWidth: 1,
      title: 'RSI',
      priceLineVisible: false,
      lastValueVisible: true,
    },
    2,
  );
  rsiSeries.createPriceLine({
    price: 70,
    color: '#ff525288',
    lineWidth: 1,
    lineStyle: LineStyle.Dashed,
    axisLabelVisible: true,
    title: '70',
  });
  rsiSeries.createPriceLine({
    price: 30,
    color: '#00c85388',
    lineWidth: 1,
    lineStyle: LineStyle.Dashed,
    axisLabelVisible: true,
    title: '30',
  });

  applyData();
}

onMounted(initChart);

watch([candles, trades], applyData, { deep: false });
// period / visibility changes → recompute data only
watch(
  () => [
    settings.indicators.emaFast,
    settings.indicators.emaSlow,
    settings.indicators.rsiPeriod,
    settings.indicators.showVolume,
    settings.indicators.showRSI,
  ],
  applyData,
);
// replay scrubbing → re-slice
watch(() => replay.currentIdx, applyData);
watch(() => replay.isActive, applyData);

onBeforeUnmount(() => {
  markersApi = null;
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
.chart-container {
  width: 100%;
  height: 100%;
  min-height: 520px;
}

.chart-shell {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 520px;
}

.chart-empty {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #787b86;
  font-size: 12px;
  pointer-events: none;
}
</style>
