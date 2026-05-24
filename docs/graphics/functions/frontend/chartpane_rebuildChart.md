---
name: chartpane_rebuildChart
file: frontend/src/components/ChartPane.vue
signature: rebuildChart() → Promise<void>
responsibility: Tear down and reinstantiate the chart while preserving the user's current visible range. Called when toggling a pane on/off (volume or RSI) because LWC's pane indices change and a clean rebuild is simpler than reshuffling.
related: [[chartpane_initChart]], [[fe_components_chartpane]]
---

# `rebuildChart`

A thin wrapper around `initChart()`. Snapshots the current visible range, rebuilds, restores it.

## Implementation

```ts
async function rebuildChart() {
  const range = chart?.timeScale().getVisibleLogicalRange() ?? null;
  initChart();                                // tears down + recreates
  if (range) {
    await nextTick();                         // wait for the new chart to size
    chart?.timeScale().setVisibleLogicalRange(range);
  }
}
```

## Why the rebuild

LWC v5 panes are indexed positionally. When the user toggles volume off, the RSI pane that was at index 2 has to move to index 1 — and `addSeries(..., paneIndex)` doesn't support live re-paneing. The fix is the surgical equivalent of "reload the page": rebuild the chart from scratch in [[chartpane_initChart]].

## Why `nextTick`

The newly created chart needs a tick to measure its container and compute the time scale's logical range. Calling `setVisibleLogicalRange` immediately after `initChart()` would set the range against an unmeasured chart and silently no-op. Awaiting `nextTick` lets the autoSize calculation run first.

## What this preserves vs loses

- ✓ Visible date / time range — the snapshot + restore guarantees this.
- ✗ User pan / zoom outside the new range — by construction, the restored range IS the new visible window, so panning state is replaced.
- ✗ Crosshair hover state — the new chart has a new crosshair listener, so `hoveredCandle` resets to null.

This trade-off is acceptable because pane toggles are infrequent (a user-driven settings change, not part of normal interaction).
