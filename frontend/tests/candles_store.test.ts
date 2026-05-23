/**
 * Tests for the candles Pinia store. Mocks the api service so the
 * test runs without a backend.
 */

import { describe, expect, it, beforeEach, vi } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { useCandlesStore } from '../src/stores/candles';

// Mock the api service module - vi.mock is hoisted.
vi.mock('../src/services/api', () => ({
  fetchCandles: vi.fn(),
  fetchStrategyConfig: vi.fn(),
  runBacktest: vi.fn(),
}));

import { fetchCandles } from '../src/services/api';
const fetchCandlesMock = fetchCandles as unknown as ReturnType<typeof vi.fn>;

describe('useCandlesStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    fetchCandlesMock.mockReset();
  });

  it('starts empty', () => {
    const store = useCandlesStore();
    expect(store.candles).toEqual([]);
    expect(store.loading).toBe(false);
    expect(store.error).toBeNull();
    expect(store.range).toBeNull();
  });

  it('loads candles via the api service', async () => {
    fetchCandlesMock.mockResolvedValueOnce({
      candles: [
        { t: '2025-09-01T09:30:00', o: 100, h: 101, l: 99, c: 100.5, v: 1000 },
      ],
      count: 1,
      range: { start: '2025-09-01', end: '2025-09-30' },
    });

    const store = useCandlesStore();
    await store.load('2025-09-01', '2025-09-30', 'test');

    expect(fetchCandlesMock).toHaveBeenCalledWith('2025-09-01', '2025-09-30', 'test', expect.any(String));
    expect(store.candles).toHaveLength(1);
    expect(store.range).toEqual({ start: '2025-09-01', end: '2025-09-30' });
    expect(store.loading).toBe(false);
    expect(store.error).toBeNull();
  });

  it('records errors and resets candles on failure', async () => {
    fetchCandlesMock.mockRejectedValueOnce(new Error('boom'));

    const store = useCandlesStore();
    await store.load('2025-09-01', '2025-09-30', 'test');

    expect(store.candles).toEqual([]);
    expect(store.error).toBe('boom');
    expect(store.loading).toBe(false);
  });
});
