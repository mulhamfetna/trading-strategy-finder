# Plan — LL / HL / HH / LH market-structure tables (DRAFT, pending clarify gate)

Builds on `DEFINITION_BOOK.md`. Goal: emit the four swing-structure labels as registry-style tables, analogous
to `range_registry.py`. **Decision points marked `‹A#›` are settled by the clarify questions before coding.**

## Approach
1. **Detect swing pivots** — reuse `indicators/smc.py::market_structure(close, swing_l)` ‹A1 basis: close vs
   high/low› ‹A2 swing_l strength›. Pivots are causal (a pivot is confirmed `swing_l` bars later).
2. **Label each pivot** — compare each new swing high to the prior swing high → `HH`/`LH`; each new swing low to
   the prior swing low → `HL`/`LL`. (Exactly `structure_trend`'s internal comparison, now *emitted*.)
3. **Emit tables** ‹A3 shape›:
   - **Option (a)** one chronological table: `pivot_time, pivot_price, kind(high|low), label(HH|LH|HL|LL),
     prior_ref_price, delta, confirmed_at`.
   - **Option (b)** four separate tables (one per label).
   - **Option (c)** per-calendar-period (M/Q/Y) summary like the registry.
   I recommend **(a) + a small (c) summary** (chronological truth + a per-period count rollup), unless you prefer
   four separate files.
4. **Timeframe** ‹A3›: 4h decision frame (default, matches the regime study) — or 1-min / calendar like the
   registry. Source = `optimize.sub.data_2024_2026.load_bundle` (full 2024–2026).
5. **Outputs:** `study_range_regime/structure_tables.py` →
   `results/structure_swings.csv` (+ `results/structure_period_summary.csv` if (c)), and a
   `results/STRUCTURE_TABLES.md` with the rendered tables — mirroring the registry deliverable.
6. **Sanity checks:** every labeled high alternates with a labeled low (or note consecutive same-kind pivots);
   HH+HL runs should coincide with the registry's HIGH_TREND stretches (2024-07→2026); spot-check pivot prices
   against the registry extremes.

## Out of scope for this pass (documented in DEFINITION_BOOK for later) — unless ‹S› says otherwise
IFVG detector, tradeable breaker-block entry, CISD, OB entry-placement, retrace tuning. These get their own
plan after the tables land and the definitions are locked.

## Guardrails
Causal detectors only (no look-ahead — pivots confirmed `swing_l` bars later, stated per row) · reuse existing
`smc.py` (don't re-implement swings) · verbose doc + reproduce line · no engine/optimizer change (this is a
descriptive study, like the registry) · nothing committed/pushed until asked.
```
