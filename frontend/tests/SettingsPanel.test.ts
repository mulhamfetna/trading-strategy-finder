/**
 * SettingsPanel component tests — sections render, inputs bind, validation surfaces.
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
    expect(text).toContain('Data');
    expect(text).toContain('Entry distribution');
    expect(text).toContain('Big candle');
    expect(text).toContain('Entry trigger');
    expect(text).toContain('Stop loss');
    expect(text).toContain('Take profit');
    expect(text).toContain('Re-entry');
    expect(text).toContain('Box-rule decisions');
    expect(text).toContain('Indicators');
  });

  it('binds inputs to the settings store (TP target field updates store)', async () => {
    const w = mount(SettingsPanel);
    const settings = useSettingsStore();
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

  it('shows SL order error when hard SL < soft SL', async () => {
    const w = mount(SettingsPanel);
    const settings = useSettingsStore();
    settings.params.sl_soft_points = 300;
    settings.params.sl_hard_points = 150;
    await w.vm.$nextTick();
    expect(w.find('[data-testid="sl-order-error"]').exists()).toBe(true);
    expect(w.text()).toContain('Hard SL must be at least');
  });

  it('shows leg-pullback order error when leg3 <= leg2', async () => {
    const w = mount(SettingsPanel);
    const settings = useSettingsStore();
    settings.params.leg2_pullback_points = 200;
    settings.params.leg3_pullback_points = 100;
    await w.vm.$nextTick();
    expect(w.find('[data-testid="leg-order-error"]').exists()).toBe(true);
    expect(w.text()).toContain('Leg 3 pullback must be deeper');
  });

  it('Box-rule decisions section is always visible', () => {
    const w = mount(SettingsPanel);
    expect(w.text()).toContain('Box-rule decisions');
    expect(w.text()).toContain('Big-Candle vs Box conflict policy');
  });
});
