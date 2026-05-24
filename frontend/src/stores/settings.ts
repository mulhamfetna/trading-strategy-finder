import { defineStore } from 'pinia';
import { reactive, ref, watch } from 'vue';
import {
  DEFAULT_BOX_DATA_PATH,
  DEFAULT_BOX_PARAMS,
  DEFAULT_DATA_PATH,
  DEFAULT_DATA_PATH_1MIN,
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

const LS_PARAMS = 'nq-dash:params';
const LS_INDICATORS = 'nq-dash:indicators';

function tryLoad<T extends object>(key: string, defaults: T): T {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return defaults;
    return { ...defaults, ...JSON.parse(raw) };
  } catch {
    return defaults;
  }
}

export const useSettingsStore = defineStore('settings', () => {
  const params = reactive<BoxParams>(tryLoad(LS_PARAMS, { ...DEFAULT_BOX_PARAMS }));
  const dataPath = ref<string>(DEFAULT_DATA_PATH);
  const dataPath1min = ref<string>(DEFAULT_DATA_PATH_1MIN);
  const boxDataPath = ref<string>(DEFAULT_BOX_DATA_PATH);
  const startDate = ref<string>('');
  const endDate = ref<string>('');
  const indicators = reactive<IndicatorSettings>(
    tryLoad(LS_INDICATORS, { ...DEFAULT_INDICATORS }),
  );

  // Write-back on any deep change
  watch(
    () => [JSON.stringify(params), JSON.stringify(indicators)],
    ([p, i]) => {
      localStorage.setItem(LS_PARAMS, p);
      localStorage.setItem(LS_INDICATORS, i);
    },
  );

  function reset() {
    localStorage.removeItem(LS_PARAMS);
    localStorage.removeItem(LS_INDICATORS);
    Object.assign(params, DEFAULT_BOX_PARAMS);
    Object.assign(indicators, DEFAULT_INDICATORS);
    dataPath.value = DEFAULT_DATA_PATH;
    dataPath1min.value = DEFAULT_DATA_PATH_1MIN;
    boxDataPath.value = DEFAULT_BOX_DATA_PATH;
    startDate.value = '';
    endDate.value = '';
  }

  return {
    params,
    dataPath,
    dataPath1min,
    boxDataPath,
    startDate,
    endDate,
    indicators,
    reset,
  };
});
