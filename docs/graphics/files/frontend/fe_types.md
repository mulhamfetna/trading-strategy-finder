---
name: fe_types
mirrors: frontend/src/types.ts
purpose: TypeScript shapes for everything that crosses the network into the chart — Candle, BoxRect, CandlesResponse, ScalingCompletePayload. Also exports the default CSV path constants the chart uses when the user hasn't picked a file.
related: [[src_api_schemas]], [[fe_services_api]], [[fe_components_chartpane]]
---

# `frontend/src/types.ts`

The TypeScript mirror of the Pydantic models in [[src_api_schemas]]. Keep both files in lockstep — every chart-rendering bug-class so far has involved one side adding a field the other side dropped silently.

## Types in this file (graphics-relevant)

| Type | Purpose |
|---|---|
| `Candle` | `{ t, o, h, l, c, v }` — what ChartPane draws as a candlestick. `t` is the ISO-ish string returned from [[candles_from_df]]. |
| `CandlesResponse` | `{ candles, count, range }` — return of `GET /api/candles`. |
| `BoxRect` | Rectangle for the chart overlay. Mirrors the dict shape produced by [[boxlookup_get_box_rects]]. |
| `ScalingCompletePayload` | The shape of the SSE `complete` event. Its `candles` and `boxes` arrays feed the chart after a backtest. |
| `ScalingTrade` | The shape of a single completed trade. Drives the entry/exit arrows + squares in [[chartpane_toMarkers]]. |
| `ScalingProgress` | Streaming progress shape; not drawn by the chart itself (ProgressBar consumes it). |

## Constants in this file (graphics-relevant)

| Constant | Value | Used by |
|---|---|---|
| `DEFAULT_DATA_PATH` | `'NQ_4h.csv'` | [[fe_stores_candles]] and the SSE backtest request — picks the candle CSV |
| `DEFAULT_DATA_PATH_1MIN` | `'NQ_1m.csv'` | SSE backtest request only — not drawn |
| `DEFAULT_BOX_DATA_PATH` | `'NQ_full_data.csv'` | SSE backtest request — selects which box CSV [[boxlookup_get_box_rects]] reads |
| `DEFAULT_SCALING_PARAMS`, `DEFAULT_BOX_PARAMS` | Form starter values, not drawing-related | Settings panel, not the chart |

`Metrics`, `BoxSignal`, the param interfaces, and the BigCandleResolution enum are strategy-side; ChartPane doesn't read them.
