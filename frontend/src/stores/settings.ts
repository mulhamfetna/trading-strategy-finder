import { defineStore } from 'pinia';
import { reactive, ref } from 'vue';
import { DEFAULT_SCALING_PARAMS, type ScalingParams } from '../types';

export interface IndicatorSettings {
  emaFast: number;
  emaSlow: number;
  showVolume: boolean;
  showRSI: boolean;
  rsiPeriod: number;
}

const DEFAULT_INDICATORS: IndicatorSettings = {
  emaFast: 20,
  emaSlow: 50,
  showVolume: true,
  showRSI: true,
  rsiPeriod: 14,
};

export const useSettingsStore = defineStore('settings', () => {
  const params = reactive<ScalingParams>({ ...DEFAULT_SCALING_PARAMS });
  const dataPath = ref<string>('NQ_4h.csv');
  const startDate = ref<string>('');
  const endDate = ref<string>('');
  const indicators = reactive<IndicatorSettings>({ ...DEFAULT_INDICATORS });

  function reset() {
    Object.assign(params, DEFAULT_SCALING_PARAMS);
    Object.assign(indicators, DEFAULT_INDICATORS);
    dataPath.value = 'NQ_4h.csv';
    startDate.value = '';
    endDate.value = '';
  }

  return { params, dataPath, startDate, endDate, indicators, reset };
});
