<template>
  <div ref="containerRef" class="chart-container" data-testid="chart-pane" />
</template>

<script setup lang="ts">
import { onMounted, onBeforeUnmount, watch, ref, toRefs } from 'vue';
import {
  createChart,
  CandlestickSeries,
  type IChartApi,
  type ISeriesApi,
  type CandlestickData,
  type Time,
} from 'lightweight-charts';
import type { Candle } from '../types';

const props = defineProps<{
  candles: Candle[];
}>();

const { candles } = toRefs(props);

const containerRef = ref<HTMLDivElement | null>(null);
let chart: IChartApi | null = null;
let series: ISeriesApi<'Candlestick'> | null = null;

function toLwcData(rows: Candle[]): CandlestickData[] {
  return rows.map((row) => ({
    time: row.t as unknown as Time, // Lightweight Charts accepts ISO strings here
    open: row.o,
    high: row.h,
    low: row.l,
    close: row.c,
  }));
}

function applyData() {
  if (!series) return;
  series.setData(toLwcData(candles.value));
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

watch(candles, applyData, { deep: false });

onBeforeUnmount(() => {
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
