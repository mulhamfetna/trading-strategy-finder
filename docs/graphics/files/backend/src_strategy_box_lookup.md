---
name: src_strategy_box_lookup
mirrors: src/strategy/box_lookup.py
purpose: Loads the unified weekly+monthly box CSV and (for the chart) builds the `BoxRect[]` array of rectangles to overlay behind the candles. Also answers per-bar traversal signals for the strategy engine — only the rectangle-emission path is graphics-relevant.
related: [[src_api_app]], [[fe_components_boxesprimitive]]
---

# `src/strategy/box_lookup.py`

`BoxLookup` is the bridge between `NQ_full_data.csv` and the chart overlay. It does two jobs; only the second is graphics:

1. **Strategy signals (out of graphics scope)** — `get_signal`, `get_signal_detail`, the traversal state machine. The engine asks "did this close cross a box level?" and gets `long` / `short` / `hold` / `None`.

2. **Chart overlay (this file)** — `get_box_rects(start, end)` returns the rectangle list the frontend renders. Each rect is a plain dict, NOT a Pydantic model. Its shape must match the TypeScript `BoxRect` interface in [[fe_types]] exactly:

   ```
   {
     start_time:   int,    # unix seconds (UTC), 18:00 of the day before the row's Date
     end_time:     int,    # unix seconds (UTC), 17:00 of the row's Date
     upper:        float,
     lower:        float,
     level:        str,    # e.g. 'W-RH', 'M-IL sub'
     timeframe:    str,    # 'weekly' | 'monthly'
     fill_color:   str,    # rgba(…) string from _LEVEL_COLORS
     border_color: str,    # rgba(…) string from _LEVEL_COLORS
   }
   ```

## Module-level constants (used by the chart)

| Constant | Role |
|---|---|
| `_WEEKLY_LEVELS` | 8 tuples of `(upper_col, lower_col, label)` — the W* columns in the CSV. Defines which columns get a rectangle and what label appears on it. |
| `_MONTHLY_LEVELS` | Same shape, 8 monthly levels. |
| `_LEVEL_COLORS` | `label → (fill_rgba, border_rgba)`. Each rect carries its colour strings inline so the frontend renderer never has to look them up. Monthly hues are softer than weekly so the timeframes are visually distinguishable. |

The label vocabulary is fixed — `W-TH`, `W-TH sub`, `W-RH`, `W-IH`, `W-IL`, `W-RL`, `W-TL`, `W-TL sub`, and the monthly mirrors. Adding a level means adding it both in the `_*_LEVELS` list AND in `_LEVEL_COLORS`.

## Functions in this file (graphics-relevant)

| Function | Doc |
|---|---|
| `BoxLookup.get_box_rects(start, end)` | [[boxlookup_get_box_rects]] |

The traversal / state-machine functions (`_classify`, `_step_level`, `_best_level`, `get_signal`, `get_signal_detail`, `reset_state`) and the date-mapping helpers (`_candle_to_box_date`, `_active_row`, `_load`) belong to the strategy side, not the chart. They are intentionally not documented here.

The one date-mapping behaviour the chart inherits from this module: rectangles emitted by `get_box_rects` use the NQ-session convention — `start_time` is 18:00 of the day BEFORE the row's tagged `Date`, `end_time` is 17:00 of that `Date`. This is what makes box overlays line up correctly under the 4h NQ candles even though the CSV uses one row per session-closing day.
