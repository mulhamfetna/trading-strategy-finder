---
name: boxes_primitive_detached
file: frontend/src/components/BoxesPrimitive.ts
signature: BoxesPrimitive.detached() → void
responsibility: LWC lifecycle hook. Drops the chart / series handles so the primitive doesn't hold references that prevent GC after the chart is torn down.
related: [[boxes_primitive_attached]], [[fe_components_boxesprimitive]]
---

# `BoxesPrimitive.detached`

## Implementation

```ts
detached(): void {
  this._chart         = null;
  this._series        = null;
  this._requestUpdate = null;
}
```

## When this runs

LWC calls this from inside `chart.remove()`. [[chartpane_initChart]] calls `chart.remove()` during teardown (before reinstantiation) and `onBeforeUnmount` calls it on component destroy.

## Why null the handles

The primitive instance might be kept alive by Vue's reactivity system or by closures briefly after the chart is destroyed. Nulling the handles guarantees that any stray `paneViews()` → `renderer()` → `draw()` call after detachment hits the `if (!this._chart || !this._series ...)` guard at the top of [[boxes_renderer_draw]] and short-circuits to `return`.

Equivalent to telling GC: "this object is no longer holding the chart alive".
