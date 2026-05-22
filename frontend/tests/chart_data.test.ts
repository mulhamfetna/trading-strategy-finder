/**
 * Tests for ChartPane data-conversion functions and LWC timestamp handling.
 * Catches the "space timestamp" bug where "2025-01-01 18:00:00" is passed
 * to LWC instead of a UTCTimestamp number.
 */
import { describe, it, expect } from 'vitest';
import type { Candle } from '../src/types';

// ---- Inline the helpers from ChartPane so we can unit-test them ----

type Time = number; // UTCTimestamp

interface CandlestickData { time: Time; open: number; high: number; low: number; close: number; }
interface LineData { time: Time; value: number; }
interface HistogramData { time: Time; value: number; color: string; }

function toUTCTimestamp(t: string): number {
  // "2025-01-01 18:00:00" or "2025-01-01T18:00:00"
  const normalized = t.replace(' ', 'T');
  const ts = new Date(normalized + (normalized.includes('Z') ? '' : 'Z')).getTime();
  if (isNaN(ts)) throw new Error(`Invalid candle timestamp: ${t}`);
  return ts / 1000;
}

function toLwcData(rows: Candle[]): CandlestickData[] {
  return rows.map((row) => ({
    time: toUTCTimestamp(row.t),
    open: row.o, high: row.h, low: row.l, close: row.c,
  }));
}

function computeEMA(prices: number[], period: number): (number | null)[] {
  if (prices.length < period) return prices.map(() => null);
  const k = 2 / (period + 1);
  const out: (number | null)[] = new Array(period - 1).fill(null);
  let ema = prices.slice(0, period).reduce((s, v) => s + v, 0) / period;
  out.push(ema);
  for (let i = period; i < prices.length; i++) {
    ema = prices[i] * k + ema * (1 - k);
    out.push(ema);
  }
  return out;
}

function computeRSI(prices: number[], period: number): (number | null)[] {
  if (prices.length < period + 1) return prices.map(() => null);
  const out: (number | null)[] = new Array(period).fill(null);
  let avgGain = 0, avgLoss = 0;
  for (let i = 1; i <= period; i++) {
    const d = prices[i] - prices[i - 1];
    if (d > 0) avgGain += d; else avgLoss -= d;
  }
  avgGain /= period;
  avgLoss /= period;
  out.push(avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss));
  for (let i = period + 1; i < prices.length; i++) {
    const d = prices[i] - prices[i - 1];
    const gain = d > 0 ? d : 0;
    const loss = d < 0 ? -d : 0;
    avgGain = (avgGain * (period - 1) + gain) / period;
    avgLoss = (avgLoss * (period - 1) + loss) / period;
    out.push(avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss));
  }
  return out;
}

// ---- Tests ----

const SAMPLE: Candle[] = [
  { t: '2025-01-01 18:00:00', o: 21269.0, h: 21333.0, l: 21121.75, c: 21322.25, v: 32778 },
  { t: '2025-01-01 22:00:00', o: 21322.5,  h: 21419.0, l: 21260.0,  c: 21419.0, v: 18820 },
  { t: '2025-01-02 02:00:00', o: 21419.0,  h: 21419.0, l: 21047.5,  c: 21057.75, v: 9031 },
];

describe('candle timestamp conversion', () => {
  it('converts space-separated timestamp to UTCTimestamp (number)', () => {
    const ts = toUTCTimestamp('2025-01-01 18:00:00');
    expect(typeof ts).toBe('number');
    expect(isNaN(ts)).toBe(false);
    expect(ts).toBeGreaterThan(1_000_000_000); // definitely a Unix ts in seconds
  });

  it('converts T-separated ISO timestamp to UTCTimestamp', () => {
    const ts = toUTCTimestamp('2025-01-01T18:00:00');
    expect(typeof ts).toBe('number');
    expect(isNaN(ts)).toBe(false);
  });

  it('both formats produce the same Unix timestamp', () => {
    const a = toUTCTimestamp('2025-01-01 18:00:00');
    const b = toUTCTimestamp('2025-01-01T18:00:00');
    expect(a).toBe(b);
  });

  it('timestamps are monotonically increasing across candles', () => {
    const lwc = toLwcData(SAMPLE);
    for (let i = 1; i < lwc.length; i++) {
      expect(lwc[i].time).toBeGreaterThan(lwc[i - 1].time);
    }
  });

  it('throws on a garbage timestamp', () => {
    expect(() => toUTCTimestamp('not-a-date')).toThrow();
  });
});

describe('toLwcData', () => {
  it('produces correct OHLC values', () => {
    const data = toLwcData(SAMPLE);
    expect(data[0].open).toBe(21269.0);
    expect(data[0].high).toBe(21333.0);
    expect(data[0].low).toBe(21121.75);
    expect(data[0].close).toBe(21322.25);
  });

  it('returns number times (not strings)', () => {
    const data = toLwcData(SAMPLE);
    data.forEach((d) => expect(typeof d.time).toBe('number'));
  });
});

describe('computeEMA', () => {
  it('returns nulls for warmup period', () => {
    const prices = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
    const ema = computeEMA(prices, 3);
    expect(ema[0]).toBeNull();
    expect(ema[1]).toBeNull();
    expect(ema[2]).not.toBeNull();
  });

  it('length equals input length', () => {
    const prices = Array.from({ length: 50 }, (_, i) => i + 1);
    expect(computeEMA(prices, 20)).toHaveLength(50);
  });

  it('returns all nulls when fewer prices than period', () => {
    expect(computeEMA([1, 2], 5)).toEqual([null, null]);
  });
});

describe('computeRSI', () => {
  it('returns nulls for warmup period then real values', () => {
    const prices = Array.from({ length: 30 }, (_, i) => 100 + Math.sin(i) * 10);
    const rsi = computeRSI(prices, 14);
    expect(rsi[13]).toBeNull();
    expect(rsi[14]).not.toBeNull();
    expect(rsi[14]).toBeGreaterThanOrEqual(0);
    expect(rsi[14]).toBeLessThanOrEqual(100);
  });

  it('RSI of all-up prices approaches 100', () => {
    const prices = Array.from({ length: 20 }, (_, i) => 100 + i);
    const rsi = computeRSI(prices, 14);
    expect(rsi[rsi.length - 1]!).toBeGreaterThan(90);
  });

  it('RSI of all-down prices approaches 0', () => {
    const prices = Array.from({ length: 20 }, (_, i) => 100 - i);
    const rsi = computeRSI(prices, 14);
    expect(rsi[rsi.length - 1]!).toBeLessThan(10);
  });
});
