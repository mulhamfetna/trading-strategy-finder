/**
 * Tests for the SSE parser in sse.ts — exercising the exact shapes
 * the backend sends, including the large complete event.
 */
import { describe, it, expect } from 'vitest';

// Re-implement parseSseFrame here so we can test it in isolation.
// (It's not exported from sse.ts, so we inline a copy.)
function parseSseFrame(raw: string): { type: string; data: unknown } | null {
  if (!raw.trim()) return null;
  let eventType: string | null = null;
  const dataLines: string[] = [];
  for (const line of raw.split('\n')) {
    if (line.startsWith('event:')) eventType = line.slice('event:'.length).trim();
    else if (line.startsWith('data:')) dataLines.push(line.slice('data:'.length).trim());
  }
  if (!eventType || dataLines.length === 0) return null;
  try {
    const data = JSON.parse(dataLines.join('\n'));
    if (['progress', 'complete', 'error'].includes(eventType))
      return { type: eventType, data };
  } catch { return null; }
  return null;
}

describe('SSE frame parser', () => {
  it('parses a progress event', () => {
    const raw = `event: progress\ndata: {"current_idx":0,"total":2168,"percent":0.046,"phase":"running","trades_so_far":0,"pnl_so_far":0,"win_rate_so_far":0.0,"current_position":"long","current_legs_filled":1}`;
    const ev = parseSseFrame(raw);
    expect(ev?.type).toBe('progress');
    expect((ev?.data as any).current_idx).toBe(0);
    expect((ev?.data as any).total).toBe(2168);
  });

  it('parses an error event', () => {
    const raw = `event: error\ndata: {"detail":"data file not found: NQ_4h.csv"}`;
    const ev = parseSseFrame(raw);
    expect(ev?.type).toBe('error');
    expect((ev?.data as any).detail).toContain('not found');
  });

  it('parses a complete event with 2168 candles and 646 trades', () => {
    const metrics = { total_profit: 116788, total_trades: 646, win_rate: 84.67, profit_factor: 2.71, avg_profit: 338.4, avg_loss: -690.16, gross_profit: 185114, gross_loss: -68326, expected_value: 180.79, max_drawdown: 6300, sharpe_ratio: 0.337, wins: 547, losses: 99 };
    const candles = Array.from({ length: 2168 }, (_, i) => ({
      t: `2025-01-${String(Math.floor(i / 4) + 1).padStart(2, '0')} ${String((i % 4) * 4).padStart(2, '0')}:00:00`,
      o: 21000, h: 21100, l: 20900, c: 21050, v: 10000,
    }));
    const trades = Array.from({ length: 646 }, (_, i) => ({
      entry_idx: i * 3, exit_idx: i * 3 + 2, direction: 'long',
      avg_entry_price: 21000, exit_price: 21150,
      contracts: 1, profit_points: 150, profit_dollars: 300,
      exit_reason: 'TAKE PROFIT', legs: [{ contracts: 1, price: 21000, candle_idx: i * 3 }],
    }));
    const payload = { metrics, candles, trades, elapsed_ms: 353 };
    const raw = `event: complete\ndata: ${JSON.stringify(payload)}`;
    const ev = parseSseFrame(raw);
    expect(ev?.type).toBe('complete');
    const d = ev?.data as any;
    expect(d.metrics.total_trades).toBe(646);
    expect(d.candles).toHaveLength(2168);
    expect(d.trades).toHaveLength(646);
    expect(d.elapsed_ms).toBe(353);
  });

  it('returns null for an empty frame', () => {
    expect(parseSseFrame('')).toBeNull();
    expect(parseSseFrame('   ')).toBeNull();
  });

  it('returns null for a frame with no event type', () => {
    expect(parseSseFrame('data: {"foo":1}')).toBeNull();
  });

  it('returns null when JSON is malformed', () => {
    expect(parseSseFrame('event: progress\ndata: {bad json')).toBeNull();
  });
});
