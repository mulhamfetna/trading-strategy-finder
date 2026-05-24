---
name: boxes_paneView_zOrder
file: frontend/src/components/BoxesPrimitive.ts
signature: BoxesPaneView.zOrder() → 'bottom' | 'normal' | 'top'
responsibility: LWC pane-view hook that pins the boxes layer to the bottom of the z stack so candles always draw on top of the rectangles. This is the single line of code that makes the chart visually layered correctly.
related: [[boxes_paneView_renderer]], [[fe_components_boxesprimitive]]
---

# `BoxesPaneView.zOrder`

Trivially implemented but crucial.

## Implementation

```ts
zOrder(): 'bottom' | 'normal' | 'top' {
  return 'bottom';
}
```

## Why `'bottom'`

Lightweight Charts' primitive plugin API allows three z-positions: bottom (below all series), normal (interleaved with series at the same pane index), top (above all series).

Boxes are visual context — they belong UNDER the price action so the user reads candles first, then sees the box context behind them. If this returned `'normal'` or `'top'`, the semi-transparent fill would tint the candle bodies and the candles' wicks would be visually broken by the box border lines.

Tested behaviour: with this set to `'bottom'`, hovering on a candle still produces the OHLC tooltip (LWC's hit testing isn't affected by primitive z-order).
