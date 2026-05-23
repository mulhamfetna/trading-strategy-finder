/**
 * Pure helpers used by ChartPane.vue. Extracted into a separate module
 * so they can be unit-tested against production behaviour (BUG-025).
 */

import type { Time } from 'lightweight-charts';
import type { Candle } from '../types';

/**
 * Convert a candle timestamp string to a Lightweight Charts
 * UTCTimestamp (seconds since epoch).
 *
 * The 4h CSV produces "YYYY-MM-DD HH:MM:SS" (space separator). LWC
 * intraday charts require a numeric UTCTimestamp — passing a string
 * causes the chart to silently render nothing.
 */
export function toUTCTimestamp(t: string): Time {
  const iso = t.replace(' ', 'T');
  const ms = new Date(iso + (iso.endsWith('Z') ? '' : 'Z')).getTime();
  if (isNaN(ms)) throw new Error(`Invalid candle timestamp: ${t}`);
  return (ms / 1000) as unknown as Time;
}

export interface CandlestickRow {
  time: Time;
  open: number;
  high: number;
  low: number;
  close: number;
}

export function toLwcData(rows: Candle[]): CandlestickRow[] {
  return rows.map((row) => ({
    time: toUTCTimestamp(row.t),
    open: row.o,
    high: row.h,
    low: row.l,
    close: row.c,
  }));
}

export function computeEMA(prices: number[], period: number): (number | null)[] {
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

export function computeRSI(prices: number[], period: number): (number | null)[] {
  if (prices.length < period + 1) return prices.map(() => null);
  const out: (number | null)[] = new Array(period).fill(null);
  let avgGain = 0;
  let avgLoss = 0;
  for (let i = 1; i <= period; i++) {
    const d = prices[i] - prices[i - 1];
    if (d > 0) avgGain += d;
    else avgLoss -= d;
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
