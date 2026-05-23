/**
 * Settings store tests — defaults match the master strategy playbook.
 */

import { describe, expect, it, beforeEach } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { useSettingsStore } from '../src/stores/settings';

describe('useSettingsStore', () => {
  beforeEach(() => {
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
    expect(s.params.weekly_window_days).toBe(7);
    expect(s.params.monthly_window_days).toBe(30);
    expect(s.params.big_candle_resolution).toBe('big_candle_wins');
    expect(s.dataPath).toBe('NQ_4h.csv');
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
});
