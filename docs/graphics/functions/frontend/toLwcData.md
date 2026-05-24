---
name: toLwcData
file: frontend/src/services/chart_helpers.ts
signature: toLwcData(rows: Candle[]) → CandlestickRow[]
responsibility: Reshape an array of Candle (`{ t, o, h, l, c, v }`) into the row shape Lightweight Charts' candlestick series expects (`{ time, open, high, low, close }`). Drops the volume field — volume is fed to a separate histogram series.
related: [[toUTCTimestamp]], [[chartpane_applyData]]
---

# `toLwcData`

Trivial mapper. Exists separately so [[chartpane_applyData]] can stay short and so tests can assert against the exact output shape.

## Implementation

```ts
export function toLwcData(rows: Candle[]): CandlestickRow[] {
  return rows.map((row) => ({
    time:  toUTCTimestamp(row.t),
    open:  row.o,
    high:  row.h,
    low:   row.l,
    close: row.c,
  }));
}
```

`CandlestickRow` is `{ time: Time, open: number, high: number, low: number, close: number }`. Exported from the same module.

## Volume omission

Volume is not in the LWC candlestick row shape — LWC draws volume as a separate `Histogram` series in pane 1. ChartPane builds that histogram inline (not through this helper) because the histogram needs a per-bar colour decision (`r.c >= r.o ? bullTinted : bearTinted`) and a `priceFormat: { type: 'volume' }` series option.

## Performance

Allocates a new array on every call. ChartPane invokes this on every `applyData()` which fires on every replay scrub tick — if the candle count ever grows beyond ~50k bars this becomes worth caching against array identity. Currently the 4h NQ dataset spans roughly 7 years × ~6 bars/day ≈ 15k bars, which is well below the threshold.
