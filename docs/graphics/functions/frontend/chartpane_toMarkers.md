---
name: chartpane_toMarkers
file: frontend/src/components/ChartPane.vue
signature: toMarkers(rows: Candle[], tradeRows: ScalingTrade[], viewTo = Infinity) → SeriesMarker<Time>[]
responsibility: Builds the array of arrow / square markers the Lightweight Charts markers plugin draws over the candle series. One entry-arrow per trade, plus one exit-square once the exit bar is in view.
related: [[chartpane_applyData]], [[fe_components_chartpane]]
---

# `toMarkers`

Pure transform. Takes the visible candle slice plus the trades and produces an LWC-ready marker list.

## Per trade, two markers

```
ENTRY:
  time      = toUTCTimestamp(rows[t.entry_idx].t)
  position  = 'belowBar' (long) | 'aboveBar' (short)
  color     = CHART_THEME.bull (long) | CHART_THEME.bear (short)
  shape     = 'arrowUp' (long) | 'arrowDown' (short)
  text      = 'B' (long) | 'S' (short)

EXIT (only when t.exit_idx <= viewTo):
  time      = toUTCTimestamp(rows[t.exit_idx].t)
  position  = 'aboveBar' (long) | 'belowBar' (short)
  color     = CHART_THEME.bull (profit ≥ 0) | CHART_THEME.bear (profit < 0)
  shape     = 'square'
  text      = '+12' or '-7'   (signed integer point profit, no decimals)
```

The `viewTo` cutoff is the trick that makes replay work for trades: a trade that is still open at the current replay frontier shows only its entry arrow. The exit appears the moment the playback reaches `exit_idx`.

## Sorting

```ts
return markers.sort((a, b) => (a.time as number) - (b.time as number));
```

LWC requires markers in time-ascending order; out-of-order input throws. The cast is needed because `Time` is an opaque branded type — the numeric UTCTimestamp underneath is fine to subtract.

## Edge cases

- `rows.length === 0` or `tradeRows.length === 0` → empty array. Cheap early return.
- `rows[t.entry_idx]` undefined (idx out of range) → that trade's entry marker is silently skipped. Same for exit. This is intentional — partial replay slices can validly have trades whose entries aren't in scope yet.

## What this function does NOT do

- It does not filter by `entry_idx <= viewTo`. The caller in [[chartpane_applyData]] does that BEFORE calling `toMarkers`, because the marker list is then handed to LWC's markers API which doesn't re-filter.
- It does not render anything. The output goes into `markersApi.setMarkers(...)`.
- It does not use `t.exit_price` or `t.avg_entry_price` — only `entry_idx`, `exit_idx`, `direction`, `profit_dollars`, `profit_points`. The candle-grounded display prices are referenced elsewhere (trade list), not on the chart.
