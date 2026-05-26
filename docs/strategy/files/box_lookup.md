---
name: box_lookup
description: src/strategy/box_lookup.py — owns box CSV loading, NQ session mapping, and the nearest-unburned box selection
type: file
---

# box_lookup.py

Implements the **box source model** defined in [[strategy-master]] §1 and §2.2.

## Responsibilities

- **Load the 16-level CSV.** Reads `NQ_full_data.csv` (8 weekly + 8 monthly levels per date row).
- **NQ session mapping.** Maps each 4h candle to its session date using the **18:00 prev-day → 17:00 next-day** rule. Candles with hour ≥ 18 roll forward by one calendar day.
- **Nearest-unburned box selection.** Given a price + a direction bias (`up` looks at boxes **above**, `down` looks at boxes **below**), returns the closest **unburned** weekly-or-monthly level on the correct side. Burned levels (price has fully traversed them) are skipped.
- **Burn tracking.** Maintains per-session burn state so the same box is not re-selected after the candle has crossed both edges.
- **Nested-box detection.** Reports when price sits inside both a monthly and a weekly box simultaneously, so [[box_strategy]] can apply the nested-box edge rule per [[strategy-master]] §2.2.

## What it does **not** own

- The decision of which direction to look (that's in [[box_strategy]] from the truth table).
- The action taken when nested (HOLD vs weekly-only vs monthly-only — that's a config consumed by [[box_strategy]]).

## Input format

`NQ_full_data.csv` columns (per row, one date):

- Weekly: `WTHU`, `WTHD`, `WTH1`, `WTH2`, `WRHU`, `WRHD`, `WIHU`, `WIHD`, `WILU`, `WILD`, `WRLU`, `WRLD`, `WTLU`, `WTLD`, `WTL1`, `WTL2`
- Monthly: same shape with `M` prefix

Each level is a price; levels combine pairwise into 8 weekly + 8 monthly boxes (upper / lower edge per box).

## Key constants

- `tick_threshold = 0.75` — minimum box height for a level to be treated as a valid box.
