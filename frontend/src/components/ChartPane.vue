<template>
  <div ref="containerRef" class="chart-container" data-testid="chart-pane" />
</template>

<script setup lang="ts">
import { onMounted, onBeforeUnmount, watch, ref, toRefs } from 'vue';
import {
  createChart,
  createSeriesMarkers,
  CandlestickSeries,
  type IChartApi,
  type ISeriesApi,
  type ISeriesMarkersPluginApi,
  type CandlestickData,
  type SeriesMarker,
  type Time,
} from 'lightweight-charts';
import type { Candle, ScalingTrade } from '../types';

const props = withDefaults(
  defineProps<{
    candles: Candle[];
    trades?: ScalingTrade[];
  }>(),
  { trades: () => [] },
);

const { candles, trades } = toRefs(props);

const containerRef = ref<HTMLDivElement | null>(null);
let chart: IChartApi | null = null;
let series: ISeriesApi<'Candlestick'> | null = null;
let markersApi: ISeriesMarkersPluginApi<Time> | null = null;

function toLwcData(rows: Candle[]): CandlestickData[] {
  return rows.map((row) => ({
    time: row.t as unknown as Time,
    open: row.o,
    high: row.h,
    low: row.l,
    close: row.c,
  }));
}

function toMarkers(rows: Candle[], tradeRows: ScalingTrade[]): SeriesMarker<Time>[] {
  if (!rows.length || !tradeRows.length) return [];
  const markers: SeriesMarker<Time>[] = [];
  for (const t of tradeRows) {
    const entry = rows[t.entry_idx];
    const exit = rows[t.exit_idx];
    if (entry) {
      markers.push({
        time: entry.t as unknown as Time,
        position: t.direction === 'long' ? 'belowBar' : 'aboveBar',
        color: t.direction === 'long' ? '#00c853' : '#ff5252',
        shape: t.direction === 'long' ? 'arrowUp' : 'arrowDown',
        text: t.direction === 'long' ? 'B' : 'S',
      });
    }
    if (exit) {
      markers.push({
        time: exit.t as unknown as Time,
        position: t.direction === 'long' ? 'aboveBar' : 'belowBar',
        color: t.profit_dollars >= 0 ? '#00c853' : '#ff5252',
        shape: 'square',
        text: `${t.profit_dollars >= 0 ? '+' : ''}${t.profit_points.toFixed(0)}`,
      });
    }
  }
  return markers.sort((a, b) => String(a.time).localeCompare(String(b.time)));
}

function applyData() {
  if (!series) return;
  series.setData(toLwcData(candles.value));
  const m = toMarkers(candles.value, trades.value);
  if (markersApi) {
    markersApi.setMarkers(m);
  } else if (series) {
    markersApi = createSeriesMarkers(series, m);
  }
  chart?.timeScale().fitContent();
}

onMounted(() => {
  if (!containerRef.value) return;
  chart = createChart(containerRef.value, {
    layout: {
      background: { color: '#131722' },
      textColor: '#d1d4dc',
    },
    grid: {
      vertLines: { color: '#363a45' },
      horzLines: { color: '#363a45' },
    },
    timeScale: { borderColor: '#363a45' },
    rightPriceScale: { borderColor: '#363a45' },
    autoSize: true,
  });
  series = chart.addSeries(CandlestickSeries, {
    upColor: '#00c853',
    downColor: '#ff5252',
    borderUpColor: '#00c853',
    borderDownColor: '#ff5252',
    wickUpColor: '#00c853',
    wickDownColor: '#ff5252',
  });
  applyData();
});

watch([candles, trades], applyData, { deep: false });

onBeforeUnmount(() => {
  markersApi = null;
  chart?.remove();
  chart = null;
  series = null;
});
</script>

<style scoped>
.chart-container {
  width: 100%;
  height: 100%;
  min-height: 400px;
}
</style>
