---
name: signals-stage2-master
description: Top-level spec for Stage 2 — reverse-signal windows over the Stage 1 candle stream
type: master
---

# Stage 2 — reverse-signal extractor

Stage 2 reads the Stage 1 output ([[signals-master]]) and emits one row per **closed reverse-signal window**: a transition from `long → ... → short` or `short → ... → long`, ignoring intervening `hold` candles.

The output is per-window (not per-candle, not per-level-pair). See [[output_schema]] for the locked column list and [[reverse_signal_rule]] for the scan procedure.

---

## 1. Input

A Stage 1 CSV (`subprojects/signals/signals_{preset}.csv`). Stage 1 emits one row per (candle, active level pair); Stage 2 collapses to one row per **candle** before scanning.

### Candle-level state collapse

For each unique `datetime` in the Stage 1 stream:

```
candle_state =
    'long'  if any row for the candle has signal == 'long'
    'short' if any row for the candle has signal == 'short'
    'hold'  otherwise
```

The Stage 1 color rule guarantees a candle is never both long and short. If that invariant ever breaks, the collapser raises `ValueError`.

---

## 2. The reverse-signal rule

A reverse signal is two opposite candle-level states separated by zero or more holds. Same-state repeats **discard** the open anchor and restart.

Linear scan in `datetime` ASC order:

1. Skip leading holds until the first `long`/`short` candle → **anchor**.
2. For each next candle:
   - `hold` → continues the open window.
   - same state as anchor → **discard** the open window (emit nothing), the new candle becomes the new anchor.
   - opposite state → **close** the window, emit one row, the reverse candle becomes the next window's anchor.
3. At EOF: if a window is still open, drop it silently.

Adjacent windows **share the reverse candle**: it is the last of window N and the anchor of window N+1.

Full decision matrix: [[reverse_signal_rule]].

---

## 3. Output

One row per closed window. 21 columns, fixed order:

`first_datetime, first_open, first_high, first_low, first_close, first_signal, first_box_id, first_box_type, last_datetime, last_open, last_high, last_low, last_close, last_signal, last_box_id, last_box_type, window_high, window_low, tp, sl, holds_between`

- `window_high` = `max(high)` across all candles in the window inclusive.
- `window_low`  = `min(low)`  across all candles in the window inclusive.
- `tp` and `sl` are **direction-aware**, keyed to the anchor candle's color:
  - **green anchor** (`first_close > first_open`):  `tp = window_high − first_close`, `sl = first_close − window_low`
  - **red anchor**   (`first_close < first_open`):  `tp = first_close − window_low`,  `sl = window_high − first_close`
  - A doji anchor cannot occur — Stage 1's color rule makes any doji a `hold`.
  - Both quantities are non-negative by construction.
- `holds_between` = hold candles **strictly between** anchor and reverse (excludes both endpoints).
- `first_box_id` / `last_box_id` = the `box_id`s of the anchor / reverse candle's Stage 1 rows whose `signal` matches the candle's candle-level state, sorted alphabetically and joined with `;`. Hold-signal rows on the same candle are excluded.
- `first_box_type` / `last_box_type` = the **first 4 characters** of each `;`-separated component of the corresponding `*_box_id`, in the same order. Strips the date suffix to leave just the box label prefix (e.g. `M-IH_2025-01-02` → `M-IH`). `_sub` labels collapse into their non-sub siblings (`M-TH_sub` → `M-TH`).

Sort: `first_datetime` ASC.

Per-column semantics: [[output_schema]].

---

## 4. Files

```
subprojects/signals/stage2/
├── generate_stage2.py                 ← module + CLI
├── reverse_signals_full.csv           ← preset full
├── reverse_signals_2025.csv           ← preset 2025
├── reverse_signals_2026.csv           ← preset 2026
├── by_direction/
│   ├── long_to_short_full.csv         ← first_signal == 'long'
│   ├── long_to_short_2025.csv
│   ├── long_to_short_2026.csv
│   ├── short_to_long_full.csv         ← first_signal == 'short'
│   ├── short_to_long_2025.csv
│   └── short_to_long_2026.csv
├── tests/
│   ├── test_generate_stage2_synthetic.py
│   └── test_generate_stage2_real_data.py
├── plots/
│   └── scatter_tp_vs_sl.py            ← static matplotlib scatter (tp vs sl)
├── dashboard/
│   └── index.html                     ← interactive X/Y scatter viewer (see [[stage2_dashboard]])
└── docs/
    ├── MASTER.md                      ← this file
    ├── files/
    │   ├── generate_stage2.md
    │   ├── generate_stage2_synthetic.md
    │   ├── generate_stage2_real_data.md
    │   └── dashboard.md
    └── references/
        ├── reverse_signal_rule.md
        └── output_schema.md
```

Per-file references: [[generate_stage2]], [[generate_stage2_synthetic]], [[generate_stage2_real_data]].

---

## 5. Row counts (locked against `signals_full.csv`)

| Preset | Total windows | long → short | short → long |
|---|---|---|---|
| `full` | 370 | 185 | 185 |
| `2025` | 257 | 129 | 128 |
| `2026` | 112 | 56 | 56 |

The `full` figures are regression-locked in [[generate_stage2_real_data]]. The per-year preset figures are derivatives and not locked.

---

## 6. Interactive viewer

`dashboard/index.html` is a self-contained Plotly viewer over `reverse_signals_full.csv`. Two `<select>`s let the user pick any of the 21 columns as X and Y; points are colored green (long) / red (short) by `first_signal`. No backend, no build step, no Python — just open in a browser via a static HTTP server.

Run:

```
cd subprojects/signals/stage2
python3 -m http.server 8000
# open http://localhost:8000/dashboard/
```

Full reference: [[stage2_dashboard]]. Design spec: `docs/superpowers/specs/2026-05-25-stage2-scatter-dashboard-design.md`.

---

## 7. What Stage 2 does NOT do

- Modify Stage 1 code, tests, or outputs.
- Touch any main-project files (`src/`, `tests/`, `frontend/`, `docs/graphics/`).
- Interpret manageability of the generated values — that is Stage 3.
- Render charts or write graphics.

See `sub-projects-preprint.md` for the overall three-stage plan.
