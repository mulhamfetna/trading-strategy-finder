---
name: load_and_filter
file: src/api/app.py
signature: _load_and_filter(data_path: str, start: str, end: str) -> pd.DataFrame
responsibility: Load the OHLCV CSV from disk and slice it to the requested date range. Centralises the validation + error mapping so /api/candles and the SSE backtest endpoint behave identically when the data file is missing or the date range is malformed.
related: [[get_candles]], [[candles_from_df]], [[src_api_app]]
---

# `_load_and_filter`

Private helper used by `/api/candles`. The SSE backtest endpoint has its own equivalent path that surfaces failures as SSE error frames instead of raising; this function is the REST counterpart.

## Behaviour

1. `os.path.exists(data_path)` — raises `MissingDataFileError(data_path, role='candles')` if missing. The exception handler turns this into a 422 with structured `code` / `message` / `system_status`.
2. Parses `start` and `end` as `pd.Timestamp`. A `ValueError` / `TypeError` here becomes a 400 with `detail="invalid date format; use YYYY-MM-DD"`.
3. Rejects `start > end` with a 400 explaining the values.
4. Calls `load_data(data_path)` (strategy-side loader, out of graphics scope). Wraps `MissingDataFileError` straight through; anything else becomes a 500 with the exception's message included.
5. Calls `filter_by_date_range(df, start, end)` (strategy-side splitter).
6. Returns `df.reset_index(drop=True)` so downstream code can rely on `df.iloc[i]` lining up with `i = 0..len(df)-1`.

## Why it matters for the chart

Every candle that reaches ChartPane has been through this function. The reset_index step is load-bearing — [[candles_from_df]] indexes positionally and would emit wrong rows if the input still carried the original CSV's row numbers.

## Not the place to look for

Box CSVs (use [[boxlookup_get_box_rects]] directly), the 1-min CSV (handled inline in `_box_event_stream`), or any kind of synthesis of OHLC from external sources.
