# Stage 1.1 — next-signal rule (quick reference)

The complete procedure that produces `next_signals_{preset}.csv`. Sibling of `stage1_0_reverse_signals/rule_reference.md`.

## Decision matrix

| # | Anchor state | Next candle state | Action | Emit? |
|---|---|---|---|---|
| 1 | n/a   | leading `hold`        | skip                                            | no  |
| 2 | n/a   | first `long`/`short`  | becomes anchor                                  | no  |
| 3 | long  | hold                  | append to open window                           | no  |
| 4 | short | hold                  | append to open window                           | no  |
| 5 | long  | long                  | **close** window, emit row, candle becomes next anchor | **yes** |
| 6 | short | short                 | **close** window, emit row, candle becomes next anchor | **yes** |
| 7 | long  | short                 | **close** window, emit row, candle becomes next anchor | **yes** |
| 8 | short | long                  | **close** window, emit row, candle becomes next anchor | **yes** |
| 9 | long/short | EOF              | drop open window silently                       | no  |

The only delta vs. `stage1_0_reverse_signals` is rows 5 and 6: same-state transitions emit instead of discarding.

## Properties

- Every emitted row has `first_signal ∈ {long, short}` and `last_signal ∈ {long, short}`. **Not** required to be opposite.
- Every adjacent emitted-row pair shares an endpoint candle. No discard branches.
- **Strict superset of `stage1_0_reverse_signals`.** Filtering by `first_signal != last_signal` recovers the reverse-signal output exactly.

## Per-window outputs

For `[c_0 (anchor), ..., c_k (closer)]` — identical to `stage1_0_reverse_signals`:

```
window_high    = max(c_i.H for i in 0..k)
window_low     = min(c_i.L for i in 0..k)
holds_between  = count(c_i.state == hold for i in 1..k-1)

# Direction-aware tp / sl, keyed to ANCHOR color, independent of closer:
if c_0.C > c_0.O:     # green anchor
    tp = window_high − c_0.C
    sl = c_0.C − window_low
elif c_0.C < c_0.O:   # red anchor
    tp = c_0.C − window_low
    sl = window_high − c_0.C
```

## Pseudocode

```
i = 0
while i < n and candles[i].state == 'hold': i += 1
if i >= n: return []

anchor = i
i += 1
results = []

while i < n:
    s = candles[i].state
    if s == 'hold':
        i += 1
        continue
    results.append(emit_window(candles[anchor:i+1]))
    anchor = i               # shared endpoint, always
    i += 1
return results
```
