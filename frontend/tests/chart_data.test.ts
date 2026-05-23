/**
 * Tests for ChartPane data-conversion functions and LWC timestamp handling.
 * Catches the "space timestamp" bug where "2025-01-01 18:00:00" is passed
 * to LWC instead of a UTCTimestamp number.
 *
 * BUG-025 fix: this file imports the production helpers. Previously it
 * inlined copies, so the tests passed even when ChartPane drifted.
 */
import { describe, it, expect } from 'vitest';
import type { Candle } from '../src/types';
import {
  toUTCTimestamp,
  toLwcData,
  computeEMA,
  computeRSI,
} from '../src/services/chart_helpers';

// ---- Tests ----

const SAMPLE: Candle[] = [
  { t: '2025-01-01 18:00:00', o: 21269.0, h: 21333.0, l: 21121.75, c: 21322.25, v: 32778 },
  { t: '2025-01-01 22:00:00', o: 21322.5,  h: 21419.0, l: 21260.0,  c: 21419.0, v: 18820 },
  { t: '2025-01-02 02:00:00', o: 21419.0,  h: 21419.0, l: 21047.5,  c: 21057.75, v: 9031 },
];

// toUTCTimestamp returns LWC's branded `Time` type. At runtime it's a
// plain number — cast here for numeric assertions.
const asNum = (t: unknown): number => t as number;

describe('candle timestamp conversion', () => {
  it('converts space-separated timestamp to UTCTimestamp (number)', () => {
    const ts = toUTCTimestamp('2025-01-01 18:00:00');
    expect(typeof ts).toBe('number');
    expect(isNaN(asNum(ts))).toBe(false);
    expect(asNum(ts)).toBeGreaterThan(1_000_000_000);
  });

  it('converts T-separated ISO timestamp to UTCTimestamp', () => {
    const ts = toUTCTimestamp('2025-01-01T18:00:00');
    expect(typeof ts).toBe('number');
    expect(isNaN(asNum(ts))).toBe(false);
  });

  it('both formats produce the same Unix timestamp', () => {
    const a = toUTCTimestamp('2025-01-01 18:00:00');
    const b = toUTCTimestamp('2025-01-01T18:00:00');
    expect(a).toBe(b);
  });

  it('timestamps are monotonically increasing across candles', () => {
    const lwc = toLwcData(SAMPLE);
    for (let i = 1; i < lwc.length; i++) {
      expect(asNum(lwc[i].time)).toBeGreaterThan(asNum(lwc[i - 1].time));
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
