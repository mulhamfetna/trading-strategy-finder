/**
 * Smoke tests for ChartPane.vue.
 *
 * Lightweight Charts is a canvas-heavy library that does not initialize
 * cleanly under happy-dom. We mock the library and assert that our
 * wrapper drives it correctly.
 */

import { describe, expect, it, vi } from 'vitest';
import { createPinia } from 'pinia';

// vi.hoisted lets us define mock spies that are usable inside vi.mock
// (which is itself hoisted to the top of the file).
const mocks = vi.hoisted(() => {
  const setData = vi.fn();
  const setMarkers = vi.fn();
  const remove = vi.fn();
  const fitContent = vi.fn();
  const createPriceLine = vi.fn();
  const addSeries = vi.fn(() => ({ setData, createPriceLine }));
  const createSeriesMarkers = vi.fn(() => ({ setMarkers }));
  const createChart = vi.fn(() => ({
    addSeries,
    remove,
    timeScale: () => ({ fitContent }),
  }));
  return { setData, setMarkers, remove, fitContent, addSeries, createSeriesMarkers, createChart, createPriceLine };
});

vi.mock('lightweight-charts', () => ({
  createChart: mocks.createChart,
  createSeriesMarkers: mocks.createSeriesMarkers,
  CandlestickSeries: { __sentinel: 'CandlestickSeries' },
  LineSeries: { __sentinel: 'LineSeries' },
  HistogramSeries: { __sentinel: 'HistogramSeries' },
  LineStyle: { Dashed: 2, Solid: 0 },
}));

import { mount } from '@vue/test-utils';
import ChartPane from '../src/components/ChartPane.vue';
import type { Candle } from '../src/types';

const SAMPLE_CANDLES: Candle[] = [
  { t: '2025-09-01T09:30:00', o: 20000, h: 20020, l: 19990, c: 20010, v: 1000 },
  { t: '2025-09-01T09:45:00', o: 20010, h: 20030, l: 19995, c: 20025, v: 1100 },
];

function mountChart(candles: Candle[] = []) {
  return mount(ChartPane, {
    global: { plugins: [createPinia()] },
    props: { candles },
  });
}

describe('ChartPane', () => {
  it('creates a chart and all series on mount', () => {
    mocks.createChart.mockClear();
    mocks.addSeries.mockClear();

    const wrapper = mountChart();

    expect(mocks.createChart).toHaveBeenCalledTimes(1);
    // candlestick + EMA fast + EMA slow + volume + RSI = 5
    expect(mocks.addSeries).toHaveBeenCalledTimes(5);
    expect(wrapper.find('[data-testid="chart-pane"]').exists()).toBe(true);
    wrapper.unmount();
  });

  it('forwards the candles prop to the candlestick series setData', () => {
    mocks.setData.mockClear();

    const wrapper = mountChart(SAMPLE_CANDLES);

    // first setData call is always the candlestick series
    const firstCall = mocks.setData.mock.calls[0][0];
    expect(firstCall).toHaveLength(2);
    expect(firstCall[0]).toMatchObject({
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

    const wrapper = mountChart([]);
    const initialCalls = mocks.setData.mock.calls.length;

    await wrapper.setProps({ candles: SAMPLE_CANDLES });

    expect(mocks.setData.mock.calls.length).toBeGreaterThan(initialCalls);
    wrapper.unmount();
  });

  it('removes the chart on unmount', () => {
    mocks.remove.mockClear();

    const wrapper = mountChart();
    wrapper.unmount();

    expect(mocks.remove).toHaveBeenCalledTimes(1);
  });
});
