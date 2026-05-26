---
name: signals-stage1_1-master
description: Top-level spec for Stage 1.1 — next-signal windows over the Stage 1 candle stream
type: master
---

# Stage 1.1 — next-signal extractor

Stage 1.1 reads the Stage 1 output ([[signals-master]]) and emits one row per **closed next-signal window**: every transition from a non-hold candle (`long`/`short`) to the next non-hold candle, regardless of whether the second candle matches or opposes the anchor's direction. The intervening `hold` candles are skipped.

This subproject is a **sibling variant** of `stage1_0_reverse_signals`. Both consume the same Stage 1 CSV and write per-window rows in the same 21-column schema; only the windowing rule differs. The stage 1.1 rule is a **strict superset** of the stage 1.0 rule: every reverse-signal window is also a next-signal window.

---

## 1. Input

A Stage 1 CSV (`subprojects/signals/signals_{preset}.csv`). Stage 1 emits one row per (candle, active level pair); Stage 1.1 collapses to one row per **candle** before scanning.

### Candle-level state collapse

For each unique `datetime` in the Stage 1 stream:

```
candle_state =
    'long'  if any row for the candle has signal == 'long'
    'short' if any row for the candle has signal == 'short'
    'hold'  otherwise
```

The Stage 1 color rule guarantees a candle is never both long and short.

---

## 2. The next-signal rule

A next-signal window connects two non-hold candles separated by zero or more holds. **Same-state and opposite-state transitions both emit a window** — this is the only semantic difference from `stage1_0_reverse_signals`.

Linear scan in `datetime` ASC order:

1. Skip leading holds until the first `long`/`short` candle → **anchor**.
2. For each next candle:
   - `hold` → continues the open window.
   - `long` or `short` (any state) → **close** the window, emit one row, the closer becomes the next window's anchor.
3. At EOF: if a window is still open, drop it silently.

Adjacent windows **always share the closer candle**. Unlike stage 1.0 (which discards same-state runs), stage 1.1 has no discard branch.

Full decision matrix: [[next_signal_rule]].

---

## 3. Output

One row per closed window. 21 columns, identical to `stage1_0_reverse_signals`. `tp`/`sl` are direction-aware, keyed to the **anchor** candle's color, independent of the closer's signal.

### 3.1 Invariant differences from `stage1_0_reverse_signals`

| Invariant in stage 1.0 | Status in stage 1.1 |
|---|---|
| `first_signal != last_signal` on every row | **No longer holds.** Same-direction windows have equal endpoints. |
| Adjacent windows share endpoints when no discard fired | Always share (no discard branches). |
| 2 split files (`long_to_short`, `short_to_long`) | **4 split files** — all four pair classes. |

---

## 4. Row counts (locked against `signals_full.csv`)

| Preset | Total | long→long | long→short | short→long | short→short |
|---|---|---|---|---|---|
| `full` | 828 | 258 | 186 | 186 | 198 |
| `2025` | 567 | 178 | 127 | 126 | 136 |
| `2026` | 260 |  80 |  59 |  59 |  62 |

The `long→short` and `short→long` totals (186 each) **exactly match** `stage1_0_reverse_signals` — enforced by `test_anchor_direction_split_matches_stage1_0`.

---

## 5. Files

```
subprojects/signals/stage1_1_next_signal/
├── generate_stage2.py
├── next_signals_{full,2025,2026}.csv
├── by_direction/
│   ├── long_to_long_{preset}.csv
│   ├── long_to_short_{preset}.csv
│   ├── short_to_long_{preset}.csv
│   └── short_to_short_{preset}.csv
├── tests/
├── dashboard/index.html
└── docs/
```

---

## 6. Relationship to `stage1_0_reverse_signals`

Stage 1.1 is a strict superset: filter `first_signal != last_signal` to recover the stage 1.0 dataset exactly. Stage 1 itself (the per-candle producer) is shared.

See [[next_signal_rule]] for the formal decision matrix and soundness properties.
