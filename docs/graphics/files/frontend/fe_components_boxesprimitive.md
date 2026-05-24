---
name: fe_components_boxesprimitive
mirrors: frontend/src/components/BoxesPrimitive.ts
purpose: Custom Lightweight Charts v5 series primitive that paints TradingView-style box rectangles on the main price pane. Solves the off-bar timestamp problem (LWC's timeToCoordinate returns null for any time not in the series data).
related: [[fe_components_chartpane]], [[boxlookup_get_box_rects]]
---

# `frontend/src/components/BoxesPrimitive.ts`

A self-contained drawing module. ChartPane creates one instance, attaches it to the candle series, and feeds it `setBarTimes(barTimes)` + `setBoxes(boxes)`. Everything else is internal to this file.

## The core problem this file solves

Lightweight Charts' `timeScale().timeToCoordinate(time)` only returns a valid pixel x for timestamps that EXACTLY match a bar in the series data. Off-bar timestamps (weekend gaps, holidays, the 17:00–18:00 NQ session-close hour) return `null` — which would mean every box whose start or end fell in a gap would silently disappear.

The fix is the [[boxes_snapBox]] helper: given a box's `[start_time, end_time)` window plus a sorted array of the actual bar timestamps, it returns the bar timestamps the renderer should pass to `timeToCoordinate` so the result is always a real coordinate. Boxes that start before the first visible bar are marked `'extend'` and rendered to the left of the canvas; same for boxes that end after the last bar.

## Top-level exports

| Export | Kind | Doc |
|---|---|---|
| `BoxRect` (re-export) | interface | mirrors the backend dict from [[boxlookup_get_box_rects]] |
| `BoxSnap` | interface | return shape of `snapBox` — `{ x1, x2 }` where each is `number \| 'extend'` |
| `lowerBound(arr, val)` | function | [[boxes_lowerBound]] |
| `snapBox(box, barTimes)` | function | [[boxes_snapBox]] |
| `BoxesPrimitive` (class) | the primitive itself | see below |

## Internal classes

| Class | Doc | One-line role |
|---|---|---|
| `BoxesRenderer` (`.draw`) | [[boxes_renderer_draw]] | Canvas paint of all visible box rectangles, in a single pass. |
| `BoxesPaneView` (`.renderer`, `.zOrder`) | [[boxes_paneView_renderer]] / [[boxes_paneView_zOrder]] | LWC pane-view bridge. Returns a fresh renderer each frame and pins the z-order to `'bottom'` so boxes draw under the candles. |

## `BoxesPrimitive` instance methods

| Method | Doc | Called by |
|---|---|---|
| `attached(params)` | [[boxes_primitive_attached]] | LWC, when [[chartpane_initChart]] runs `candleSeries.attachPrimitive(boxesPrimitive)`. |
| `detached()` | [[boxes_primitive_detached]] | LWC, on chart teardown. |
| `paneViews()` | [[boxes_primitive_paneViews]] | LWC, every frame. |
| `setBarTimes(times)` | [[boxes_primitive_setBarTimes]] | [[chartpane_applyData]], every time candles change. |
| `setBoxes(boxes)` | [[boxes_primitive_setBoxes]] | [[chartpane_applyData]], every time the box list changes. |
| `clear()` | [[boxes_primitive_clear]] | Not currently invoked from ChartPane; provided for completeness. |
