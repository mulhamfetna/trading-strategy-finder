---
name: fe_services_api
mirrors: frontend/src/services/api.ts
purpose: Axios REST client. The only graphics-relevant call here is fetchCandles — it pulls OHLCV from the backend so the chart has bars to draw before a backtest is ever run.
related: [[fe_stores_candles]], [[src_api_app]]
---

# `frontend/src/services/api.ts`

Typed REST client wrapping `/api/*`. Uses relative URLs so the same code works in dev (Vite proxies to `localhost:8000`) and in production (frontend served from the backend origin).

The client has a 30-second timeout — long enough for the largest currently-active 4h dataset, generous enough to survive a slow load.

## Functions in this file (graphics-relevant)

| Function | Doc |
|---|---|
| `fetchCandles(start, end, dataset, dataPath)` | [[fetchCandles]] |

The SSE-streamed POST endpoint (`/api/backtest/box`) is implemented in `frontend/src/services/sse.ts`, not here, because it can't use axios — browser EventSource doesn't support POST so it uses raw `fetch()` + a ReadableStream reader. That file ships candles + boxes into the backtest store after every run.

## What this file does NOT do

No upload calls, no box fetcher, no health check. Boxes reach the chart through the SSE `complete` event embedded in the backtest stream — not through a dedicated REST call. The standalone `GET /api/boxes` endpoint ([[get_boxes]]) exists on the backend but no frontend code currently invokes it.
