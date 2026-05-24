---
name: boxes_primitive_setBoxes
file: frontend/src/components/BoxesPrimitive.ts
signature: BoxesPrimitive.setBoxes(boxes: BoxRect[]) → void
responsibility: Hand the primitive the current list of box rectangles to draw, and request a repaint. The primary mutation point — every box-overlay refresh goes through this method.
related: [[boxes_primitive_setBarTimes]], [[boxes_renderer_draw]], [[chartpane_applyData]], [[fe_components_boxesprimitive]]
---

# `BoxesPrimitive.setBoxes`

## Implementation

```ts
setBoxes(boxes: BoxRect[]): void {
  this._boxes = boxes;
  this._requestUpdate?.();
}
```

Reference-swap the box array, then ask LWC for a repaint.

## requestUpdate semantics

`_requestUpdate` is the callback LWC handed in via [[boxes_primitive_attached]]. It schedules a repaint on the next animation frame — multiple calls in the same tick coalesce into one paint, so the `setBarTimes` + `setBoxes` pair from [[chartpane_applyData]] still produces just one redraw.

The optional chaining (`?.()`) guards against being called between primitive construction and `attached()`, or after `detached()` — both of which null `_requestUpdate`. Acceptable to silently no-op in those states because there's no chart to repaint anyway.

## Reference vs deep copy

The primitive stores the array reference, not a copy. If the caller later mutates the same array in place, the next paint will reflect the mutation. The current convention in ChartPane is to always pass a fresh array (`boxes.value` is a Pinia ref whose `.value` is reassigned, never mutated in place), so this is safe in practice.

## What happens on each repaint

1. LWC asks the pane view for a renderer → [[boxes_paneView_renderer]] constructs a fresh `BoxesRenderer` snapshotting the current `_boxes` and `_barTimes`.
2. LWC calls `renderer.draw(target)` → [[boxes_renderer_draw]] iterates the boxes and paints them.
