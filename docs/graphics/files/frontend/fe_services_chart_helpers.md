---
name: fe_services_chart_helpers
mirrors: frontend/src/services/chart_helpers.ts
purpose: Pure helpers used by ChartPane — timestamp conversion, candle-row reshape, EMA, RSI. Extracted from the component so they can be unit-tested against production behaviour.
related: [[fe_components_chartpane]]
---

# `frontend/src/services/chart_helpers.ts`

All four exports are pure functions. Pulling them out of `ChartPane.vue` was driven by BUG-025: tests used to inline copies that drifted from production. Now the component and its tests both import the same module.

## Functions in this file

| Function | Doc | One-line role |
|---|---|---|
| `toUTCTimestamp(t)` | [[toUTCTimestamp]] | `"YYYY-MM-DDTHH:MM:SS"` → LWC `UTCTimestamp` (seconds since epoch). |
| `toLwcData(rows)` | [[toLwcData]] | `Candle[]` → `CandlestickRow[]` for `candleSeries.setData`. |
| `computeEMA(prices, period)` | [[computeEMA]] | EMA series for the EMA overlay lines. |
| `computeRSI(prices, period)` | [[computeRSI]] | RSI series for the RSI pane. |

`CandlestickRow` is the row shape Lightweight Charts expects from a candlestick series — `{ time, open, high, low, close }`. Exported so tests can assert against it.
