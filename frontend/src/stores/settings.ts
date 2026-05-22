/**
 * Pinia store for scaling-strategy settings. Mirrors the backend
 * ScalingParams; the SettingsPanel component binds inputs to these
 * fields directly via reactive refs.
 */

import { defineStore } from 'pinia';
import { reactive, ref } from 'vue';
import { DEFAULT_SCALING_PARAMS, type ScalingParams } from '../types';

export const useSettingsStore = defineStore('settings', () => {
  const params = reactive<ScalingParams>({ ...DEFAULT_SCALING_PARAMS });
  const dataPath = ref<string>('NQ_4h.csv');
  const startDate = ref<string>('');  // empty = whole CSV
  const endDate = ref<string>('');

  function reset() {
    Object.assign(params, DEFAULT_SCALING_PARAMS);
    dataPath.value = 'NQ_4h.csv';
    startDate.value = '';
    endDate.value = '';
  }

  return { params, dataPath, startDate, endDate, reset };
});
