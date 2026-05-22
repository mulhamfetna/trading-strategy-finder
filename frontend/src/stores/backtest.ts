/**
 * Pinia store that drives the scaling backtest:
 *  - holds the live progress event for the ProgressBar
 *  - holds the final metrics / trades / candles for the report panels
 *  - exposes run() which kicks off the SSE stream
 */

import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { streamScalingBacktest } from '../services/sse';
import type {
  Candle,
  Metrics,
  ScalingCompletePayload,
  ScalingProgress,
  ScalingTrade,
} from '../types';
import { useSettingsStore } from './settings';

export const useBacktestStore = defineStore('backtest', () => {
  const isRunning = ref(false);
  const progress = ref<ScalingProgress | null>(null);
  const error = ref<string | null>(null);

  const candles = ref<Candle[]>([]);
  const trades = ref<ScalingTrade[]>([]);
  const metrics = ref<Metrics | null>(null);
  const elapsedMs = ref<number | null>(null);

  const percent = computed(() => progress.value?.percent ?? 0);
  const hasResults = computed(() => metrics.value !== null);

  async function run() {
    if (isRunning.value) return;
    const settings = useSettingsStore();
    isRunning.value = true;
    error.value = null;
    progress.value = null;
    metrics.value = null;
    elapsedMs.value = null;
    // Keep previous candles/trades visible until new ones arrive on 'complete',
    // OR clear them - we clear so the UI obviously enters the loading state.
    candles.value = [];
    trades.value = [];

    try {
      const stream = streamScalingBacktest({
        params: settings.params,
        data_path: settings.dataPath,
        start: settings.startDate || undefined,
        end: settings.endDate || undefined,
      });
      for await (const ev of stream) {
        if (ev.type === 'progress') {
          progress.value = ev.data;
        } else if (ev.type === 'complete') {
          const payload = ev.data as ScalingCompletePayload;
          metrics.value = payload.metrics;
          trades.value = payload.trades;
          candles.value = payload.candles;
          elapsedMs.value = payload.elapsed_ms;
        } else if (ev.type === 'error') {
          error.value = ev.data.detail;
        }
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : String(err);
    } finally {
      isRunning.value = false;
    }
  }

  return {
    isRunning,
    progress,
    error,
    candles,
    trades,
    metrics,
    elapsedMs,
    percent,
    hasResults,
    run,
  };
});
