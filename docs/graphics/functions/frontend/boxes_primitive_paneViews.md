---
name: boxes_primitive_paneViews
file: frontend/src/components/BoxesPrimitive.ts
signature: BoxesPrimitive.paneViews() → readonly IPrimitivePaneView[]
responsibility: LWC contract hook. Returns the list of pane views that participate in drawing. This primitive uses a single pane view (the one bound to the candle series' pane).
related: [[boxes_paneView_renderer]], [[fe_components_boxesprimitive]]
---

# `BoxesPrimitive.paneViews`

## Implementation

```ts
paneViews(): readonly IPrimitivePaneView[] {
  return [this._paneView];
}
```

Single-element array, the `BoxesPaneView` instance constructed in the primitive's constructor.

## Why one pane view

Boxes live exclusively on the main price pane (pane 0, where candles are). They are not drawn on the volume pane or the RSI pane. A separate-pane overlay would need a separate pane view.

## When LWC calls this

Every frame, alongside `renderer()`. LWC iterates the returned array and asks each pane view for its renderer. There is no caching at this layer — if pane composition ever needs to change at runtime, this method can be made stateful (it currently returns the same array on every call).
