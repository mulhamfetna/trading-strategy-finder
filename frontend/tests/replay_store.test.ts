import { describe, it, expect, beforeEach, vi } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { useReplayStore } from '../src/stores/replay';
import { useBacktestStore } from '../src/stores/backtest';
import type { Candle } from '../src/types';

function makeCandles(n: number): Candle[] {
  return Array.from({ length: n }, (_, i) => ({
    t: `2025-01-${String(i + 1).padStart(2, '0')}T00:00:00`,
    o: 100, h: 110, l: 90, c: 105, v: 1000,
  }));
}

describe('replay store', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    setActivePinia(createPinia());
  });

  it('activates at index 0 and marks isActive', () => {
    const replay = useReplayStore();
    const backtest = useBacktestStore();
    backtest.candles = makeCandles(5);

    replay.activate();

    expect(replay.isActive).toBe(true);
    expect(replay.currentIdx).toBe(0);
    expect(replay.isPlaying).toBe(false);
  });

  it('stepForward advances index', () => {
    const replay = useReplayStore();
    const backtest = useBacktestStore();
    backtest.candles = makeCandles(5);
    replay.activate();

    replay.stepForward();
    expect(replay.currentIdx).toBe(1);
    replay.stepForward();
    expect(replay.currentIdx).toBe(2);
  });

  it('stepBack decrements index and clamps at 0', () => {
    const replay = useReplayStore();
    const backtest = useBacktestStore();
    backtest.candles = makeCandles(5);
    replay.activate();
    replay.seekTo(2);

    replay.stepBack();
    expect(replay.currentIdx).toBe(1);
    replay.stepBack();
    expect(replay.currentIdx).toBe(0);
    replay.stepBack();
    expect(replay.currentIdx).toBe(0); // clamped
  });

  it('play advances index on each tick and stops at end', () => {
    const replay = useReplayStore();
    const backtest = useBacktestStore();
    backtest.candles = makeCandles(3);
    replay.activate();

    replay.play();
    expect(replay.isPlaying).toBe(true);

    vi.advanceTimersByTime(200);
    expect(replay.currentIdx).toBe(1);

    vi.advanceTimersByTime(200);
    expect(replay.currentIdx).toBe(2);

    vi.advanceTimersByTime(200);
    expect(replay.isPlaying).toBe(false); // stopped at end
  });

  it('deactivate clears isActive and stops playback', () => {
    const replay = useReplayStore();
    const backtest = useBacktestStore();
    backtest.candles = makeCandles(5);
    replay.activate();
    replay.play();

    replay.deactivate();

    expect(replay.isActive).toBe(false);
    expect(replay.isPlaying).toBe(false);
  });

  it('percent reflects position in the dataset', () => {
    const replay = useReplayStore();
    const backtest = useBacktestStore();
    backtest.candles = makeCandles(5);
    replay.activate();
    replay.seekTo(4);

    expect(replay.percent).toBe(100);
  });

  // BUG-020: clicking "Run Backtest" while replay is active clears
  // `backtest.candles`. Replay must deactivate so the scrubber's :max
  // doesn't go to -1 and currentCandle doesn't go undefined.
  it('deactivates automatically when backtest candles are cleared', async () => {
    const replay = useReplayStore();
    const backtest = useBacktestStore();
    backtest.candles = makeCandles(5);
    replay.activate();
    replay.seekTo(3);
    expect(replay.isActive).toBe(true);

    backtest.candles = [];
    await Promise.resolve();

    expect(replay.isActive).toBe(false);
    expect(replay.currentIdx).toBe(0);
  });

  it('clamps currentIdx when backtest candles shrink below it', async () => {
    const replay = useReplayStore();
    const backtest = useBacktestStore();
    backtest.candles = makeCandles(10);
    replay.activate();
    replay.seekTo(8);

    backtest.candles = makeCandles(4);
    await Promise.resolve();

    expect(replay.currentIdx).toBe(3); // newTotal - 1
    expect(replay.isActive).toBe(true);
  });

  // FIX-16: unrealised P&L during an open trade
  it('includes mark-to-market PnL for an open long while in replay', () => {
    const replay = useReplayStore();
    const backtest = useBacktestStore();
    // 5 candles, closes climb from 100 to 140
    backtest.candles = [
      { t: '2025-01-01T00:00:00', o: 100, h: 105, l:  95, c: 100, v: 1 },
      { t: '2025-01-02T00:00:00', o: 100, h: 115, l:  95, c: 110, v: 1 },
      { t: '2025-01-03T00:00:00', o: 110, h: 125, l: 105, c: 120, v: 1 },
      { t: '2025-01-04T00:00:00', o: 120, h: 135, l: 115, c: 130, v: 1 },
      { t: '2025-01-05T00:00:00', o: 130, h: 145, l: 125, c: 140, v: 1 },
    ];
    backtest.trades = [
      {
        entry_idx: 0,
        exit_idx: 4,
        direction: 'long',
        entry_signal_price: 100,
        exit_close: 140,
        avg_entry_price: 100,
        exit_price: 140,
        contracts: 1,
        profit_points: 40,
        profit_dollars: 80,  // 40 pts × 1 contract × $2/pt
        exit_reason: 'TAKE PROFIT',
        legs: [],
      },
    ];
    replay.activate();
    // Step into the middle of the trade.
    replay.seekTo(2);
    // close=120, entry=100, dir=+1, contracts=1, point_value=2 -> +40
    expect(replay.unrealisedPnl).toBe(40);
    // No trade closed yet -> realised=0.
    expect(replay.realisedPnl).toBe(0);
    expect(replay.runningPnl).toBe(40);
  });

  it('negates unrealised PnL for an open short', () => {
    const replay = useReplayStore();
    const backtest = useBacktestStore();
    backtest.candles = [
      { t: '2025-01-01T00:00:00', o: 100, h: 105, l:  95, c: 100, v: 1 },
      { t: '2025-01-02T00:00:00', o: 100, h: 115, l:  95, c: 110, v: 1 },
      { t: '2025-01-03T00:00:00', o: 110, h: 125, l: 105, c: 120, v: 1 },
    ];
    backtest.trades = [
      {
        entry_idx: 0,
        exit_idx: 2,
        direction: 'short',
        entry_signal_price: 100,
        exit_close: 120,
        avg_entry_price: 100,
        exit_price: 120,
        contracts: 1,
        profit_points: -20,
        profit_dollars: -40,
        exit_reason: 'STOP',
        legs: [],
      },
    ];
    replay.activate();
    replay.seekTo(1);
    // close=110, entry=100, dir=-1 -> -20
    expect(replay.unrealisedPnl).toBe(-20);
  });

  it('drops unrealised PnL once the trade closes', () => {
    const replay = useReplayStore();
    const backtest = useBacktestStore();
    backtest.candles = [
      { t: '2025-01-01T00:00:00', o: 100, h: 105, l:  95, c: 100, v: 1 },
      { t: '2025-01-02T00:00:00', o: 100, h: 115, l:  95, c: 110, v: 1 },
      { t: '2025-01-03T00:00:00', o: 110, h: 125, l: 105, c: 120, v: 1 },
    ];
    backtest.trades = [
      {
        entry_idx: 0,
        exit_idx: 1,
        direction: 'long',
        entry_signal_price: 100,
        exit_close: 110,
        avg_entry_price: 100,
        exit_price: 110,
        contracts: 1,
        profit_points: 10,
        profit_dollars: 20,
        exit_reason: 'TAKE PROFIT',
        legs: [],
      },
    ];
    replay.activate();
    replay.seekTo(2);  // past the exit
    expect(replay.unrealisedPnl).toBe(0);
    expect(replay.realisedPnl).toBe(20);
    expect(replay.runningPnl).toBe(20);
  });
});
