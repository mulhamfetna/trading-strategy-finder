---
name: boxes_primitive_setBarTimes
file: frontend/src/components/BoxesPrimitive.ts
signature: BoxesPrimitive.setBarTimes(times: number[]) → void
responsibility: Hand the primitive the sorted list of real candle timestamps it should snap box edges onto. Called by [[chartpane_applyData]] on every data or replay change so box x-coordinates always reference the bars that are currently visible.
related: [[boxes_snapBox]], [[chartpane_applyData]], [[fe_components_boxesprimitive]]
---

# `BoxesPrimitive.setBarTimes`

## Implementation

```ts
setBarTimes(times: number[]): void {
  this._barTimes = times;
}
```

No requestUpdate call. Setting bar times alone does NOT request a repaint — see "Pairing" below.

## What gets passed in

```ts
// From chartpane_applyData:
const barTimes = rows.map((r) => (toUTCTimestamp(r.t) as unknown as number));
boxesPrimitive.setBarTimes(barTimes);
```

`rows` is the visible slice (`candles.value.slice(0, viewTo + 1)`), so during replay this array shrinks to whatever bars have been "revealed" so far. The cast to `number` is necessary because `Time` is an opaque branded type in TypeScript even though its runtime is a number.

## Pairing with setBoxes

The repaint request is on [[boxes_primitive_setBoxes]], not here. The convention in [[chartpane_applyData]] is:

```ts
boxesPrimitive.setBarTimes(barTimes);
boxesPrimitive.setBoxes(boxes.value);   // ← this one triggers the redraw
```

Calling them in this order means the renderer is reconstructed with both the new bar times AND the new boxes in one frame — no flash of mismatched state.

## Why no requestUpdate here

If `setBarTimes` requested a repaint and so did `setBoxes`, the chart would paint twice in quick succession on every data change. Centralising the request on `setBoxes` keeps it to one paint per call site.

## Invariant required

The input must be sorted ascending. [[boxes_snapBox]] uses [[boxes_lowerBound]] which assumes sorted input. The caller in ChartPane gets this for free because candle rows are chronological.
