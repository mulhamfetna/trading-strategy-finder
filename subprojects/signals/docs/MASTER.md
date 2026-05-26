---
name: signals-master
description: Master specification for the Stage 1 signal extractor — per-(4h-candle, box) labelling of long / short / hold based on candle color, range touch, and close vs box edges
type: master
---

# Stage 1 Master Specification — signal-only dataset

This document is the single source of truth for what the Stage 1 signal extractor does. Stage 1 is part of an offline sub-project that lives entirely under `subprojects/signals/` and shares **no code or runtime state** with the main trading engine.

The full multi-stage roadmap (from `sub-projects-preprint.md`):

| Stage | Purpose |
|---|---|
| **1 (this doc)** | Label each (4h candle, box) pair as `long` / `short` / `hold`. No 1-min, no SL/TP, no trading. |
| **2 (future)** | Hunt for reverse-signal pairs and compute the max SL/TP that doesn't hit the opposite signal. |
| **3 (future)** | Inspect the Stage 2 output; if the SL/TP distances are manageable, use them — else design a strategy that copes. |

Stage 1 is **frozen** by the FINAL spec (formerly draft Round 5, now archived in this MASTER) and locked by 18 tests under `subprojects/signals/tests/`.

---

## 1. Inputs

Two CSVs per run, both from the dataset-preset layout introduced in the main project:

| Input | Path (full preset) | Source |
|---|---|---|
| 4h candles | `data/full_data/NQ_4h.csv` | NinjaTrader export, loaded via [[src-data-loader]] |
| Boxes (wide format) | `data/full_data/NQ_full_data.csv` | Unified box CSV (v4+), one row per market date |

The preset selector (`full`, `2025`, `2026`) picks which trio of files to read. Default preset is `2026`.

### Box CSV structure

The box CSV is **not** "one row per box". It is one row per market date with up to **16 candidate level pairs** per row:

- **8 weekly labels:** `W-TH`, `W-TH sub`, `W-RH`, `W-IH`, `W-IL`, `W-RL`, `W-TL`, `W-TL sub`
- **8 monthly labels:** `M-TH`, `M-TH sub`, `M-RH`, `M-IH`, `M-IL`, `M-RL`, `M-TL`, `M-TL sub`

Each label is encoded as two columns: an upper-edge column and a lower-edge column. A label is **active** on a date row when both of its columns are non-NaN. Many sub-labels (`W-TH sub`, etc.) are NaN on most dates.

The exact `(upper_col, lower_col, label)` triples come from `_WEEKLY_LEVELS + _MONTHLY_LEVELS` in [[box_lookup]] — Stage 1 imports those constants directly so the two systems can't drift.

### Candle → box-date mapping

Stage 1 uses the same NQ-session rule as the main engine:

```
candle.hour >= 18  →  box_date = candle.date + 1 day
candle.hour < 18   →  box_date = candle.date
```

This is the static method `BoxLookup._candle_to_box_date` in [[box_lookup]], imported and reused by Stage 1.

---

## 2. The rule

For each 4h candle, for each active level pair on the candle's mapped box-date row, evaluate:

```
candle_color:
    green if close > open
    red   if close < open
    none  if close == open    (doji)

touched:
    (low <= box_upper) AND (high >= box_lower)         # inclusive range overlap

if NOT touched:
    signal = hold
elif candle_color == green AND close > box_upper:
    signal = long
elif candle_color == red AND close < box_lower:
    signal = short
else:
    signal = hold
```

Three rule properties matter:

- **Touch is inclusive** at both edges (`<=` and `>=`). A wick sitting exactly on the box edge counts as a touch.
- **Close vs edge is strict** (`>` and `<`). A close sitting exactly on the upper or lower edge is `hold`.
- **Doji is always `hold`** — color is a required input and the rule has no third color.

Dual-touch (both high and low inside the box) is allowed; color decides which side of the rule applies. See [[truth_table]] for the full decision matrix.

---

## 3. Output

One CSV per preset, written to `subprojects/signals/signals_{preset}.csv`. Columns, in order:

```
datetime, open, high, low, close, volume, signal, box_id, box_upper, box_lower
```

| Column | Type | Notes |
|---|---|---|
| `datetime` | ISO-8601 string | from the 4h candle |
| `open`, `high`, `low`, `close` | float | from the 4h candle |
| `volume` | int | from the 4h candle |
| `signal` | `long` / `short` / `hold` | lowercase |
| `box_id` | string | composite `{label_with_underscores}_{box_date_iso}`, e.g. `W-RH_2025-01-15` or `W-TH_sub_2025-01-15`. NaN when no box overlaps the candle. |
| `box_upper`, `box_lower` | float | edges of the level pair. NaN when no box. |

See [[output_schema]] for column-by-column semantics.

### Row fan-out per candle

| Active level pairs on the candle's box-date row | Output rows |
|---|---|
| 0 (no row in box CSV, or every level pair is NaN) | 1 row, `signal=hold`, all box columns NaN |
| K ≥ 1 | K rows, one per active level pair, rule applied independently to each |

Realistic K on a typical 2025 candle: ~8–12. Every 4h candle in the preset produces **at least one row**.

### Row ordering

Primary: `datetime ASC`. Secondary: `box_upper DESC`. Tertiary (rare tiebreaker): `box_lower DESC`. NaN box values sort last.

### NaN representation

pandas default — empty cells in the CSV, restored as `NaN` when read back via `pd.read_csv`.

---

## 4. Determinism

Same input CSVs + same code → byte-identical output CSV. No timestamps in the output, no machine-specific paths, no dictionary-order ambiguities. The locked row count and signal distribution in [[generate_stage1]] §"Locked counts" depend on this property.

---

## 5. What Stage 1 is NOT

- It is **not** the main engine's signal logic. The main engine uses `BoxLookup.signal()` with its own traversal-state rule (above→inside→below = short, etc.). Stage 1 uses a much simpler color+touch+close rule.
- It does **not** call `BoxLookup.signal()`. It only reuses the level-pair constants and the date-mapping helper.
- It does **not** consume 1-minute candles, scaling parameters, SL/TP parameters, or any trading semantics.
- It does **not** produce trades — only labelled candle-box pairs.

---

## 6. Implementation status

| Concern | Status |
|---|---|
| CLI script | done — see [[generate_stage1]] |
| Synthetic tests (12) | passing |
| Real-data regression locks (6) | passing |
| Generated CSVs (full / 2025 / 2026) | written under `subprojects/signals/` |
| Stage 2 | not started; spec in `sub-projects-preprint.md` |

---

## 7. Sub-document map

- [[generate_stage1]] — the CLI script: arguments, data flow, locked output counts.
- [[truth_table]] — the full decision matrix in tabular form.
- [[output_schema]] — column-by-column semantics of `signals_{preset}.csv`.
