/**
 * SettingsPanel component tests - the panel renders inputs bound to
 * the settings store; editing an input updates the store.
 */

import { describe, expect, it, beforeEach } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { mount } from '@vue/test-utils';
import SettingsPanel from '../src/components/SettingsPanel.vue';
import { useSettingsStore } from '../src/stores/settings';

describe('SettingsPanel', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('renders sections for every parameter group', () => {
    const w = mount(SettingsPanel);
    const text = w.text();
    expect(text).toContain('Entry distribution');
    expect(text).toContain('Big candle');
    expect(text).toContain('Take profit');
    expect(text).toContain('Stop loss');
    expect(text).toContain('Re-entry');
    expect(text).toContain('Data');
  });

  it('binds inputs to the settings store (TP target field updates store)', async () => {
    const w = mount(SettingsPanel);
    const settings = useSettingsStore();
    // Find a number input whose label contains "Target (pts from avg)"
    const labels = w.findAll('label');
    const tpLabel = labels.find((l) => l.text().includes('Target (pts from avg)'));
    expect(tpLabel).toBeTruthy();
    const input = tpLabel!.find('input[type="number"]');
    await input.setValue('250');
    expect(settings.params.tp_target_points).toBe(250);
  });

  it('Reset button restores defaults', async () => {
    const w = mount(SettingsPanel);
    const settings = useSettingsStore();
    settings.params.total_contracts = 42;

    const buttons = w.findAll('button');
    const resetBtn = buttons.find((b) => b.text().includes('Reset'));
    expect(resetBtn).toBeTruthy();
    await resetBtn!.trigger('click');

    expect(settings.params.total_contracts).toBe(4);
  });
});
