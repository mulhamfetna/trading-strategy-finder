/**
 * Backtest store tests - mock streamScalingBacktest and verify the
 * store consumes progress/complete/error events into reactive state.
 */

import { describe, expect, it, beforeEach, vi } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';

// Hoisted mock for the SSE service. The store imports
// streamScalingBacktest from '../services/sse'; tests inject a
// generator that yields whatever events we want.
const mocks = vi.hoisted(() => {
  const eventQueue: Array<{ type: string; data: unknown }> = [];
  async function* mockStream() {
    for (const ev of eventQueue) {
      // Yield asynchronously so the store sees one event at a time
      // (matches the real SSE behavior).
      await Promise.resolve();
      yield ev;
    }
  }
  return { eventQueue, mockStream };
});

vi.mock('../src/services/sse', () => ({
  streamScalingBacktest: () => mocks.mockStream(),
}));

import { useBacktestStore } from '../src/stores/backtest';

describe('useBacktestStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    mocks.eventQueue.length = 0;
  });

  it('starts in an idle state', () => {
    const s = useBacktestStore();
    expect(s.isRunning).toBe(false);
    expect(s.progress).toBeNull();
    expect(s.metrics).toBeNull();
    expect(s.trades).toEqual([]);
    expect(s.candles).toEqual([]);
    expect(s.error).toBeNull();
  });

  it('updates progress as events stream in', async () => {
    mocks.eventQueue.push(
      {
        type: 'progress',
        data: {
          current_idx: 100, total: 200, percent: 50, phase: 'running',
          trades_so_far: 3, pnl_so_far: 150, win_rate_so_far: 66.7,
          current_position: 'long', current_legs_filled: 1,
        },
      },
      {
        type: 'complete',
        data: {
          metrics: {
            total_profit: 1234.5, total_trades: 10, win_rate: 70,
            profit_factor: 2.5, sharpe_ratio: 1.1, max_drawdown: 100,
            avg_profit: 200, avg_loss: -75,
          },
          trades: [
            {
              entry_idx: 1, exit_idx: 3, direction: 'long',
              avg_entry_price: 20000, exit_price: 20150,
              contracts: 4, profit_points: 150, profit_dollars: 1200,
              exit_reason: 'TAKE PROFIT', legs: [],
            },
          ],
          candles: [
            { t: '2025-01-01T00:00:00', o: 20000, h: 20020, l: 19990, c: 20010, v: 1000 },
          ],
          elapsed_ms: 321,
        },
      },
    );

    const s = useBacktestStore();
    await s.run();

    expect(s.isRunning).toBe(false);
    expect(s.progress?.percent).toBe(50);
    expect(s.metrics?.total_profit).toBe(1234.5);
    expect(s.trades).toHaveLength(1);
    expect(s.candles).toHaveLength(1);
    expect(s.elapsedMs).toBe(321);
    expect(s.error).toBeNull();
    expect(s.hasResults).toBe(true);
  });

  it('captures error events into store.error', async () => {
    mocks.eventQueue.push({ type: 'error', data: { detail: 'data not found' } });

    const s = useBacktestStore();
    await s.run();

    expect(s.error).toBe('data not found');
    expect(s.isRunning).toBe(false);
  });
});
