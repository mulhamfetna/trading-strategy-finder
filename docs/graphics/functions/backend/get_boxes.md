---
name: get_boxes
file: src/api/app.py
signature: GET /api/boxes?start=&end=&box_data_path=&tick_threshold=  → { boxes: BoxRect[] }
responsibility: Public REST endpoint that returns the list of box rectangles overlapping a date range. Currently used only ad-hoc / by tests — production chart-rendering of boxes flows through the SSE `complete` event instead. Kept available for future direct-load paths.
related: [[boxlookup_get_box_rects]], [[src_strategy_box_lookup]]
---

# `GET /api/boxes` → `get_boxes(...)`

FastAPI handler bound at `/api/boxes`. Returns a plain `{ "boxes": [...] }` dict, NOT a Pydantic-typed model — the items are the same dict shape [[boxlookup_get_box_rects]] returns.

## Query parameters (all required)

| Param | Type | Meaning |
|---|---|---|
| `start` | `str` | `YYYY-MM-DD`. |
| `end` | `str` | `YYYY-MM-DD`. |
| `box_data_path` | `str` | Path to the unified box CSV (typically `NQ_full_data.csv`). |
| `tick_threshold` | `float` | Points margin past a box edge before the traversal state machine considers the close "outside" the box. Required because BoxLookup uses it both at load time (none) and per-call (yes — this is the threshold). |

## Implementation

```python
bl = BoxLookup(unified_path=box_data_path, tick_threshold=tick_threshold)
rects = bl.get_box_rects(start, end)
return { "boxes": rects }
```

A fresh BoxLookup per call. Acceptable because the CSV is small (one row per session day) and the read is cached at the OS level.

## Frontend caller status

No frontend code currently calls this endpoint. Boxes reach the chart via the SSE `complete` payload (see [[src_api_app]]). Kept in place so:
- Manual diagnostics can pull boxes without running a full backtest.
- Future use cases — e.g. an "explore boxes only" mode — can hit it directly.

If a frontend caller is added, mirror its wire shape in the [[fe_types]] `BoxRect` interface.

## Errors

- 422 — missing CSV, malformed box geometry (`ConfigurationError(code='malformed-box-geometry')`), or missing query parameters.
- 500 — anything else during load.
