---
name: full-candles-pipeline
description: End-to-end data flow of the full-candles signal pipeline — from the raw OHLC candle CSV + box CSV through Stage 1 labelling to the three output files (all-signals, holds-dropped, reverse-signals) for every timeframe and preset
type: pipeline
---

# Full-Candles Pipeline — from first entry to three output files

This document traces a single timeframe's candle CSV all the way through to its
**three output artifacts**, naming every transformation, the exact rule applied,
and the schema of each file. It is the reference for `generate_full_candles.py`,
which reuses the frozen `generate_stage1.py` (Stage 1) and
`stage1_0_reverse_signals/generate_stage2.py` (Stage 2) code paths verbatim — so
this pipeline is **byte-identical** to the original 4h pipeline (verified: the
`NQ_4h` outputs match the committed originals exactly).

The pipeline is **timeframe-independent**. The only time-aware element is the
hour-based session roll (§2), which is identical for every bar length, so any
timeframe's candle CSV flows through unchanged. See [[full-candles-readme]].

---

## 0. The whole flow at a glance

```
          INPUT A: candle CSV                INPUT B: box CSV
       NQ_<TF>.csv  (per timeframe)     data/full_data/NQ_full_data.csv
   datetime,open,high,low,close,volume   one row per market date,
                 │                         up to 16 level-pairs/row
                 ▼                                   │
        ┌──────────────────┐                         │
        │ 1. load_data()   │  normalise headers,     │
        │    + year filter │  parse datetime,        │
        │   (preset split) │  keep year rows         │
        └──────────────────┘                         │
                 │                                    ▼
                 │                         ┌────────────────────┐
                 │                         │ index boxes by Date│
                 │                         └────────────────────┘
                 ▼                                    │
        ┌───────────────────────────────────────────────────────┐
        │ 2. candle → box-date map   (hour >= 18 → +1 day)        │
        │ 3. STAGE 1 RULE per (candle × active level-pair)        │
        │    color + touch + close-vs-edge → long / short / hold  │
        │    (generate_stage1._emit_rows)                         │
        └───────────────────────────────────────────────────────┘
                 │
                 ▼
   ╔═══════════════════════════════════╗
   ║ OUTPUT 1  all-signals             ║  signals_<TF>_<preset>.csv
   ║ one row per (candle, box), holds  ║  10 cols
   ╚═══════════════════════════════════╝
                 │
        ┌────────┴─────────┐
        ▼                  ▼
   filter signal       feed full stream
   ∈ {long,short}      (holds kept — they
        │               are allowed between
        ▼               window endpoints)
   ╔═══════════════════════════╗        │
   ║ OUTPUT 2 holds-dropped    ║        ▼
   ║ signals_<TF>_<preset>     ║   ┌──────────────────────────────────┐
   ║   _no_holds.csv           ║   │ 4. STAGE 2: collapse to 1 state   │
   ╚═══════════════════════════╝   │    per candle, scan reverse        │
                                    │    windows (long→…→short / …)      │
                                    │    window_high = max high          │
                                    │    window_low  = min low           │
                                    │    tp/sl keyed to anchor color     │
                                    │    (generate_stage2.generate)      │
                                    └──────────────────────────────────┘
                                                  │
                          ┌───────────────────────┼───────────────────────┐
                          ▼                                               ▼
              ╔═══════════════════════════╗            by_direction/long_to_short_<TF>_<preset>.csv
              ║ OUTPUT 3 reverse-signals  ║            by_direction/short_to_long_<TF>_<preset>.csv
              ║ reverse_signals_<TF>_     ║            (OUTPUT 3 split by first_signal)
              ║   <preset>.csv  (21 cols) ║
              ╚═══════════════════════════╝
```

Run for every timeframe ∈ {1m, 2m, 5m, 15m, 1h, 2h, 4h} × preset ∈ {full, 2025, 2026}.

---

## 1. Inputs and loading

### Input A — candle CSV (per timeframe)
`Full_Canldes_Data/.../NQ_<TF>.csv`, columns:

```
datetime, open, high, low, close, volume
2025-01-01 18:00:00, 21269.0, 21333.0, 21121.75, 21322.25, 32778
```

`src.data.loader.load_data()` strips/normalises headers (lowercase→Title case,
`datetime`→`Date`) and parses `Date` to real timestamps. Format is timeframe-free:
the same loader handles 1m through 4h.

### Input B — box CSV (shared by all timeframes)
`data/full_data/NQ_full_data.csv` — **one row per market date**, not one row per
box. Each date row carries up to **16 candidate level-pairs** (8 weekly + 8
monthly labels: `W-TH`, `W-RH`, `W-IH`, `W-IL`, `W-RL`, `W-TL`, the `sub`
variants, and the monthly `M-*` equivalents). A level-pair is **active** on a
date only when both its upper and lower columns are non-NaN. The exact
`(upper_col, lower_col, label)` triples are imported directly from
`src.strategy.box_lookup._WEEKLY_LEVELS + _MONTHLY_LEVELS`, so Stage 1 and the
live engine can never drift. Boxes are date-keyed, hence **shared unchanged across
every timeframe**.

### Preset split (causality-free, calendar-year)
The candle stream is filtered by **calendar year** before Stage 1:
- `full` → all candles
- `2025` → candles with `Date.year == 2025`
- `2026` → candles with `Date.year == 2026`

This reproduces the original per-year input files exactly: `2025 rows ⊎ 2026 rows
= full rows`. Stage 2 then runs **independently per preset**, so a reverse window
straddling the year boundary appears only in `full` (this is why `full` has one
more 4h reverse window than `2025 + 2026`: 372 vs 253 + 118 = 371).

---

## 2. Candle → box-date mapping

Each candle is mapped to the box-date row whose levels it should be tested
against, using the NQ session rule (`BoxLookup._candle_to_box_date`):

```
candle.hour >= 18  →  box_date = candle.date + 1 day     # post-18:00 belongs to next session
candle.hour <  18  →  box_date = candle.date
```

This is **hour-based**, so it is identical for every timeframe — the only reason
the whole pipeline is timeframe-agnostic.

---

## 3. Stage 1 rule → OUTPUT 1 (all-signals)

For each candle, for each **active** level-pair on its mapped box-date row, emit
one row labelled by this rule (`generate_stage1._emit_rows`):

```
color   = green if close > open ; red if close < open ; none if close == open (doji)
touched = (low <= box_upper) AND (high >= box_lower)        # inclusive overlap

if   not touched:                       signal = hold
elif color == green and close > box_upper: signal = long    # strict break above
elif color == red   and close < box_lower: signal = short   # strict break below
else:                                    signal = hold
```

Rule properties: touch is **inclusive** (`<=`/`>=`); close-vs-edge is **strict**
(`>`/`<`, so a close *on* the edge is `hold`); a **doji is always `hold`**. Full
matrix in [[truth_table]].

**Row fan-out:** a candle whose box-date row has K active level-pairs emits K rows
(rule applied independently per pair). A candle with no active pairs emits **one**
`hold` row with empty box columns. So every candle yields ≥ 1 row.

**Ordering:** `datetime ASC`, then `box_upper DESC`, then `box_lower DESC`, NaN
last (stable mergesort → deterministic).

### OUTPUT 1 schema — `signals_<TF>_<preset>.csv` (10 columns)

| Column | Type | Meaning |
|---|---|---|
| `datetime` | ISO-8601 | candle timestamp |
| `open` `high` `low` `close` | float | candle OHLC |
| `volume` | int | candle volume |
| `signal` | `long`/`short`/`hold` | the Stage 1 label |
| `box_id` | str | `{label}_{box_date}`, e.g. `W-RH_2025-01-15`; empty when no box |
| `box_upper` `box_lower` | float | the level-pair edges; empty when no box |

---

## 4. Holds-dropped filter → OUTPUT 2

A pure view of OUTPUT 1: keep rows where `signal ∈ {long, short}`, drop every
`hold`. Same 10 columns, same order. This is the "only short/long" mirror.

### OUTPUT 2 — `no_holds/signals_<TF>_<preset>_no_holds.csv`
Identical schema to OUTPUT 1; row count = `long + short` of that preset.

---

## 5. Stage 2 → OUTPUT 3 (reverse-signals)

Stage 2 (`generate_stage2.generate`) consumes the **full** Stage 1 stream
(OUTPUT 1, *with* holds — holds are permitted *between* window endpoints) in two
steps:

**5a. Collapse to one state per candle.** Group OUTPUT 1 by `datetime`:
`candle_state = long` if any row is `long`, `short` if any is `short`, else
`hold`. (The color rule guarantees a candle can't be both.) Matching `box_id`s are
collected into `state_box_ids`.

**5b. Scan for reverse windows.** Linearly walk the candle-state stream. A window
opens at a non-hold **anchor** and closes at the next **opposite** state
(long→…→short or short→…→long), with holds allowed in between; a same-state repeat
restarts the anchor. For each closed window:

```
window_high = max(high) over the window      # the "maximum high"
window_low  = min(low)  over the window       # the "minimum low"

green anchor (close>open):  tp = window_high − first_close ;  sl = first_close − window_low
red   anchor (close<open):  tp = first_close − window_low  ;  sl = window_high − first_close
holds_between = count of hold candles strictly inside the window
```

The closing (reverse) candle becomes the next window's anchor. A trailing open
window with no reverse is dropped.

### OUTPUT 3 schema — `reverse_signals_<TF>_<preset>.csv` (21 columns)

| Group | Columns |
|---|---|
| anchor candle | `first_datetime, first_open, first_high, first_low, first_close, first_signal, first_box_id, first_box_type` |
| reverse candle | `last_datetime, last_open, last_high, last_low, last_close, last_signal, last_box_id, last_box_type` |
| window | `window_high, window_low` |
| risk | `tp, sl` |
| span | `holds_between` |

`*_box_type` strips the date suffix from each `;`-joined `box_id` component
(`M-IH_2025-01-02;W-RL_2025-01-02` → `M-IH;W-RL`). Sorted by `first_datetime`.

### OUTPUT 3 splits — `by_direction/`
The same rows partitioned by `first_signal`:
- `long_to_short_<TF>_<preset>.csv` — windows that opened `long`
- `short_to_long_<TF>_<preset>.csv` — windows that opened `short`

---

## 6. Determinism & verification

Same inputs + same code → byte-identical outputs (no timestamps, no machine paths,
stable sort). The pipeline was validated by diffing the regenerated `NQ_4h`
outputs against the committed originals:

| 4h preset | signals (long/short/hold) | no_holds | reverse windows |
|---|---|---|---|
| full | 20,322 (559/507/19,256) | 1,066 | 372 |
| 2025 | 14,662 (382/348/13,932) | 730 | 253 |
| 2026 | 5,660 (177/159/5,324) | 336 | 118 |

Both `signals_full.csv` and `reverse_signals_full.csv` came back **IDENTICAL**.
Per-(timeframe, preset) live counts for all seven timeframes are written to
`full_candles/SUMMARY.csv` on every run.

---

## 7. How to swap in any timeframe / instrument

Because the rule is pure OHLC-vs-box logic and the only time element is the
hour-based roll, you can drop in **any** candle CSV:

1. Format it as `datetime, open, high, low, close, volume` (lowercase is fine).
2. Ensure the box CSV's date range covers the candle dates.
3. Name it `NQ_<TF>.csv` in the data dir and add `<TF>` to `--timeframes` (or pass
   it explicitly). A non-NQ session boundary would require changing the one `>= 18`
   constant in `box_lookup`; for any NQ timeframe it is already correct.

---

## 8. Sub-document map

- [[full-candles-readme]] — folder layout + regenerate commands (`../README.md`).
- [[signals-master]] — frozen Stage 1 spec (`../../docs/MASTER.md`).
- [[truth_table]] — Stage 1 decision matrix (`../../truth_table.md`).
- Stage 2 spec — `../../stage1_0_reverse_signals/docs/MASTER.md`.
