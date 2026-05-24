---
name: boxes_renderer_draw
file: frontend/src/components/BoxesPrimitive.ts
signature: BoxesRenderer.draw(target: CanvasRenderingTarget2D) → void
responsibility: Paint every visible box rectangle onto the chart canvas. One pass: snap each box's time window to bar coordinates, resolve price-to-pixel for the edges, clip to canvas, fill + stroke + label.
related: [[boxes_snapBox]], [[fe_components_boxesprimitive]]
---

# `BoxesRenderer.draw`

The only method on `BoxesRenderer`. Called by Lightweight Charts on every frame the primitive needs to repaint.

## Per-frame setup

```ts
if (!this._chart || !this._series || this._boxes.length === 0) return;
if (this._barTimes.length === 0) return;

const timeScale = this._chart.timeScale();

target.useMediaCoordinateSpace(({ context, mediaSize }) => {
  const W = mediaSize.width;
  const H = mediaSize.height;
  // ... per-box loop
});
```

`useMediaCoordinateSpace` is LWC's contract for drawing in CSS pixels (not device pixels). The browser handles the DPR scaling.

## Per box

```
snap = snapBox(box, barTimes)
if snap is null: continue

# x coords
if snap.x1 === 'extend': x1 = -W
else                   : x1 = timeScale.timeToCoordinate(snap.x1)   # skip box if null
if snap.x2 === 'extend': x2 = W * 2
else                   : x2 = timeScale.timeToCoordinate(snap.x2)   # skip box if null

if x1 >= x2: continue          # degenerate

# y coords
y1Raw = series.priceToCoordinate(box.upper)
y2Raw = series.priceToCoordinate(box.lower)
if both null: continue
y1 = y1Raw ?? -H               # upper price off the top
y2 = y2Raw ?? H * 2             # lower price off the bottom
top    = min(y1, y2)
height = abs(y2 - y1)
if height < 1: continue

# clip to canvas
visLeft   = max(x1, 0)
visTop    = max(top, 0)
visRight  = min(x2, W)
visBottom = min(top + height, H)
if visRight <= visLeft or visBottom <= visTop: continue

# fill
fillStyle = box.fill_color
fillRect(visLeft, visTop, visRight - visLeft, visBottom - visTop)

# borders — upper + lower lines
strokeStyle = box.border_color
lineWidth   = 1
if box.timeframe === 'monthly': setLineDash([5, 3])     # dashed monthlies
draw line at `top`    if it is on canvas
draw line at `bottom` if it is on canvas

# label
if box width > 20 and label is on canvas:
  setLineDash([])
  font   = 'bold 9px monospace'
  fillStyle = box.border_color
  fillText(box.level, visLeft + 3, max(top + 11, visTop + 11))
```

## The off-chart coordinate trick

When `snapBox` returns `'extend'`:
- `x1 = -W` → the left edge of the rectangle is one canvas-width to the left of the viewport.
- `x2 = W * 2` → the right edge is one canvas-width to the right.

After the clip step (`max(x1, 0)`, `min(x2, W)`), the box renders flush against the canvas edge. The user sees a rectangle that runs all the way to the side of the chart, exactly the visual effect a real "extends past the data" box should have.

Same trick on the y axis: if a price is off-screen `priceToCoordinate` returns null, and we substitute `-H` or `H*2` so the rectangle gets clipped to the canvas instead of vanishing.

## Border lines: visibility-gated

```ts
if (top >= -1 && top <= H + 1) draw the upper border line
if (bottom >= -1 && bottom <= H + 1) draw the lower border line
```

Avoids spending paint cycles on lines that are off-canvas. The `±1` slack accommodates sub-pixel rounding.

## Label placement

The label gets drawn only if the visible box width is wider than 20 px (otherwise the label would overflow into the next box) and the top of the box hasn't scrolled fully out of view. The `max(top + 11, visTop + 11)` keeps the label inside the visible portion of the box even when the upper edge is off-canvas.

## What this function does NOT do

- It does not mutate the box list, the bar-times list, the chart, or the series.
- It does not log, warn, or throw — bad geometry is silently skipped. Upstream guarantees (validated columns in [[candles_from_df]], validated box geometry in BoxLookup) handle correctness; this renderer is the last line of defense and is robust to anything weird that slips through.
