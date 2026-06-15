# Delivery audit — original 6-point price-range → dynamic SL/TP task

**Date:** 2026-06-15. Re-checked every outcome the original task stream asked for, against what exists on disk.
Triggered by: "review that task stream deeply and make sure you delivered all the outcomes required before
moving forward." The honest finding: **points 1 and 2 were computed *inside* the per-bar feature builder but
never emitted as the registry TABLES the task explicitly asked for** — now fixed with `range_registry.py`.

## The 6 points → status → artifact

| # | Original requirement | Status | Artifact |
|---|---|:--:|---|
| **1** | Register the **highest & lowest price point** for **each month / quarter / year** across 2024/2025/2026 | ✅ **delivered** | `range_registry.py` → `results/registry_{month,quarter,year}.csv` + `results/REGISTRY_TABLES.md` (true 1-min intrabar extremes + the timestamp of each extreme) |
| **2** | Assign a **NEW vs REPEATED** signal to each range | ✅ **delivered** | same; columns `signal`, `band_id`, `repeat_count` + `results/band_registry_{tf}.csv` |
| 2a | Merge ranges within a tolerance (bigger swallows smaller); log the value per record | ✅ | merge `margin = pct·price` (Q2a-approved % basis, default 5% ≈ 1k @ 20k), logged per period as `margin_pts`; union-on-merge |
| 2b | A range farther than the tolerance = a **different** range | ✅ | new band created when neither top nor bottom is within `margin` |
| 2c | Each range counted once, then **repeats over months (not necessarily in sequence)** | ✅ | `band_registry_*.csv` lists each distinct band, `times_seen`, and the exact (non-contiguous) periods — e.g. monthly band 2 recurs 2024-06, -07, -09 **and** 2025-03 |
| 2d | Announce a **new high / new low** | ✅ | `signal ∈ {NEW_HIGH, NEW_LOW, NEW_RANGE, REPEAT}` (NEW_HIGH/LOW = broke all prior territory + margin) |
| **3** | Look back, label **LOW_TREND / HIGH_TREND** (look-back, not forward) | ✅ **delivered** | registry `trend` column (period-level, descriptive) **and** `regime_features.py` `*_trend` (per-bar, causal — the version that feeds trades) |
| **4** | Rules: high-trend+long→widen TP, low-trend+short→widen TP, opposite→shrink; pin SL vs both dynamic | ✅ **studied & validated** | `regime_eval.py` (full grid) + `regime_validate.py` (6-fold). **Robust winner: trend-follow · pinned-SL · widen-only (W1.25/S1.0)** — beats fixed 6/6 (M), 5/6 (Q) folds. `STUDY_range_regime.md` |
| **5** | Split long vs short SL/TP | ✅ **threaded + swept** | engine E1 + **E2** (`fast_engine`/`core`/`optimizer`/`build_payload`, golden 6/6) + **Q1 sweep** (`split_sltp_sweep.py` → no asymmetric edge; symmetric champion wins) + `REPORT_Q1_split_sltp.md`. Definitive free search pinned as wsh5 (task #217) |
| **6** | Make SL/TP **dynamic to price change** | ✅ **studied** | regime rule (point 4) + `STUDY_cross_year_scale.md` (cross-year scale: prize is real **+$27k/−58% DD** but **not** causally recoverable by vol-linkage or recency → robust path = periodic full re-optimization) |

## What is still OPEN (honest list)

1. **Point 5 — split long/short SL/TP not yet *evaluated*.** The engine supports it and it's golden-safe, but the
   `× {shared | split}` arm of the S3 grid (action plan §Phase S) was deferred to the `wsh5` joint optimizer run.
   No standalone split sweep exists yet.
2. **`regime_charts.py` (S2) — retrospective visual ribbon** — ✅ **DONE** (`chart_regime_ribbon.png`,
   `chart_structure_swings.png`, `chart_period_bands.png`).
3. **Phase E2 — thread split SL/TP through `fast_engine` + `optimize/core` + the optimizer search space** + the
   fast-vs-exact parity test T4 — ✅ **DONE** (`UPDATE_E2_split_threading.md`; golden 6/6, T4 parity green). A
   `wsh5` run can now search the split space via `split_sltp=True`.
4. **Trend semantics note.** The registry `trend` (point 3) uses pure recency of the last broken extreme; the
   causal `regime_features.py` adds a current-price confirmation. They agree in spirit; `regime_features.py` is
   the authority for anything that touches a trade. 2024–26 is a near-continuous uptrend, so most periods label
   HIGH_TREND — a single-regime caveat already flagged in `STUDY_range_regime.md`.

## Headline results (so the registry connects to the goal)

- **Point 1 in one line:** NQ ran 16,334 (05-Jan-2024) → 29,782 (14-May-2026); yearly highs 22,426 / 26,399 /
  29,782. Quarterly/monthly tables in `REGISTRY_TABLES.md`.
- **Point 4 (the actionable edge):** *trend-follow · pinned-SL · widen-only* is the only rule that survived
  multi-fold validation — modest, era-caveated, needs `wsh5` before adoption.
- **Point 6 (the big lever):** SL/TP scale must adapt across eras (+$27k / −58% DD vs fixed), but **no causal
  formula recovers it** — periodic full re-optimization is the robust mechanism, not a price/vol scaling rule.

## Reproduce
`python3 study_range_regime/range_registry.py --pct 0.05` → registry + band CSVs + `REGISTRY_TABLES.md`.
