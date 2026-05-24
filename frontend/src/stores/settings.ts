import { defineStore } from 'pinia';
import { reactive, ref } from 'vue';
import {
  DEFAULT_BOX_DATA_PATH,
  DEFAULT_BOX_PARAMS,
  DEFAULT_DATA_PATH,
  type BoxParams,
} from '../types';

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
  showVolume: false,
  showRSI: false,
  rsiPeriod: 14,
};

export const useSettingsStore = defineStore('settings', () => {
  const params = reactive<BoxParams>({ ...DEFAULT_BOX_PARAMS });
  const dataPath = ref<string>(DEFAULT_DATA_PATH);
  const boxDataPath = ref<string>(DEFAULT_BOX_DATA_PATH);
  const startDate = ref<string>('');
  const endDate = ref<string>('');
  const indicators = reactive<IndicatorSettings>({ ...DEFAULT_INDICATORS });

  function reset() {
    Object.assign(params, DEFAULT_BOX_PARAMS);
    Object.assign(indicators, DEFAULT_INDICATORS);
    dataPath.value = DEFAULT_DATA_PATH;
    boxDataPath.value = DEFAULT_BOX_DATA_PATH;
    startDate.value = '';
    endDate.value = '';
  }

  return {
    params,
    dataPath,
    boxDataPath,
    startDate,
    endDate,
    indicators,
    reset,
  };
});
