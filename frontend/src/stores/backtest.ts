/**
 * Pinia store that drives the master-strategy backtest:
 *  - holds the live progress event for the ProgressBar
 *  - holds the final metrics / trades / candles for the report panels
 *  - exposes run() which kicks off the SSE stream
 */

import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { streamBoxBacktest } from '../services/sse';
import type {
  BoxRect,
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
  const warnings = ref<string[]>([]);

  const candles = ref<Candle[]>([]);
  const trades = ref<ScalingTrade[]>([]);
  const metrics = ref<Metrics | null>(null);
  const elapsedMs = ref<number | null>(null);
  const boxes = ref<BoxRect[]>([]);
  const lastRunSettings = ref<string | null>(null);

  const percent = computed(() => progress.value?.percent ?? 0);
  const hasResults = computed(() => metrics.value !== null);

  async function run() {
    if (isRunning.value) return;
    const settings = useSettingsStore();
    isRunning.value = true;
    error.value = null;
    warnings.value = [];
    progress.value = null;
    metrics.value = null;
    elapsedMs.value = null;
    candles.value = [];
    trades.value = [];
    boxes.value = [];

    const runPayload = {
      params: settings.params,
      data_path: settings.dataPath,
      box_data_path: settings.boxDataPath,
      start: settings.startDate || undefined,
      end: settings.endDate || undefined,
    };
    lastRunSettings.value = JSON.stringify(runPayload);

    try {
      const stream = streamBoxBacktest(runPayload);
      for await (const ev of stream) {
        if (ev.type === 'progress') {
          progress.value = ev.data;
        } else if (ev.type === 'complete') {
          const payload = ev.data as ScalingCompletePayload;
          metrics.value = payload.metrics;
          trades.value = payload.trades;
          candles.value = payload.candles;
          elapsedMs.value = payload.elapsed_ms;
          boxes.value = payload.boxes ?? [];
        } else if (ev.type === 'warning') {
          warnings.value = [...warnings.value, `${ev.data.stage}: ${ev.data.message}`];
        } else if (ev.type === 'error') {
          // Structured errors use `message`; legacy path uses `detail`.
          error.value = ev.data.detail ?? ev.data.message ?? 'Unknown error';
        }
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : String(err);
    } finally {
      isRunning.value = false;
    }
  }

  const isDirty = computed(() => {
    if (!hasResults.value || lastRunSettings.value === null) return false;
    const settings = useSettingsStore();
    const current = JSON.stringify({
      params: settings.params,
      data_path: settings.dataPath,
      box_data_path: settings.boxDataPath,
      start: settings.startDate || undefined,
      end: settings.endDate || undefined,
    });
    return current !== lastRunSettings.value;
  });

  return {
    isRunning,
    progress,
    error,
    warnings,
    candles,
    trades,
    metrics,
    elapsedMs,
    boxes,
    percent,
    hasResults,
    isDirty,
    run,
  };
});
