---
name: boxes_snapBox
file: frontend/src/components/BoxesPrimitive.ts
signature: snapBox(box: { start_time, end_time }, barTimes: number[]) → BoxSnap | null
responsibility: Pure helper that maps a box's `[start_time, end_time)` window onto real bar timestamps. Returns the bar timestamps the renderer should pass to LWC's timeToCoordinate so the result is always a real pixel coordinate — never null.
related: [[boxes_lowerBound]], [[boxes_renderer_draw]], [[fe_components_boxesprimitive]]
---

# `snapBox`

The function that solves the off-bar timestamp problem. Its return value, `BoxSnap`, tells the renderer where to draw the box's left and right edges.

## Return shape

```ts
interface BoxSnap {
  x1: number | 'extend';
  x2: number | 'extend';
}
```

- A `number` is a real bar timestamp (Unix seconds) that LWC will accept for `timeToCoordinate`.
- `'extend'` means the box stretches past the chart edge on that side — the renderer translates this to a coordinate outside the visible canvas so the rectangle still renders flush with the edge.

A `null` return means the box is entirely off-chart and should not be drawn at all.

## Semantics: `end_time` is exclusive

Matches the backend's box-rect convention from [[boxlookup_get_box_rects]]. A bar whose timestamp equals `end_time` is the first bar AFTER the box and is correctly excluded.

## Algorithm

```
firstBar = barTimes[0]
lastBar  = barTimes[barTimes.length - 1]

# x1 (left edge)
if box.start_time <= firstBar:        x1 = 'extend'              # starts before chart
elif box.start_time > lastBar:        return null                # starts after chart
else:
    idx = lowerBound(barTimes, box.start_time)
    x1  = barTimes[min(idx, len-1)]                              # first bar >= start

# x2 (right edge)
if box.end_time > lastBar:            x2 = 'extend'              # ends after chart
elif box.end_time <= firstBar:        return null                # ends before chart starts
else:
    idx = lowerBound(barTimes, box.end_time) - 1
    if idx < 0:                       return null
    x2 = barTimes[idx]                                            # last bar < end (exclusive)

if both numeric and x1 >= x2:         return null                 # degenerate
```

The `-1` after the lower-bound call on `x2` is what makes the end exclusive: `lowerBound` gives the first bar `>= end_time`; subtracting one gives the last bar `< end_time`.

## Edge cases (covered by unit tests in `frontend/tests/`)

- Empty `barTimes` → `null`.
- Box entirely before the chart → `null`.
- Box entirely after the chart → `null`.
- Box exactly bridging the chart (start before, end after) → `{ x1: 'extend', x2: 'extend' }`.
- One-bar-wide intersection → `{ x1, x2 }` where `x1 === x2`; the renderer drops it because the height-or-width-zero check kicks in.

## Where the rect actually gets drawn

[[boxes_renderer_draw]] consumes the snap result and passes the numeric x's into `timeScale.timeToCoordinate(...)`. The `'extend'` literals are translated to `-W` (left of canvas) and `W * 2` (right of canvas) so the rectangle visibly clips at the canvas edge.
