/**
 * MetricsCards regression tests.
 *
 * BUG-011 regressed: PF / Sharpe were rendered as "0.00" when the
 * backend emitted 0 for "undefined". The backend now emits `null`; the
 * component must render "N/A" for null values.
 */

import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';
import MetricsCards from '../src/components/MetricsCards.vue';
import type { Metrics } from '../src/types';

function metricsFixture(overrides: Partial<Metrics> = {}): Metrics {
  return {
    total_profit: 0,
    profit_factor: null,
    win_rate: 0,
    sharpe_ratio: null,
    max_drawdown: 0,
    total_trades: 0,
    ...overrides,
  };
}

describe('MetricsCards', () => {
  it('renders the empty-state placeholder when metrics are null', () => {
    const w = mount(MetricsCards, { props: { metrics: null } });
    expect(w.get('[data-testid="metrics-cards-placeholder"]')).toBeTruthy();
    expect(w.text()).toContain('No report yet');
  });

  it('renders N/A for profit_factor when the backend emits null (BUG-011)', () => {
    const w = mount(MetricsCards, {
      props: { metrics: metricsFixture({ total_trades: 5, profit_factor: null }) },
    });
    expect(w.text()).toContain('Profit Factor');
    expect(w.text()).toContain('N/A');
  });

  it('renders N/A for sharpe_ratio when the backend emits null (BUG-011)', () => {
    const w = mount(MetricsCards, {
      props: { metrics: metricsFixture({ total_trades: 1, sharpe_ratio: null }) },
    });
    // For a 1-trade run, Sharpe is undefined.
    expect(w.text()).toContain('Sharpe');
    expect(w.text()).toContain('N/A');
  });

  it('renders numeric PF when defined', () => {
    const w = mount(MetricsCards, {
      props: { metrics: metricsFixture({ total_trades: 10, profit_factor: 1.75 }) },
    });
    expect(w.text()).toContain('1.75');
  });

  it('renders numeric Sharpe when defined', () => {
    const w = mount(MetricsCards, {
      props: { metrics: metricsFixture({ total_trades: 10, sharpe_ratio: 0.42 }) },
    });
    expect(w.text()).toContain('0.42');
  });

  // BUG-026: Max DD sign/format. Backend returns a non-negative magnitude.
  it('renders Max DD as a negative dollar value when nonzero', () => {
    const w = mount(MetricsCards, {
      props: { metrics: metricsFixture({ total_trades: 5, max_drawdown: 500 }) },
    });
    expect(w.text()).toContain('-$500.00');
  });

  it('renders Max DD as unsigned $0.00 when drawdown is zero (no -$0.00)', () => {
    const w = mount(MetricsCards, {
      props: { metrics: metricsFixture({ total_trades: 5, max_drawdown: 0 }) },
    });
    expect(w.text()).toContain('$0.00');
    expect(w.text()).not.toContain('-$0.00');
    expect(w.text()).not.toContain('+$0.00');
  });

  // BUG-005 family: zero must not inherit a sign or red/green color.
  it('renders Net Profit as unsigned $0.00 at exactly zero', () => {
    const w = mount(MetricsCards, {
      props: { metrics: metricsFixture({ total_trades: 5, total_profit: 0 }) },
    });
    expect(w.text()).toContain('$0.00');
    expect(w.text()).not.toContain('+$0.00');
    expect(w.text()).not.toContain('-$0.00');
  });

  it('renders Net Profit with leading + when positive', () => {
    const w = mount(MetricsCards, {
      props: { metrics: metricsFixture({ total_trades: 5, total_profit: 123.45 }) },
    });
    expect(w.text()).toContain('+$123.45');
  });

  it('renders Net Profit with leading - when negative', () => {
    const w = mount(MetricsCards, {
      props: { metrics: metricsFixture({ total_trades: 5, total_profit: -50 }) },
    });
    expect(w.text()).toContain('-$50.00');
  });
});
