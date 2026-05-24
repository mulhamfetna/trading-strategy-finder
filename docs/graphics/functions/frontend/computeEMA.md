---
name: computeEMA
file: frontend/src/services/chart_helpers.ts
signature: computeEMA(prices: number[], period: number) → (number | null)[]
responsibility: Standard exponential moving average. Returns an array the same length as `prices`, with `null` at every index that hasn't reached the warmup period yet. ChartPane filters out the nulls when feeding the EMA line series.
related: [[chartpane_applyData]]
---

# `computeEMA`

## Implementation

```ts
if (prices.length < period) return prices.map(() => null);
const k = 2 / (period + 1);
const out: (number | null)[] = new Array(period - 1).fill(null);
let ema = prices.slice(0, period).reduce((s, v) => s + v, 0) / period;  // seed with SMA
out.push(ema);
for (let i = period; i < prices.length; i++) {
  ema = prices[i] * k + ema * (1 - k);
  out.push(ema);
}
return out;
```

The seed is a simple moving average over the first `period` closes; from there the EMA recursion takes over. Standard TradingView convention.

## Output shape

Length = `prices.length`. The first `period - 1` entries are `null`. Index `period - 1` is the SMA seed. Index `period` onward is the EMA proper.

If `prices.length < period`, the entire output is `null` — the EMA can't be plotted yet. ChartPane surfaces this case as a visible warning chip (`emaWarning`) so the user knows the line is hidden on purpose, not by a bug.

## Caller integration

ChartPane builds line-series data with a `reduce`:

```ts
const buildLineData = (vals: (number | null)[]): LineData<Time>[] =>
  vals.reduce<LineData<Time>[]>((acc, v, i) => {
    if (v !== null) acc.push({ time: times[i], value: v });
    return acc;
  }, []);
```

Nulls become "missing" points, which LWC handles natively (the line breaks rather than drawing through zero).

## Both EMAs share this function

Fast (default 20) and slow (default 50) EMAs both call this with their own period. The settings store owns the periods (`indicators.emaFast`, `indicators.emaSlow`); changing either triggers ChartPane's period watcher which calls `applyData()` again.
