---
name: fetchCandles
file: frontend/src/services/api.ts
signature: fetchCandles(start: string, end: string, dataset: 'train' | 'test', dataPath: string) → Promise<CandlesResponse>
responsibility: Axios GET against /api/candles. The wire-level call that takes a date range + CSV path and returns the candles that will become bars on the chart.
related: [[get_candles]], [[candlesStore_load]]
---

# `fetchCandles`

The one and only function in `frontend/src/services/api.ts`. Thin wrapper around an axios GET.

## Signature

```ts
async function fetchCandles(
  start: string,
  end: string,
  dataset: 'train' | 'test',
  dataPath: string,
): Promise<CandlesResponse>;
```

## Implementation

```ts
const resp = await client.get<CandlesResponse>('/candles', {
  params: { start, end, dataset, data_path: dataPath },
});
return resp.data;
```

`client` is the module-level axios instance with `baseURL: '/api'` and a 30 s timeout. The final URL therefore resolves to `/api/candles?...`.

## Parameter mapping

| Frontend param | Backend query key |
|---|---|
| `start` | `start` |
| `end` | `end` |
| `dataset` | `dataset` (forwarded but not currently used; see [[get_candles]]) |
| `dataPath` | `data_path` (note the snake_case rename) |

The snake_case rename matters — the backend's Pydantic models reject camelCase. Don't "fix" this by renaming the backend param.

## Errors

Axios rejects on non-2xx. The caller ([[candlesStore_load]]) catches and stores the error message; this function does no special handling — it just propagates the rejection.
