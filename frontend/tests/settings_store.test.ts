/**
 * Settings store tests — defaults match the master strategy playbook.
 */

import { describe, expect, it, beforeEach } from 'vitest';
import { nextTick } from 'vue';
import { setActivePinia, createPinia } from 'pinia';
import { useSettingsStore } from '../src/stores/settings';

describe('useSettingsStore', () => {
  beforeEach(() => {
    localStorage.clear();
    setActivePinia(createPinia());
  });

  it('defaults match the master strategy playbook', () => {
    const s = useSettingsStore();
    expect(s.params.total_contracts).toBe(4);
    expect(s.params.leg1_contracts).toBe(1);
    expect(s.params.leg2_contracts).toBe(1);
    expect(s.params.leg3_contracts).toBe(2);
    expect(s.params.leg2_pullback_points).toBe(100);
    expect(s.params.leg3_pullback_points).toBe(150);
    expect(s.params.big_candle_threshold_points).toBe(400);
    expect(s.params.tp_target_points).toBe(150);
    expect(s.params.tp_watch_threshold_points).toBe(50);
    expect(s.params.point_value).toBe(2);
    expect(s.params.box_tick_threshold).toBe(0.75);
    expect(s.params.big_candle_resolution).toBe('big_candle_wins');
    expect(s.dataPath).toBe('NQ_4h.csv');
    expect(s.dataPath1min).toBe('NQ_1m.csv');
    expect(s.boxDataPath).toBe('NQ_full_data.csv');
  });

  it('default indicators: volume and RSI off', () => {
    const s = useSettingsStore();
    expect(s.indicators.showVolume).toBe(false);
    expect(s.indicators.showRSI).toBe(false);
    expect(s.indicators.emaFast).toBe(20);
    expect(s.indicators.emaSlow).toBe(50);
    expect(s.indicators.rsiPeriod).toBe(14);
  });

  it('reset() restores defaults after edits', () => {
    const s = useSettingsStore();
    s.params.total_contracts = 99;
    s.dataPath = 'other.csv';
    s.startDate = '2025-01-01';

    s.reset();

    expect(s.params.total_contracts).toBe(4);
    expect(s.dataPath).toBe('NQ_4h.csv');
    expect(s.startDate).toBe('');
  });

  // localStorage persistence
  it('hydrates params from localStorage on init', () => {
    localStorage.setItem('nq-dash:params', JSON.stringify({ total_contracts: 8 }));
    setActivePinia(createPinia());
    const s = useSettingsStore();
    expect(s.params.total_contracts).toBe(8);
    expect(s.params.leg1_contracts).toBe(1); // unrelated field intact
  });

  it('saves params to localStorage when a param changes', async () => {
    const s = useSettingsStore();
    s.params.total_contracts = 9;
    await nextTick();
    const saved = JSON.parse(localStorage.getItem('nq-dash:params')!);
    expect(saved.total_contracts).toBe(9);
  });

  it('saves indicators to localStorage when a flag changes', async () => {
    const s = useSettingsStore();
    s.indicators.showVolume = true;
    await nextTick();
    const saved = JSON.parse(localStorage.getItem('nq-dash:indicators')!);
    expect(saved.showVolume).toBe(true);
  });

  it('reset() clears localStorage keys and restores defaults', async () => {
    const s = useSettingsStore();
    s.params.total_contracts = 99;
    await nextTick();
    expect(localStorage.getItem('nq-dash:params')).not.toBeNull();

    s.reset();
    expect(localStorage.getItem('nq-dash:params')).toBeNull();
    expect(localStorage.getItem('nq-dash:indicators')).toBeNull();
    expect(s.params.total_contracts).toBe(4);
    expect(s.indicators.showVolume).toBe(false);
  });
});
