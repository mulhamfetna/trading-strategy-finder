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

/**
 * Hydrate from localStorage, but discard any blob whose key-set doesn't
 * match the current defaults. Protects against schema drift: when a
 * backend field is renamed (e.g. hard_sl_confirmation_timeframe_seconds
 * → _minutes on 2026-05-24), an old browser cache would otherwise hand
 * the request builder a payload the backend 422s on. Strict
 * symmetric-difference check: both missing and extra keys disqualify
 * the cached blob.
 */
function tryLoad<T extends object>(key: string, defaults: T): T {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return defaults;
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      return defaults;
    }
    const defaultKeys = Object.keys(defaults).sort();
    const parsedKeys  = Object.keys(parsed).sort();
    if (
      defaultKeys.length !== parsedKeys.length ||
      defaultKeys.some((k, i) => k !== parsedKeys[i])
    ) {
      // Schema mismatch — fall back to defaults. The write-back watcher
      // will overwrite the stale entry as soon as the user edits anything.
      return defaults;
    }
    return { ...defaults, ...parsed };
  } catch {
    return defaults;
  }
}

export type EngineMode = 'box' | 'simple';
export interface SimpleParams {
  sl_soft_points: number;
  sl_hard_points: number;
  tp_soft_points: number;
  tp_hard_points: number;
  direction_scope: 'both' | 'long_only' | 'short_only';
  flip_entry_direction: boolean;
}
const DEFAULT_SIMPLE_PARAMS: SimpleParams = {
  sl_soft_points:       100,
  sl_hard_points:       200,
  tp_soft_points:       100,
  tp_hard_points:       150,
  direction_scope:      'both',
  flip_entry_direction: false,
};

const LS_ENGINE = 'nq-dash:engine';
const LS_SIMPLE = 'nq-dash:simple';

export const useSettingsStore = defineStore('settings', () => {
  const params = reactive<BoxParams>(tryLoad(LS_PARAMS, { ...DEFAULT_BOX_PARAMS }));
  const simpleParams = reactive<SimpleParams>(
    tryLoad(LS_SIMPLE, { ...DEFAULT_SIMPLE_PARAMS }),
  );
  const _ls = typeof localStorage !== 'undefined' ? localStorage : null;
  const engineMode = ref<EngineMode>(
    ((_ls?.getItem(LS_ENGINE) as EngineMode) ?? 'simple'),
  );
  watch(engineMode, (v) => _ls?.setItem(LS_ENGINE, v));
  watch(
    () => JSON.stringify(simpleParams),
    (s) => _ls?.setItem(LS_SIMPLE, s),
  );
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
    localStorage.removeItem(LS_SIMPLE);
    localStorage.removeItem(LS_ENGINE);
    Object.assign(params, DEFAULT_BOX_PARAMS);
    Object.assign(simpleParams, DEFAULT_SIMPLE_PARAMS);
    Object.assign(indicators, DEFAULT_INDICATORS);
    engineMode.value = 'simple';
    dataPath.value = DEFAULT_DATA_PATH;
    dataPath1min.value = DEFAULT_DATA_PATH_1MIN;
    boxDataPath.value = DEFAULT_BOX_DATA_PATH;
    startDate.value = '';
    endDate.value = '';
  }

  return {
    params,
    simpleParams,
    engineMode,
    dataPath,
    dataPath1min,
    boxDataPath,
    startDate,
    endDate,
    indicators,
    reset,
  };
});
