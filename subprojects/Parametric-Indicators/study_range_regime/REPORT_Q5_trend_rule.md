# Report Q5 — registry TREND switched to relative HH/LL (new/repeat unchanged)

**Date:** 2026-06-15. **Your rule:** *"down-trend (low trend) should follow the LL and up-trend (high trend)
should follow the HH; but the new/repeat counter stays the same — it must be an entirely NEW lowest/highest
price ever since we started watching."*

## What changed (one column only)
- **TREND** (`range_registry.py`) is now **relative, period-over-period**:
  - `HIGH_TREND` ⇐ this period's high **> the prior period's high** (a Higher High);
  - `LOW_TREND` ⇐ this period's low **< the prior period's low** (a Lower Low);
  - outside bar (both HH and LL) or inside bar (neither) → `NEUTRAL`; first period → `NEUTRAL`.
- **new/repeat signal is UNCHANGED** — still anchored to the **cumulative all-time record**: `NEW_HIGH` = a high
  above every prior period's high (+margin), `NEW_LOW` = a low below every prior low (−margin), else
  `NEW_RANGE`/`REPEAT`. (So `NEW_LOW` is still 0 over the 2024–26 up-only market — that part is *meant* to stay
  strict.)

## Before → after (why LOW_TREND now exists)
The old trend was anchored on the cumulative record (same basis as new/repeat) → since price never made a new
all-time low, `LOW_TREND` could never fire. The new relative basis reacts to ordinary pullbacks:

| granularity | OLD trend (cumulative) | NEW trend (relative HH/LL) |
|---|---|---|
| month   | HIGH_TREND 23 · NEUTRAL 6 · **LOW_TREND 0** | HIGH_TREND 18 · **LOW_TREND 8** · NEUTRAL 3 |
| quarter | HIGH_TREND 8 · NEUTRAL 2 · **LOW_TREND 0**  | HIGH_TREND 6 · **LOW_TREND 2** · NEUTRAL 2 |
| year    | HIGH_TREND 1 · NEUTRAL 2 · **LOW_TREND 0**  | HIGH_TREND 2 · NEUTRAL 1 (no yearly LL — each year's low ≥ prior) |

Examples now correctly flagged `LOW_TREND`: **2024-04** (low 17,113 < 2024-03's 17,832) and **2025-04** (low
16,460 < 2025-03's 18,976 — the April-2025 crash). These are real lower-low months that the old definition hid.

## Two trends now coexist (by design)
- **Registry `signal` (new/repeat)** = "are we in genuinely NEW all-time territory?" — strict, cumulative.
- **Registry `trend`** = "is the latest period extending up (HH) or down (LL) vs the previous one?" — relative.
- **Structure tables `label`** (LL/HL/HH/LH, `structure_tables.py`) = the same relative idea at the *swing*
  level on the 4h frame (153 LLs at swing_l=3) — finer-grained than the per-period registry trend.

## Scope note
This change is confined to the **registry tables** (`range_registry.py`), as you asked ("regenerate tables").
The causal per-bar `regime_features.py` (which fed the now-closed regime-rule study) keeps its own definition;
its results are frozen and not regenerated here. Reproduce: `python3 study_range_regime/range_registry.py`.
