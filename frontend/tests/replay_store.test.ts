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
});
