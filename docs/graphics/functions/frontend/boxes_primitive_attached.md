---
name: boxes_primitive_attached
file: frontend/src/components/BoxesPrimitive.ts
signature: BoxesPrimitive.attached(params: { chart, series, requestUpdate }) → void
responsibility: LWC lifecycle hook called when `candleSeries.attachPrimitive(primitive)` runs. Stores the chart / series handles and the `requestUpdate` callback so subsequent setBoxes / setBarTimes calls can request a repaint.
related: [[boxes_primitive_detached]], [[chartpane_initChart]], [[fe_components_boxesprimitive]]
---

# `BoxesPrimitive.attached`

## Implementation

```ts
attached(params: { chart, series, requestUpdate }): void {
  this._chart         = params.chart;
  this._series        = params.series;
  this._requestUpdate = params.requestUpdate;
}
```

Just stash the three handles. No drawing happens here — the first paint is triggered by LWC's normal render cycle right after `attachPrimitive` returns.

## What each handle is for

| Handle | Used by |
|---|---|
| `_chart` | [[boxes_renderer_draw]] — `chart.timeScale().timeToCoordinate(...)` for x mapping. |
| `_series` | [[boxes_renderer_draw]] — `series.priceToCoordinate(price)` for y mapping. |
| `_requestUpdate` | [[boxes_primitive_setBoxes]] and [[boxes_primitive_clear]] — invoked to ask LWC for a repaint. |

## When this is called

Once per chart lifetime, immediately after [[chartpane_initChart]] runs `candleSeries.attachPrimitive(boxesPrimitive)`. If the chart is rebuilt by [[chartpane_rebuildChart]], a brand new primitive is constructed and this method runs again on the new instance — the old instance is garbage by then.
