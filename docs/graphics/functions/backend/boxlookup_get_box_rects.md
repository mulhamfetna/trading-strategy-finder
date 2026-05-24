---
name: boxlookup_get_box_rects
file: src/strategy/box_lookup.py
signature: BoxLookup.get_box_rects(start: str, end: str) -> List[Dict[str, Any]]
responsibility: Build the array of box-rectangle dicts the chart overlay renders. Reads the unified box CSV rows that overlap [start, end], merges consecutive rows that share the same upper/lower for a level into a single rectangle, attaches colour strings, and emits NQ-session-aware Unix-seconds timestamps.
related: [[fe_components_boxesprimitive]], [[boxes_renderer_draw]], [[src_strategy_box_lookup]], [[get_boxes]]
---

# `BoxLookup.get_box_rects`

The graphics half of `BoxLookup`. Called once per backtest run (by `_box_event_stream` after the engine finishes) and ad-hoc by [[get_boxes]].

## Output dict shape

Each item in the returned list:

```
{
  start_time:   int,    # Unix seconds (UTC), 18:00 of (first_date − 1 day)
  end_time:     int,    # Unix seconds (UTC), 17:00 of last_date
  upper:        float,
  lower:        float,
  level:        str,    # e.g. 'W-RH'
  timeframe:    str,    # 'weekly' | 'monthly'
  fill_color:   str,    # rgba(…) from _LEVEL_COLORS
  border_color: str,    # rgba(…) from _LEVEL_COLORS
}
```

The frontend's `BoxRect` interface ([[fe_types]]) mirrors this exactly. The renderer ([[boxes_renderer_draw]]) consumes the rect verbatim.

## Algorithm

1. Filter the DataFrame to rows whose session overlaps `[start, end]`:
   `Date > start − 1 day AND Date <= end + 1 day`.
   The `± 1 day` slack handles the NQ session offset (18:00 prev-day → 17:00 same-day).
2. For each level family (`_WEEKLY_LEVELS`, then `_MONTHLY_LEVELS`), and each `(upper_col, lower_col, label)` inside:
   a. Pull the two price columns + `Date`, drop rows where either is NaN.
   b. Group consecutive rows where BOTH `upper` and `lower` are unchanged from the previous row AND the date gap is ≤ 4 calendar days. The 4-day rule handles weekend gaps without splitting a level that's constant Mon–Fri then resumes the next week with the same value (`>4` is the trigger to start a new group).
   c. For each group, emit one rect:
      - `upper`, `lower` from the first row of the group (constant across the group by construction).
      - `start_time` = `(first_date − 6 hours).timestamp()` — because `first_date` is at midnight, subtracting 6h gives 18:00 of the previous calendar day, which is when the NQ session for that box opens.
      - `end_time` = `(last_date + 17 hours).timestamp()` — 17:00 of `last_date`, when the NQ session closes.
      - `fill_color`, `border_color` from `_LEVEL_COLORS[label]`.

## NQ session timestamp convention

`start_time` and `end_time` are deliberately set to the actual NQ session window, not midnight-to-midnight. This makes box edges align under the candle data exactly — a 4h NQ bar at `18:00` is the first bar of session day D, and the box starts at that same `18:00` of (D-1) so the rectangle's left edge sits right under the open of the first session bar.

## Implementation note

Iterates with `.sort_index()` (NOT `.sort_values('Date')`) because the DataFrame holds `Date` both as the index AND as a column (the loader uses `set_index('Date', drop=False)`). pandas ≥ 1.5 raises `ValueError` on `sort_values` when the same name exists in both places.

## Failure modes

- Returns `[]` when no rows overlap or all the relevant columns are NaN — never raises.
- Malformed box geometry (upper ≤ lower) is NOT validated here; it surfaces from the traversal path's `_classify` instead. The chart-rendering path passes the values through untouched, and the renderer skips degenerate rectangles (height < 1 pixel).
