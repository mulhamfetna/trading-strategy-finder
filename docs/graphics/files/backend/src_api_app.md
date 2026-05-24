---
name: src_api_app
mirrors: src/api/app.py
purpose: FastAPI application — exposes the REST + SSE endpoints that the dashboard chart consumes. Only the candle / box / backtest paths are documented here; optimizer endpoints are out of graphics scope.
related: [[src_api_schemas]], [[src_strategy_box_lookup]]
---

# `src/api/app.py`

FastAPI app entry point. Wraps the strategy engine behind REST + SSE so the Vue dashboard can draw candles, fetch box overlays, and stream backtest progress.

The application also wires two custom exception handlers:
- `ConfigurationError` → 422 JSON body with the structured `code` / `message` / `system_status` shape.
- `RequestValidationError` → 422 with a list of which fields failed validation plus the received body — this is what the frontend sees when the SSE wire shape drifts.

Beyond exception handling, CORS is permissive in dev (Vite at localhost:5173) and configurable in prod via `TRADING_DASH_ALLOW_ORIGINS`.

## Functions in this file (graphics-relevant)

| Function | Doc |
|---|---|
| `_load_and_filter(data_path, start, end)` | [[load_and_filter]] |
| `_candles_from_df(df) -> List[Candle]` | [[candles_from_df]] |
| `get_candles(start, end, data_path)` | [[get_candles]] |
| `get_boxes(start, end, box_data_path, tick_threshold)` | [[get_boxes]] |
| `list_data_files()` | [[list_data_files]] |

The SSE backtest endpoint (`post_box_backtest` / `_box_event_stream`) is also graphics-relevant because the `complete` payload it streams contains the `candles` and `boxes` arrays that ChartPane renders. The endpoint itself is not deeply documented here because the strategy execution side of it is out of scope; the chart-relevant slice of its work is:

1. After the engine finishes, it calls `_candles_from_df(df)` and ships the result as `complete_payload['candles']`.
2. It calls `box_lookup.get_box_rects(range_start, range_end)` once up-front (see [[boxlookup_get_box_rects]]) and ships the result as `complete_payload['boxes']`.

Both arrays land in `useBacktestStore` ([[fe_stores_backtest]]) and from there in ChartPane.

## Endpoint surface (graphics-relevant only)

```
GET  /api/candles        → [[get_candles]]      → CandlesResponse
GET  /api/boxes          → [[get_boxes]]        → { boxes: BoxRect[] }
GET  /api/data-files     → [[list_data_files]]  → { files: string[] }
POST /api/backtest/box   → SSE stream — `complete` event carries candles + boxes
GET  /api/health         → liveness probe (not graphics-related)
POST /api/upload-data-file → CSV upload (data plumbing, not graphics)
```
