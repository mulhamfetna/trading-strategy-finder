---
name: boxes_paneView_renderer
file: frontend/src/components/BoxesPrimitive.ts
signature: BoxesPaneView.renderer() → IPrimitivePaneRenderer
responsibility: LWC pane-view hook. Returns a fresh BoxesRenderer instance every call, constructed from the latest primitive state. Called by LWC on every frame the primitive needs to redraw.
related: [[boxes_renderer_draw]], [[boxes_paneView_zOrder]], [[fe_components_boxesprimitive]]
---

# `BoxesPaneView.renderer`

## Implementation

```ts
renderer(): IPrimitivePaneRenderer {
  const { boxes, barTimes, chart, series } = this._getState();
  return new BoxesRenderer(boxes, barTimes, chart, series);
}
```

The pane view holds a `_getState` callback (closed over the primitive's state). Each frame, the pane view destructures the current state and constructs a renderer with it.

## Why a fresh renderer every frame

The renderer is intentionally cheap to allocate (4-tuple in the constructor; no heavy work until `draw` is called). Allocating per frame keeps the snapshot of `boxes` and `barTimes` consistent for the duration of one paint — there is no risk of the array being mutated mid-draw because the renderer's constructor stores the references atomically.

## When LWC calls this

- On chart initial paint.
- After `series.attachPrimitive(...)` runs.
- After any `requestUpdate()` callback the primitive holds is invoked (see [[boxes_primitive_setBoxes]]).
- On chart resize, pan, zoom, time-scale change.

## What this function does NOT do

- It does not draw. That's [[boxes_renderer_draw]].
- It does not decide layer ordering. That's [[boxes_paneView_zOrder]].
