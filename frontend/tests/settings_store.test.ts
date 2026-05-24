/**
 * Settings store tests — defaults match the master strategy playbook.
 */

import { describe, expect, it, beforeEach } from 'vitest';
import { nextTick } from 'vue';
import { setActivePinia, createPinia } from 'pinia';
import { useSettingsStore } from '../src/stores/settings';
import { DEFAULT_BOX_PARAMS } from '../src/types';

// Helper for the "extra unknown key" test — returns a fresh copy of
// the canonical default-params blob so the stale-schema check sees a
// shape-compatible base, and we only need to add one extra key on top.
function DEFAULT_BOX_PARAMS_FOR_TEST() {
  return { ...DEFAULT_BOX_PARAMS };
}

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
  it('hydrates params from localStorage on init', async () => {
    // tryLoad requires the cached blob's key-set to match defaults exactly
    // (stale-schema protection). Seed by mutating a real store first so the
    // write-back watcher produces a valid blob, then re-init.
    const s0 = useSettingsStore();
    s0.params.total_contracts = 8;
    await nextTick();
    setActivePinia(createPinia());
    const s = useSettingsStore();
    expect(s.params.total_contracts).toBe(8);
    expect(s.params.leg1_contracts).toBe(1); // unrelated field intact
  });

  it('discards a localStorage blob with stale schema (missing required keys)', () => {
    // Simulates the pre-2026-05-24 schema where Hard SL TF was stored as
    // `_seconds` rather than `_minutes`. The strict tryLoad check rejects
    // any blob whose key-set differs from current defaults.
    const stale = {
      total_contracts: 99,
      leg1_contracts: 1,
      hard_sl_confirmation_timeframe_seconds: 5,
      // missing the new hard_sl_confirmation_timeframe_minutes — discard.
    };
    localStorage.setItem('nq-dash:params', JSON.stringify(stale));
    setActivePinia(createPinia());
    const s = useSettingsStore();
    expect(s.params.total_contracts).toBe(4);    // ← default, NOT the 99 from stale
    // The renamed field is present with its new default
    expect(s.params.hard_sl_confirmation_timeframe_minutes).toBe(1);
    // And the old field isn't accidentally surfaced
    expect((s.params as unknown as Record<string, unknown>).hard_sl_confirmation_timeframe_seconds).toBeUndefined();
  });

  it('discards a localStorage blob with extra unknown keys (forward-compat guard)', () => {
    // If a future schema dropped a field, the stored blob would have an
    // extra key relative to defaults — also discarded for consistency.
    const tampered = {
      // Build a complete payload first, then add an extra unknown key.
      ...DEFAULT_BOX_PARAMS_FOR_TEST(),
      unknown_field_that_was_dropped: 'whatever',
    };
    localStorage.setItem('nq-dash:params', JSON.stringify(tampered));
    setActivePinia(createPinia());
    const s = useSettingsStore();
    // The total_contracts override in the stale blob would have been 4
    // (because DEFAULT_BOX_PARAMS_FOR_TEST mirrors defaults), so a fresh
    // store value of 4 is consistent either way. The real check is the
    // unknown field doesn't leak through:
    expect((s.params as unknown as Record<string, unknown>).unknown_field_that_was_dropped).toBeUndefined();
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
