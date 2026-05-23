/**
 * Pinia store for OHLCV candles. Loads from the FastAPI backend
 * /api/candles endpoint and exposes status + data to components.
 */

import { defineStore } from 'pinia';
import { ref } from 'vue';
import type { Candle } from '../types';
import { fetchCandles } from '../services/api';
import { useSettingsStore } from './settings';

export const useCandlesStore = defineStore('candles', () => {
  const candles = ref<Candle[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const range = ref<{ start: string; end: string } | null>(null);

  async function load(
    start: string,
    end: string,
    dataset: 'train' | 'test',
  ): Promise<void> {
    loading.value = true;
    error.value = null;
    const settings = useSettingsStore();
    try {
      const resp = await fetchCandles(start, end, dataset, settings.dataPath);
      candles.value = resp.candles;
      range.value = resp.range;
    } catch (err) {
      error.value = err instanceof Error ? err.message : String(err);
      candles.value = [];
    } finally {
      loading.value = false;
    }
  }

  return { candles, loading, error, range, load };
});
