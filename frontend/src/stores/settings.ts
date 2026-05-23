import { defineStore } from 'pinia';
import { reactive, ref } from 'vue';
import {
  DEFAULT_BOX_DATA_PATHS,
  DEFAULT_BOX_PARAMS,
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
  showVolume: true,
  showRSI: true,
  rsiPeriod: 14,
};

export const useSettingsStore = defineStore('settings', () => {
  const params = reactive<BoxParams>({ ...DEFAULT_BOX_PARAMS });
  const dataPath = ref<string>('NQ_4h.csv');
  const weekDataPath = ref<string>(DEFAULT_BOX_DATA_PATHS.week_data_path);
  const monthDataPath = ref<string>(DEFAULT_BOX_DATA_PATHS.month_data_path);
  const startDate = ref<string>('');
  const endDate = ref<string>('');
  const indicators = reactive<IndicatorSettings>({ ...DEFAULT_INDICATORS });

  function reset() {
    Object.assign(params, DEFAULT_BOX_PARAMS);
    Object.assign(indicators, DEFAULT_INDICATORS);
    dataPath.value = 'NQ_4h.csv';
    weekDataPath.value = DEFAULT_BOX_DATA_PATHS.week_data_path;
    monthDataPath.value = DEFAULT_BOX_DATA_PATHS.month_data_path;
    startDate.value = '';
    endDate.value = '';
  }

  return {
    params,
    dataPath,
    weekDataPath,
    monthDataPath,
    startDate,
    endDate,
    indicators,
    reset,
  };
});
