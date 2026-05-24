---
name: computeRSI
file: frontend/src/services/chart_helpers.ts
signature: computeRSI(prices: number[], period: number) → (number | null)[]
responsibility: Wilder-smoothed RSI (the standard implementation). Returns an array the same length as `prices` with `null` until enough history accumulates. ChartPane feeds the result to the RSI pane line series (with 30 and 70 horizontal threshold lines added separately).
related: [[chartpane_applyData]]
---

# `computeRSI`

## Implementation

```ts
if (prices.length < period + 1) return prices.map(() => null);
const out: (number | null)[] = new Array(period).fill(null);

// Seed: average gain / loss over first `period` price diffs
let avgGain = 0, avgLoss = 0;
for (let i = 1; i <= period; i++) {
  const d = prices[i] - prices[i - 1];
  if (d > 0) avgGain += d;
  else avgLoss -= d;
}
avgGain /= period;
avgLoss /= period;
out.push(avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss));

// Wilder smoothing for the rest
for (let i = period + 1; i < prices.length; i++) {
  const d = prices[i] - prices[i - 1];
  const gain = d > 0 ? d : 0;
  const loss = d < 0 ? -d : 0;
  avgGain = (avgGain * (period - 1) + gain) / period;
  avgLoss = (avgLoss * (period - 1) + loss) / period;
  out.push(avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss));
}
return out;
```

## Output shape

Length = `prices.length`. The first `period` entries are `null` (need `period + 1` prices to compute the first diff series). Index `period` onward is the RSI proper.

`avgLoss === 0` returns 100 explicitly — the standard RSI formula divides by `avgLoss`, so zero loss must be handled as "fully overbought" rather than letting the calculation produce `Infinity`.

## Threshold lines

The 30 (oversold) and 70 (overbought) horizontal lines are NOT part of the data this function returns. They are added in [[chartpane_initChart]] via `rsiSeries.createPriceLine(...)` with the dashed bull/bear-threshold colours from `CHART_THEME`.

## Pane allocation

The RSI line goes in pane 1 when volume is off, or pane 2 when volume is on. ChartPane handles the pane-index math in [[chartpane_initChart]]; this function doesn't know or care about pane placement.
