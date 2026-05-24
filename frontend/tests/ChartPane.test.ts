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
  const attachPrimitive = vi.fn();
  const applyOptions = vi.fn();
  const addSeries = vi.fn(() => ({ setData, createPriceLine, attachPrimitive, applyOptions }));
  const createSeriesMarkers = vi.fn(() => ({ setMarkers }));
  const createChart = vi.fn(() => ({
    addSeries,
    remove,
    subscribeCrosshairMove: vi.fn(),
    timeScale: () => ({
      fitContent,
      timeToCoordinate: vi.fn(() => 0),
      getVisibleLogicalRange: vi.fn(() => null),
      setVisibleLogicalRange: vi.fn(),
    }),
  }));
  return { setData, setMarkers, remove, fitContent, addSeries, createSeriesMarkers, createChart, createPriceLine, attachPrimitive, applyOptions };
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
import { useSettingsStore } from '../src/stores/settings';
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
    // candlestick + EMA fast + EMA slow = 3 (volume + RSI off by default)
    expect(mocks.addSeries).toHaveBeenCalledTimes(3);
    expect(wrapper.find('[data-testid="chart-pane"]').exists()).toBe(true);
    wrapper.unmount();
  });

  it('forwards the candles prop to the candlestick series setData', () => {
    mocks.setData.mockClear();

    const wrapper = mountChart(SAMPLE_CANDLES);

    // first setData call is always the candlestick series
    const firstCall = mocks.setData.mock.calls[0][0];
    expect(firstCall).toHaveLength(2);
    const item = firstCall[0];
    // time must be a number (UTCTimestamp in seconds), not a string
    expect(typeof item.time).toBe('number');
    expect(item.time).toBeGreaterThan(1_000_000_000);
    expect(item).toMatchObject({ open: 20000, high: 20020, low: 19990, close: 20010 });
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

  // FIX-17: fitContent must not fire on every replay tick / indicator change —
  // only when the candles array identity itself changes.
  it('calls fitContent only when the candles prop changes, not on indicator edits', async () => {
    mocks.fitContent.mockClear();
    const wrapper = mountChart(SAMPLE_CANDLES);
    const initialFits = mocks.fitContent.mock.calls.length;
    expect(initialFits).toBeGreaterThanOrEqual(1); // initial mount fits

    // Indicator change — should NOT re-fit.
    const settings = useSettingsStore();
    settings.indicators.emaFast = 30;
    await wrapper.vm.$nextTick();
    expect(mocks.fitContent.mock.calls.length).toBe(initialFits);

    // New candles array (e.g. a fresh backtest run) — SHOULD re-fit.
    await wrapper.setProps({
      candles: [
        ...SAMPLE_CANDLES,
        { t: '2025-09-01T10:00:00', o: 20025, h: 20040, l: 20010, c: 20035, v: 1200 },
      ],
    });
    expect(mocks.fitContent.mock.calls.length).toBeGreaterThan(initialFits);
    wrapper.unmount();
  });

  // BUG-023: EMA pane titles are baked in at addSeries time and don't
  // update when the user changes the period in SettingsPanel.
  it('updates EMA series titles when emaFast/emaSlow change', async () => {
    mocks.applyOptions.mockClear();
    const wrapper = mountChart(SAMPLE_CANDLES);
    const settings = useSettingsStore();

    settings.indicators.emaFast = 30;
    settings.indicators.emaSlow = 100;
    await wrapper.vm.$nextTick();

    const titles = mocks.applyOptions.mock.calls.map((c) => c[0]?.title);
    expect(titles).toContain('EMA30');
    expect(titles).toContain('EMA100');
    wrapper.unmount();
  });
});
