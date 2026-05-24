---
name: src_api_schemas
mirrors: src/api/schemas.py
purpose: Pydantic request / response models for the FastAPI surface. The graphics pipeline relies on `Candle`, `CandlesRange`, `CandlesResponse`, and the `BoxRect`-shaped dicts returned from /api/boxes — and on `BoxBacktestRequest` matching what the SSE client sends.
related: [[src_api_app]], [[fe_types]]
---

# `src/api/schemas.py`

Defines the wire shape for every chart-relevant endpoint. The TypeScript file [[fe_types]] must mirror these models field-for-field; drift produces 422s.

Per the no-fallback rule, every request field is REQUIRED. The form on the frontend pre-populates defaults so the user always submits a complete payload — the backend rejects partial payloads.

## Models in this file (graphics-relevant)

| Model | What the chart does with it |
|---|---|
| `Candle` | OHLCV row. `t,o,h,l,c,v` — short keys so SSE frames stay small. Drawn by ChartPane's candle series. |
| `CandlesRange` | `{ start, end }` — echo of the requested date window. |
| `CandlesResponse` | `{ candles, count, range }` — payload of `GET /api/candles`. |
| `BoxBacktestRequest` | Request body of `POST /api/backtest/box`. The `box_data_path` field selects which unified CSV [[boxlookup_get_box_rects]] reads from; the `start` / `end` fields scope the BoxRects shipped back. |

`BoxRect` is **not** declared as a Pydantic model — it's returned as a plain dict from [[boxlookup_get_box_rects]] and consumed on the frontend via the [[fe_types]] `BoxRect` TypeScript interface. The two must be kept in sync by hand: `start_time, end_time, upper, lower, level, timeframe, fill_color, border_color`.

`Metrics`, `ScalingParamsModel`, `BoxParamsModel`, the optimizer schemas, and the validator in `BoxParamsModel` (SL ordering invariants) are strategy / execution concerns — out of graphics scope.
