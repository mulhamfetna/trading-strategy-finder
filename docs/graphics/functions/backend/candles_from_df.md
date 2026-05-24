---
name: candles_from_df
file: src/api/app.py
signature: _candles_from_df(df: pd.DataFrame) -> List[Candle]
responsibility: Turn an OHLCV DataFrame into the wire-shape list of Candle Pydantic models the frontend's ChartPane consumes. Normalises the timestamp column shape and enforces the no-fallback rule on required OHLCV columns.
related: [[get_candles]], [[load_and_filter]], [[toUTCTimestamp]]
---

# `_candles_from_df`

The chokepoint where backend DataFrames become frontend Candles. Two endpoints call it: `/api/candles` (REST) and the SSE `complete` payload assembler inside `_box_event_stream`.

## Required columns (no-fallback rule)

`('Open', 'High', 'Low', 'Close', 'Volume')` must all be present. Missing any raises `ConfigurationError(code='missing-candle-columns', system_status={...})` carrying the list of missing columns, the list of columns actually present, and a hint. The 422 handler ships this verbatim to the caller.

There is intentionally no fallback to zero / NaN — the chart must not silently render a volume bar of zero or a flat candle when the source file is malformed.

## Timestamp normalisation (BUG-016 fix)

The CSVs in scope can present timestamps three different ways. Each gets normalised to the same output shape `YYYY-MM-DDTHH:MM:SS`:

| Input columns | How `timestamps[i]` is built |
|---|---|
| `Date` + `Time` and `Date` is a parsed `datetime64` | `df['Date'].dt.strftime('%Y-%m-%d')` + `'T'` + `df['Time'].astype(str)` |
| `Date` + `Time`, `Date` is already a string | `df['Date'].astype(str).str.slice(0, 10)` + `'T'` + `df['Time'].astype(str)` |
| `Date` only, parsed | `df['Date'].dt.strftime('%Y-%m-%dT%H:%M:%S').tolist()` |
| `Date` only, string | `df['Date'].astype(str).tolist()` |
| `timestamps` column | passed through as string |
| nothing recognisable | the row index, stringified (last-resort marker — should not happen in practice) |

The BUG-016 fix: when `Date` is a parsed Timestamp AND a separate `Time` column exists, `astype(str)` on a `Timestamp` returns `"YYYY-MM-DD HH:MM:SS"` — concatenating with the `Time` column then produced corrupted strings like `"YYYY-MM-DD 00:00:00THH:MM:SS"` (BUG-003 pattern). The `dt.strftime('%Y-%m-%d')` call strips the time portion before concatenation.

## Output

A list of `Candle(t=..., o=..., h=..., l=..., c=..., v=...)` Pydantic models. Numeric coercions are explicit: `float(df.iloc[i]['Open'])` etc — pandas / numpy scalar types do not serialise cleanly to JSON, so the explicit float / int casts matter.

## Empty input

`len(df) == 0` returns `[]` without touching column checks. This is deliberate: an empty range can be the user's actual request and shouldn't produce a 422.
