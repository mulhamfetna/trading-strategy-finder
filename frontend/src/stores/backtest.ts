/**
 * Pinia store that drives the master-strategy backtest:
 *  - holds the live progress event for the ProgressBar
 *  - holds the final metrics / trades / candles for the report panels
 *  - exposes run() which kicks off the SSE stream
 */

import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { streamBoxBacktest } from '../services/sse';
import { runSimpleBacktest } from '../services/simple';
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
    if (settings.engineMode === 'simple') {
      await _runSimple(settings);
      return;
    }
    await _runBox(settings);
  }

  async function _runBox(settings: ReturnType<typeof useSettingsStore>) {
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
      data_path_1min: settings.dataPath1min,
      box_data_path: settings.boxDataPath,
      start: settings.startDate || undefined,
      end: settings.endDate || undefined,
    };
    lastRunSettings.value = JSON.stringify({ engine: 'box', ...runPayload });

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
          error.value = ev.data.detail ?? ev.data.message ?? 'Unknown error';
        }
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : String(err);
    } finally {
      isRunning.value = false;
    }
  }

  async function _runSimple(settings: ReturnType<typeof useSettingsStore>) {
    isRunning.value = true;
    error.value = null;
    warnings.value = [];
    progress.value = null;
    metrics.value = null;
    elapsedMs.value = null;
    candles.value = [];
    trades.value = [];
    boxes.value = [];   // simple engine has no box rects

    const runPayload = {
      sl_soft_points:  settings.simpleParams.sl_soft_points,
      sl_hard_points:  settings.simpleParams.sl_hard_points,
      tp_points:       settings.simpleParams.tp_points,
      direction_scope: settings.simpleParams.direction_scope,
      data_path:       settings.dataPath,
      data_path_1min:  settings.dataPath1min,
      box_data_path:   settings.boxDataPath,
      start:           settings.startDate || null,
      end:             settings.endDate   || null,
    };
    lastRunSettings.value = JSON.stringify({ engine: 'simple', ...runPayload });

    try {
      const res = await runSimpleBacktest(runPayload);
      metrics.value   = res.metrics;
      trades.value    = res.trades;
      candles.value   = res.candles;
      elapsedMs.value = res.elapsed_ms;
    } catch (err) {
      error.value = err instanceof Error ? err.message : String(err);
    } finally {
      isRunning.value = false;
    }
  }

  const isDirty = computed(() => {
    if (!hasResults.value || lastRunSettings.value === null) return false;
    const settings = useSettingsStore();
    const current = settings.engineMode === 'simple'
      ? JSON.stringify({
          engine: 'simple',
          sl_soft_points:  settings.simpleParams.sl_soft_points,
          sl_hard_points:  settings.simpleParams.sl_hard_points,
          tp_points:       settings.simpleParams.tp_points,
          direction_scope: settings.simpleParams.direction_scope,
          data_path:       settings.dataPath,
          data_path_1min:  settings.dataPath1min,
          box_data_path:   settings.boxDataPath,
          start:           settings.startDate || null,
          end:             settings.endDate   || null,
        })
      : JSON.stringify({
          engine: 'box',
          params: settings.params,
          data_path: settings.dataPath,
          data_path_1min: settings.dataPath1min,
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
