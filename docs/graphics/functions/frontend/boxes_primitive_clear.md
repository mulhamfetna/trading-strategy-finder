---
name: boxes_primitive_clear
file: frontend/src/components/BoxesPrimitive.ts
signature: BoxesPrimitive.clear() → void
responsibility: Reset the primitive to an empty state — no boxes, no bar times — and request a repaint. Provided for callers that want to explicitly drop the overlay (e.g. before a new dataset loads). Not currently called from ChartPane in production.
related: [[boxes_primitive_setBoxes]], [[fe_components_boxesprimitive]]
---

# `BoxesPrimitive.clear`

## Implementation

```ts
clear(): void {
  this._boxes = [];
  this._barTimes = [];
  this._requestUpdate?.();
}
```

## Why it exists when ChartPane doesn't call it

The primitive is a self-contained module; its tests instantiate it directly without a ChartPane around it. `clear()` gives tests and any future caller a way to reset state without re-attaching.

In production the equivalent transition happens through [[chartpane_applyData]] — which always calls `setBarTimes(barTimes)` and `setBoxes(boxes.value)`, where `boxes.value` is `[]` between runs. The end result is the same (empty overlay, repaint requested) without a separate `clear()` call.

## When you might add a caller

If the chart ever needs to enter a state where the candle series remains intact but the box overlay must be hidden — e.g. a future "hide box overlays" user toggle — wiring it through `clear()` is the cleanest entry point.
