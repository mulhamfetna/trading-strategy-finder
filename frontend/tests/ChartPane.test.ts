/**
 * Smoke tests for ChartPane.vue.
 *
 * Lightweight Charts is a canvas-heavy library that does not initialize
 * cleanly under happy-dom. We mock the library and assert that our
 * wrapper drives it correctly.
 */

import { describe, expect, it, vi } from 'vitest';

// vi.hoisted lets us define mock spies that are usable inside vi.mock
// (which is itself hoisted to the top of the file).
const mocks = vi.hoisted(() => {
  const setData = vi.fn();
  const remove = vi.fn();
  const fitContent = vi.fn();
  const addSeries = vi.fn(() => ({ setData }));
  const createChart = vi.fn(() => ({
    addSeries,
    remove,
    timeScale: () => ({ fitContent }),
  }));
  return { setData, remove, fitContent, addSeries, createChart };
});

vi.mock('lightweight-charts', () => ({
  createChart: mocks.createChart,
  CandlestickSeries: { __sentinel: 'CandlestickSeries' },
}));

import { mount } from '@vue/test-utils';
import ChartPane from '../src/components/ChartPane.vue';
import type { Candle } from '../src/types';

const SAMPLE_CANDLES: Candle[] = [
  { t: '2025-09-01T09:30:00', o: 20000, h: 20020, l: 19990, c: 20010, v: 1000 },
  { t: '2025-09-01T09:45:00', o: 20010, h: 20030, l: 19995, c: 20025, v: 1100 },
];

describe('ChartPane', () => {
  it('creates a chart and candlestick series on mount', () => {
    mocks.createChart.mockClear();
    mocks.addSeries.mockClear();

    const wrapper = mount(ChartPane, { props: { candles: [] } });

    expect(mocks.createChart).toHaveBeenCalledTimes(1);
    expect(mocks.addSeries).toHaveBeenCalledTimes(1);
    expect(wrapper.find('[data-testid="chart-pane"]').exists()).toBe(true);
    wrapper.unmount();
  });

  it('forwards the candles prop to series.setData', () => {
    mocks.setData.mockClear();

    const wrapper = mount(ChartPane, { props: { candles: SAMPLE_CANDLES } });

    expect(mocks.setData).toHaveBeenCalled();
    const lastCall = mocks.setData.mock.calls[mocks.setData.mock.calls.length - 1][0];
    expect(lastCall).toHaveLength(2);
    expect(lastCall[0]).toMatchObject({
      time: '2025-09-01T09:30:00',
      open: 20000,
      high: 20020,
      low: 19990,
      close: 20010,
    });
    wrapper.unmount();
  });

  it('calls setData again when the candles prop changes', async () => {
    mocks.setData.mockClear();

    const wrapper = mount(ChartPane, { props: { candles: [] } });
    const initialCalls = mocks.setData.mock.calls.length;

    await wrapper.setProps({ candles: SAMPLE_CANDLES });

    expect(mocks.setData.mock.calls.length).toBeGreaterThan(initialCalls);
    wrapper.unmount();
  });

  it('removes the chart on unmount', () => {
    mocks.remove.mockClear();

    const wrapper = mount(ChartPane, { props: { candles: [] } });
    wrapper.unmount();

    expect(mocks.remove).toHaveBeenCalledTimes(1);
  });
});
