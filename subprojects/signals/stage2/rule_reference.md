# Stage 2 — reverse-signal rule (quick reference)

The complete procedure that produces `reverse_signals_{preset}.csv`. Parallel to `subprojects/signals/truth_table.md` for Stage 1.

## Input

Each row is one **candle** with a state ∈ `{long, short, hold}`, derived from Stage 1's per-(candle, level-pair) rows:

```
candle_state =
    long   if any Stage 1 row for the candle has signal == 'long'
    short  if any Stage 1 row for the candle has signal == 'short'
    hold   otherwise
```

## Symbols

| Symbol | Meaning |
|---|---|
| `c_i.O / H / L / C` | candle i's open / high / low / close |
| `anchor` | first non-hold candle of the open window |
| `reverse` | the candle that closes the open window with the opposite state |

## Decision matrix

| # | Anchor state | Next candle state | Action | Emit? |
|---|---|---|---|---|
| 1 | n/a | leading `hold` | skip | no |
| 2 | n/a | first `long` or `short` | becomes anchor | no |
| 3 | long | hold | append to open window | no |
| 4 | short | hold | append to open window | no |
| 5 | long | long | **discard** open window, candle becomes new anchor | no |
| 6 | short | short | **discard** open window, candle becomes new anchor | no |
| 7 | long | short | **close** window, emit row, candle becomes next anchor | **yes** |
| 8 | short | long | **close** window, emit row, candle becomes next anchor | **yes** |
| 9 | long/short | EOF | drop open window silently | no |

## Per-window outputs

For an emitted window `[c_0 (anchor), ..., c_k (reverse)]`:

```
window_high    = max(c_i.H for i in 0..k)
window_low     = min(c_i.L for i in 0..k)
holds_between  = count(c_i.state == hold for i in 1..k-1)  ≥ 0
first_box_id   = ';'.join(sorted(
                    row.box_id
                    for row in stage1_rows(c_0)
                    if row.signal == c_0.state
                 ))
last_box_id    = ';'.join(sorted(
                    row.box_id
                    for row in stage1_rows(c_k)
                    if row.signal == c_k.state
                 ))
first_box_type = ';'.join(part[:4] for part in first_box_id.split(';'))
last_box_type  = ';'.join(part[:4] for part in last_box_id.split(';'))
```

### Direction-aware tp / sl

Keyed to the anchor candle's color (`c_0.C` vs `c_0.O`):

```
if c_0.C > c_0.O:        # green anchor → long state
    tp = window_high − c_0.C
    sl = c_0.C − window_low
elif c_0.C < c_0.O:      # red anchor → short state
    tp = c_0.C − window_low
    sl = window_high − c_0.C
# c_0.C == c_0.O (doji) cannot happen — Stage 1 makes any doji 'hold'.
```

Both `tp` and `sl` are always ≥ 0 by construction.

## Properties

- Every emitted row has `first_signal` and `last_signal` opposite.
- Adjacent emitted rows usually share an endpoint candle (the reverse of row N is the anchor of row N+1).
- A `long → long` or `short → short` discard produces no output — that data is silently dropped from Stage 2's perspective.
- Leading holds and trailing unmatched anchors produce no output.

## Pseudocode

```
i = 0
n = len(candles)

# Skip leading holds.
while i < n and candles[i].state == 'hold':
    i += 1
if i >= n:
    return []

anchor = i
i += 1
results = []

while i < n:
    s = candles[i].state
    if s == 'hold':
        i += 1
        continue
    if s == candles[anchor].state:
        anchor = i           # discard, restart
        i += 1
        continue
    # opposite state
    results.append(emit_window(candles[anchor:i+1]))
    anchor = i               # shared endpoint
    i += 1

return results
```

This is the exact rule implemented in `_scan_windows` in `generate_stage2.py`.
