---
name: next_signal_rule
description: Linear-scan procedure for detecting next-signal windows over the candle-level stream
type: reference
---

# Next-signal rule

The exact scan procedure for closing next-signal windows. See [[signals-stage1_1-master]] §2 for the prose summary and [[generate_stage2]] for the implementation.

Contrast: the [[reverse_signal_rule]] in `stage1_0_reverse_signals` discards same-state transitions; this rule emits them.

## Procedure

```
i = 0
while i < n and stream[i].state == 'hold':
    i += 1
if i >= n: return

anchor = i
i += 1

while i < n:
    s = stream[i].state
    if s == 'hold':
        i += 1
        continue
    # any non-hold state — emit unconditionally
    emit_window(stream[anchor : i+1])
    anchor = i
    i += 1
```

## Decision matrix

| Anchor state | Current state | Action |
|---|---|---|
| long  | hold  | append to open window |
| long  | long  | **emit**, current becomes new anchor |
| long  | short | **emit**, current becomes new anchor |
| short | hold  | append to open window |
| short | short | **emit**, current becomes new anchor |
| short | long  | **emit**, current becomes new anchor |

Every non-hold candle either becomes the first anchor or closes exactly one window. No discard paths.

## Properties

- `first_signal` and `last_signal` are each `long` or `short`. **Not** required to be opposite.
- Every adjacent pair shares an endpoint (closer of N == anchor of N+1).
- **Strict superset of the reverse-signal rule.** Filter by `first_signal != last_signal` to recover the stage 1.0 dataset.

## Per-window aggregations

Identical to `stage1_0_reverse_signals`: `window_high`, `window_low`, `holds_between`, and direction-aware `tp`/`sl` keyed to the anchor's color. The change is purely in which windows get emitted, not how their quantities are computed.
