---
name: get_candles
file: src/api/app.py
signature: GET /api/candles?start=&end=&data_path=  → CandlesResponse
responsibility: Public REST endpoint that returns OHLCV bars for the dashboard. The pre-backtest path for getting candles onto the chart — used by the candles store, not by the backtest flow.
related: [[load_and_filter]], [[candles_from_df]], [[fetchCandles]], [[candlesStore_load]]
---

# `GET /api/candles` → `get_candles(...)`

FastAPI handler bound at `/api/candles`. Returns a `CandlesResponse` Pydantic model.

## Query parameters (all required)

| Param | Type | Meaning |
|---|---|---|
| `start` | `str` | Inclusive `YYYY-MM-DD`. |
| `end` | `str` | Inclusive `YYYY-MM-DD`. |
| `data_path` | `str` | Path to the OHLCV CSV (relative to repo root). Required — the no-fallback rule applies; the backend never picks a default. |

## Implementation

```
df       = _load_and_filter(data_path, start, end)   # → [[load_and_filter]]
candles  = _candles_from_df(df)                       # → [[candles_from_df]]
return CandlesResponse(candles=candles, count=len(candles), range=CandlesRange(start, end))
```

That's the whole function — it composes the two helpers and wraps the result.

## Errors the chart will see

- 400 — bad date format or `start > end`. Frontend surfaces the `detail` string in the candles store's `error.value`.
- 422 — missing CSV (`MissingDataFileError`), missing OHLCV columns (`ConfigurationError(code='missing-candle-columns')`), or missing/wrong-type query parameter (Pydantic `RequestValidationError`). All come back with structured `code` / `message` / `system_status`.
- 500 — unexpected exception during CSV load. Frontend should treat this as a bug to file.

## What this endpoint does NOT do

- It does not stream — the response is a single JSON document. Streaming is reserved for the backtest endpoint.
- It does not return boxes — boxes flow into the chart through the SSE `complete` event during a backtest, not through this endpoint.
- It does not honour `dataset = train | test`. The frontend forwards it but the backend currently uses the same CSV for both — the split happens later inside the strategy engine. This is intentional; do not patch the endpoint to ignore the param.
