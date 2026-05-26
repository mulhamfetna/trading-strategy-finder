# Stage 1.1 — "next-signal" subproject — proposal & truth table

**Date:** 2026-05-26
**Status:** PROPOSAL — no code, no moves, no renames yet. Awaiting approval.

This document proposes (a) a directory restructure that turns the current Stage 1 / Stage 2 work into a versioned pair, and (b) a new variant subproject `stage1.1-next-signal` whose windowing rule differs from the current reverse-signal rule. It captures the new rule's truth table and contrasts it with the existing one so you can sign off before anything is touched.

---

## 1. The current state, in one diagram

```
subprojects/
└── signals/                        ← Stage 1: per-candle signal extractor
    ├── generate_stage1.py
    ├── signals_*.csv
    ├── tests/
    ├── docs/
    └── stage2/                     ← Stage 2: reverse-signal windows over Stage 1
        ├── generate_stage2.py
        ├── reverse_signals_*.csv
        ├── by_direction/
        ├── dashboard/
        ├── tests/
        └── docs/
```

The Stage 1 producer is generic ("here is the per-candle signal stream"). The Stage 2 consumer is opinionated ("collapse to reverse windows long↔short, discard same-direction runs"). The two are bundled in one tree because Stage 2 is the only consumer that exists today.

---

## 2. The proposed restructure

Rename the existing tree, then clone the Stage 2 layer (only) into a sibling sub-directory whose rule is "next signal" instead of "reverse signal". Stage 1 itself is **not** cloned — both variants consume the same Stage 1 CSV.

```
subprojects/
└── signals/
    ├── generate_stage1.py            ← unchanged producer
    ├── signals_*.csv                 ← unchanged outputs
    ├── tests/                        ← unchanged tests
    ├── docs/                         ← unchanged docs
    ├── stage1.0-reverse-signals/     ← was: stage2/   (rename only)
    │   ├── generate_stage1_0.py
    │   ├── reverse_signals_*.csv
    │   ├── by_direction/
    │   ├── dashboard/
    │   ├── tests/
    │   └── docs/
    └── stage1.1-next-signal/         ← NEW — clone of stage1.0 with new rule
        ├── generate_stage1_1.py
        ├── next_signals_*.csv
        ├── by_direction/
        ├── dashboard/
        ├── tests/
        └── docs/
```

> Naming clarification. The user's note reads `stage1.0 → stage1.0-reverse-signals` and `stage1.1 → stage1.1-next-signal`. The thing being versioned is the **windowing layer over Stage 1**, not Stage 1 itself. Stage 1 (the per-candle signal extractor at `subprojects/signals/`) stays as a single canonical module that both variants read. If you'd rather lift the windowing layer into a peer of `signals/` (e.g. `subprojects/windows-1.0-reverse/` and `subprojects/windows-1.1-next/`), say so — the proposal below assumes nesting under `signals/` to preserve the existing import path patterns.

Implications:

- The current `subprojects/signals/stage2/` becomes `subprojects/signals/stage1.0-reverse-signals/`. **Code-wise this is a rename only**; the rule is unchanged, so all 36 existing tests, the CSVs, the dashboard, and the locked counts (372 / 186 / 186) stay valid after a path search-and-replace.
- The new `subprojects/signals/stage1.1-next-signal/` is a **clone** of that tree with the rule patched to the next-signal variant. Outputs get a new column-compatible schema (with a single semantic difference — see §4.3).
- Imports change: `subprojects.signals.stage2` → `subprojects.signals.stage1_0_reverse_signals` (or pick a Python-legal slug; see §6 — Q1).

---

## 3. The current rule, restated tightly

`stage1.0-reverse-signals` is exactly the rule that lives in `generate_stage2.py` and `reverse_signal_rule.md` today. Reproduced for contrast:

```
Linear scan in datetime ASC order over the Stage 1 candle-level stream.

state machine (per scan):
  anchor ∈ {None, long, short}
  buffer ∈ list of holds since the anchor

per candle c in stream:
  s := c.candle_state ∈ {long, short, hold}

  case s == hold:
    if anchor is None: continue (skip leading hold)
    else: buffer.append(c)

  case s in {long, short} and anchor is None:
    anchor := c
    buffer := []

  case s == anchor.signal:                                  # ← SAME-direction
    DISCARD: anchor := c; buffer := []                       # restart with new anchor

  case s != anchor.signal:                                  # ← OPPOSITE direction
    EMIT window (anchor → c, holds_between = len(buffer))
    anchor := c                                              # the closer becomes the next anchor
    buffer := []

at EOF: drop any open anchor silently
```

Properties:

- Output windows always have `first_signal != last_signal`.
- Same-direction sequences are **swallowed** (`long → long → long → short` emits exactly one window, `long@first → short@last`).
- Adjacent windows share the reverse candle (last of N, anchor of N+1).
- 370 → 372 windows on the refreshed `full` preset, balanced 186/186.

---

## 4. The new rule — "next-signal"

### 4.1 Statement

```
Linear scan in datetime ASC order over the Stage 1 candle-level stream.

state machine (per scan):
  anchor ∈ {None, long, short}
  buffer ∈ list of holds since the anchor

per candle c in stream:
  s := c.candle_state ∈ {long, short, hold}

  case s == hold:
    if anchor is None: continue (skip leading hold)
    else: buffer.append(c)

  case s in {long, short} and anchor is None:
    anchor := c
    buffer := []

  case s in {long, short} and anchor is not None:           # ← BOTH same- and opposite-dir
    EMIT window (anchor → c, holds_between = len(buffer))
    anchor := c
    buffer := []

at EOF: drop any open anchor silently
```

The only difference: `s == anchor.signal` no longer discards — it **emits**. Every transition from one non-hold candle to the next non-hold candle (with any number of holds between) becomes one window.

### 4.2 Truth table — windowing decision matrix

`stage1.0-reverse-signals` for reference, `stage1.1-next-signal` proposed:

| anchor.signal | scanned candle state | stage1.0 action            | stage1.1 action            |
|---|---|---|---|
| `None`        | hold                 | skip                        | skip                        |
| `None`        | long                 | set anchor                  | set anchor                  |
| `None`        | short                | set anchor                  | set anchor                  |
| `long`        | hold                 | buffer.append               | buffer.append               |
| `long`        | long                 | **discard, re-anchor**      | **EMIT (long→long), re-anchor** |
| `long`        | short                | EMIT (long→short), re-anchor | EMIT (long→short), re-anchor |
| `short`       | hold                 | buffer.append               | buffer.append               |
| `short`       | short                | **discard, re-anchor**      | **EMIT (short→short), re-anchor** |
| `short`       | long                 | EMIT (short→long), re-anchor | EMIT (short→long), re-anchor |
| anchor open   | EOF                  | drop silently               | drop silently               |

The two highlighted rows are the entire semantic delta. Everything else is identical to `stage1.0`.

### 4.3 Output schema delta

The 21-column schema can be reused **as-is**. Only one invariant changes:

| Invariant in stage1.0 | Status in stage1.1 |
|---|---|
| `first_signal != last_signal` for every row | **No longer holds.** Same-direction windows have `first_signal == last_signal`. |
| `first_signal ∈ {long, short}`              | Still true. |
| `last_signal ∈ {long, short}`               | Still true. |
| Adjacent windows share the closer candle (`last_datetime[N] == first_datetime[N+1]`) | Still true. |
| Direction-aware tp/sl on the anchor          | Still applies — `tp/sl` keyed off the anchor's green/red colour, independent of the closer's signal. |
| `window_high` / `window_low` over the inclusive window | Still true. |

So the schema, the CSV format, the by-direction split (`long_to_long_*.csv`, `long_to_short_*.csv`, `short_to_long_*.csv`, `short_to_short_*.csv` — **4 split files, not 2**), and the dashboard all carry over with very small patches.

### 4.4 Predicted row counts (rough)

The new rule is a strict superset of the old. Predictions for the `full` preset:

- `stage1.0` windows: 372 (verified — 186 + 186)
- `stage1.1` windows: ≥ 372. Likely materially more — every swallowed same-direction sequence in stage1.0 (`long → long`, `short → short`) now becomes one or more windows. We won't know the exact count until the generator is written.

The four-way direction split should be near-balanced on long-vs-short anchors (186 vs 186 carry over) but the per-pair counts (`long→long`, `long→short`, etc.) are an open empirical question.

---

## 5. Logic-soundness analysis — does the new rule deserve approval?

Five properties worth checking before signing off:

| # | Property | Verdict |
|---|---|---|
| 1 | **Deterministic.** Same Stage 1 stream → same windows. | ✅ Yes — no randomness, no global state. |
| 2 | **Total over non-hold candles.** Every `long`/`short` candle that has a non-`None` predecessor anchor produces exactly one window edge. | ✅ Yes — every non-hold candle is either the first anchor or a closer of exactly one window. |
| 3 | **Non-overlapping windows (interior).** No candle appears as interior (non-endpoint) of two windows. | ✅ Yes — the buffer is reset on every emit. |
| 4 | **Shared endpoints between adjacent windows.** | ✅ Yes — preserved (the closer becomes the next anchor). |
| 5 | **Strict superset of stage1.0.** Every stage1.0 window is also a stage1.1 window. | ✅ Yes — the emit logic is the same on opposite-direction transitions; stage1.1 adds emits, never removes. |

A useful corollary: stage1.0 can be derived from stage1.1 by filtering `first_signal != last_signal`. The reverse is not possible. That's a clean argument for keeping both in the repo rather than replacing the old one.

### 5.1 Why this might be worth having

- **Bigger dataset for analysis.** ≥ 372 windows vs. exactly 372 — more rows for Stage 3 inspection and any downstream optimisation.
- **Captures continuation moves.** Same-direction "next-signal" windows expose how long price keeps going in the same direction before any reversal — which the reverse-signal rule discards entirely.
- **Symmetric coverage.** All four direction pairs are visible; the user gets a 2×2 picture instead of a 1×2.

### 5.2 Concerns worth naming

- **Naming.** "Stage 1.1" suggests a Stage 1 variant, but the change is at the windowing layer, not at the per-candle signal layer. See §6 — Q1.
- **Schema column name.** `first_signal`/`last_signal` are kept, but the implicit assumption "they're opposites" is gone. Any downstream consumer that assumed `last_signal = opposite(first_signal)` (none known) would silently break.
- **By-direction split file count** goes from 2 to 4. Dashboard defaults need to pick reasonable starting colour mapping (proposal: green/red by `first_signal`, same as stage1.0).
- **Test re-locks.** All 36 stage1.0 tests still apply after rename, no changes needed; stage1.1 needs its own real-data locks once the rule produces an output (a new regression-test fixture).

---

## 6. Open questions — please answer inline (`>>>` / `<<<`)

### Q1. Directory layout — keep nested or peer?

>>>
( a — keep nested under signals/  |  b — lift to peer of signals/  |  other )
<<<

### Q2. Python slug for the dotted name

Python imports cannot have `.` in module names. Options:

- `subprojects.signals.stage1_0_reverse_signals` / `stage1_1_next_signal` (underscored)
- `subprojects.signals.reverse_signals` / `next_signals` (drop the version, label by intent)
- Other?

>>>
( your pick )
<<<

### Q3. Do we keep the existing tests + CSVs verbatim under the renamed `stage1.0-reverse-signals/`?

Default = yes (rename only, no content edits). Confirm.

>>>
( yes / no — if no, what changes? )
<<<

### Q4. For `stage1.1-next-signal`, keep the same 21-column schema and direction-aware tp/sl?

>>>
( yes / no — if no, what changes? )
<<<

### Q5. Output naming

- `reverse_signals_{preset}.csv` carries over verbatim (stage1.0).
- For stage1.1: `next_signals_{preset}.csv` (recommended) / `signals_v1_1_{preset}.csv` / other?

>>>
( your pick )
<<<

### Q6. Direction-split file naming for stage1.1

Four pairs now exist:

- `long_to_long_{preset}.csv`
- `long_to_short_{preset}.csv`
- `short_to_long_{preset}.csv`
- `short_to_short_{preset}.csv`

Confirm naming and that all four should be emitted.

>>>
( your answer )
<<<

### Q7. Does Stage 1.1 ship with its own dashboard clone, or share the stage1.0 one with a dropdown for source CSV?

>>>
( own clone / shared with picker / no dashboard yet )
<<<

### Q8. Anything else to add or veto before I cut the move-plan?

>>>
( notes )
<<<

---

## 7. After approval — proposed execution order (no work happens until you say go)

1. Restructure-rename pass: `git mv subprojects/signals/stage2 subprojects/signals/stage1.0-reverse-signals` plus a search-replace of the import path. Run the 36 existing tests — they should pass untouched (and we lock 36/36 before moving on).
2. Sibling clone: `cp -r stage1.0-reverse-signals stage1.1-next-signal`, then patch:
   - `_OUT_PATH`, file names, module names
   - The single emit-discard branch in the rule (§4.1)
   - Real-data lock values (will be unknown until first run — we record once and lock)
3. Update both subprojects' `docs/MASTER.md` to point at each other under "Related".
4. Add a top-level `subprojects/signals/README.md` (one-screen) explaining the relationship.
5. Commit, no push until you say.

Total expected effort: small. The semantic delta is ~5 lines of code; the rest is structural.
