/**
 * App.vue smoke test — single master strategy, single header label.
 *
 * Lightweight Charts and SSE plumbing are mocked.
 */

import { describe, expect, it, vi, beforeEach } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';

vi.mock('lightweight-charts', () => ({
  createChart: vi.fn(() => ({
    addSeries: vi.fn(() => ({
      setData: vi.fn(),
      createPriceLine: vi.fn(),
      attachPrimitive: vi.fn(),
      applyOptions: vi.fn(),
    })),
    remove: vi.fn(),
    timeScale: () => ({ fitContent: vi.fn(), timeToCoordinate: vi.fn(() => 0) }),
  })),
  createSeriesMarkers: vi.fn(() => ({ setMarkers: vi.fn() })),
  CandlestickSeries: {}, LineSeries: {}, HistogramSeries: {},
  LineStyle: { Dashed: 2, Solid: 0 },
}));

import { mount } from '@vue/test-utils';
import App from '../src/App.vue';

describe('App.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('renders the master strategy header', () => {
    const w = mount(App);
    expect(w.get('[data-testid="app-title"]').text()).toContain('Master Strategy');
    w.unmount();
  });
});
