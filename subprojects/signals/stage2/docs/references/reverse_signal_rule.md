---
name: reverse_signal_rule
description: Linear-scan procedure for detecting reverse-signal windows over the candle-level stream
type: reference
---

# Reverse-signal rule

The exact scan procedure for closing reverse-signal windows. See [[signals-stage2-master]] §2 for the prose summary and [[generate_stage2]] for the implementation.

---

## Input stream

A list of candles in `datetime` ASC order. Each candle has a `candle_state ∈ {long, short, hold}` derived per [[signals-stage2-master]] §1.

## Procedure

```
i = 0
while i < n and stream[i].state == 'hold':
    i += 1
if i >= n:
    return

anchor = i
i += 1

while i < n:
    s = stream[i].state
    if s == 'hold':
        i += 1
        continue
    if s == stream[anchor].state:
        anchor = i           # discard, restart
        i += 1
        continue
    # opposite state
    emit_window(stream[anchor : i+1])
    anchor = i               # shared endpoint
    i += 1
# EOF: drop unmatched open anchor (no output)
```

## Decision matrix

For the **current** candle's state, given the **anchor** candle's state:

| Anchor state | Current state | Action |
|---|---|---|
| long  | hold  | append to open window |
| long  | long  | **discard** open window, current becomes new anchor |
| long  | short | **emit** window `[anchor … current]`, current becomes new anchor |
| short | hold  | append to open window |
| short | short | **discard** open window, current becomes new anchor |
| short | long  | **emit** window `[anchor … current]`, current becomes new anchor |

## Properties

- Every emitted window has `first_signal ∈ {long, short}` and `last_signal == opposite(first_signal)`.
- Adjacent emitted windows **share their endpoint candle**: window N's last is window N+1's first.
- A discarded anchor produces **no output**. The data from that interval is lost from Stage 2's perspective.
- Leading holds (before any anchor) and trailing unmatched anchor (after EOF) produce no output.

## Per-window aggregations

For an emitted window `W = [c_0, c_1, ..., c_k]` (where `c_0` is anchor and `c_k` is reverse):

| Quantity | Formula |
|---|---|
| `window_high`   | `max(c_i.high for i in 0..k)` |
| `window_low`    | `min(c_i.low  for i in 0..k)` |
| `holds_between` | `count(c_i.state == 'hold' for i in 1..k-1)` |

### Direction-aware `tp` / `sl`

Keyed to the anchor candle's color (`c_0.close` vs `c_0.open`):

| Anchor color | `tp` | `sl` |
|---|---|---|
| **green** (`c_0.close > c_0.open`) | `window_high − c_0.close` | `c_0.close − window_low`  |
| **red**   (`c_0.close < c_0.open`) | `c_0.close − window_low`  | `window_high − c_0.close` |

A doji anchor (`c_0.close == c_0.open`) cannot occur — Stage 1's color rule guarantees doji candles are always `hold`. All four numeric quantities (`tp`, `sl`, `window_high`, `window_low` — minus the abs constraint) are non-negative under these formulas; `holds_between` is also ≥ 0.
