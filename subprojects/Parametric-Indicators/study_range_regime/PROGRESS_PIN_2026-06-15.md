# PROGRESS PIN — 2026-06-15 (price-range regime → dynamic SL/TP, + handoff to the structure task)

A verbose snapshot of everything done in this workstream, so work can resume cleanly. Two threads:
**(A)** the price-range regime / dynamic-SL/TP study (now closed with a registry deliverable + a negative
dynamic-scaling result), and **(B)** the just-opened market-structure task (LL/HL/HH/LH tables + ICT
definition book).

---

## A. Price-range regime → dynamic SL/TP — STATE: study complete; 3 items open; nothing pushed

### A.1 What was built (all on branch `dev`, committed `fab7d72`…`5234c21`, **unpushed**)
- **Engine split SL/TP (E1)** — `engine.py`: optional `long_/short_ × sl_soft/sl_hard/tp_soft/tp_hard`
  fields; absent ⇒ byte-identical (golden 6/6 MATCH preserved). `UPDATE_engine_split_sltp.md` logs every line.
- **Engine TP-only multiplier (E1b)** — `tp_mult` per-bar array (pinned-SL widen/shrink).
- **Causal regime features (S1)** — `regime_features.py` → `results/regime_features.csv`: per-4h-bar
  running M/Q/Y extremes, %-price merge margin (logged), new/repeat, look-back trend, 3-TF agreement.
- **Rule-grid eval (S3)** — `regime_eval.py` → `results/regime_eval_ranked.csv`: {TF combo}×{mean_rev|
  trend_follow}×{pinned|both} swept, magnitudes TRAIN-fit, scored OOS vs fixed champion on return/DD.
- **Multi-fold validation (the gate)** — `regime_validate.py` → `results/regime_validate_folds.csv`:
  6 contiguous folds 2024–26.
- **Cross-year scale study** — `STUDY_cross_year_scale.md` + `cross_year_tables.py` →
  `results/cross_year_scale_sweep.csv`, `cross_year_q1_recovery.csv`, `cross_year_q2_compare.csv`,
  `cross_year_trailing_refit.csv`.
- **Price-range REGISTRY (S1b, NEW this session)** — `range_registry.py` →
  `results/registry_{month,quarter,year}.csv`, `results/band_registry_{…}.csv`, `results/REGISTRY_TABLES.md`.
  Delivers original task points 1–3 as explicit tables (true 1-min extremes + timestamps + new/repeat band
  machine + repeat counts + look-back trend). `DELIVERY_AUDIT.md` maps all 6 points → status.
- **Tests** — `tests/test_engine_split_sltp.py` (T2 degenerate==shared, T3 direction-consistency, T-valid).

### A.2 Findings (the answers)
- **Point-4 actionable edge:** *trend-follow · pinned-SL · widen-only (W1.25/S1.0)* is the ONLY rule that
  survived multi-fold validation — beats fixed in 6/6 (M) and 5/6 (Q) folds; modest, era-caveated
  (2024–26 largely trending), needs `wsh5` joint search before any adoption. The single-split "mean-rev·both"
  winner was overfit (2/6 folds).
- **Point-6 dynamic scaling:** the cross-year SL/TP scale-adaptation prize is REAL (+$27k P/L / −58% maxDD
  vs fixed) but **NOT causally capturable** — neither vol/range-linkage (q1 NO: 2026 inverts) nor recency/
  trailing-refit (LOSES $87k vs $142k) recovers the oracle scale. Robust mechanism = **periodic FULL
  re-optimization** on recent data (re-fits gate+indicators+SL/TP together), not a per-bar scaling formula.
- **Harness vs dashboard discrepancy (resolved):** the vol-gate percentile window differs — dashboard
  `build_payload(window="2024")` gates on isolated-2024 (threshold 99, 148 trades, $33,238); the regime
  harness gates over the whole 2024–26 series (looser, 187 trades). Dashboard path is canonical; S3/
  multi-fold absolute numbers are on the looser-gate basis.

### A.3 OPEN items (the 3 I owe an answer on — user is deferring this question)
1. **Point 5 — split long/short SL/TP not yet *evaluated*** (engine-enabled + golden-safe; the `{shared|
   split}` sweep deferred to `wsh5`).
2. **`regime_charts.py` (S2)** — retrospective visual ribbon (bands / new-highs / regime) — not built.
3. **Phase E2** — thread split SL/TP through `fast_engine`/`optimize.core`/optimizer search space + the
   fast-vs-exact parity test (T4) — needed before a `wsh5` run can search the split space.

### A.4 Hard constraints still in force
Commit/push ONLY when asked · never stage repo-root secrets (keypass.txt, login.txt, kw-full.ovpn,
SERVER_DETIALS.md) or pre-existing modified files (WS-I_RESULTS.md, *_wsi_pareto.png, .zip) · PG password
stays in `$WSI/pg.env` · fresh optimizer runs use NEW prefix `wsh5` · golden byte-match after every engine
change · verbose docs + revert steps · minimal-scope edits with approval gates.

---

## B. NEW TASK — market-structure tables (LL/HL/HH/LH) + ICT definition book — STATE: setup

**User ask (verbatim intent):** generate **low-low / high-high / low-high / high-low** tables; first verify
the supplied definitions against standard definitions, clarify ambiguities, build a **definition book**, then
a **plan**, then proceed. A large block of ICT/Smart-Money concepts was supplied (retrace, ADX/MACD/RSI/ATR/
EMA/SMA/RMA, FVG, IFVG, trend, key levels, LL/HL/HH/LH, order block, breaker block, CISD, golf candle, gap).

**What the project ALREADY implements** (`indicators/smc.py`, verified this session):
- `fvg(high, low)` — wick-based 3-candle Fair Value Gap (bull/bear + zone).
- `market_structure(close, swing_l)` — close-based fractal swing highs/lows (basis for LL/HL/HH/LH).
- `structure_trend(close, swing_l)` — +1 HH+HL uptrend / −1 LH+LL downtrend (carried forward).
- `order_blocks(...)` — last opposite-close candle before a structure break; converts to breaker once
  price closes beyond it (no longer usable as OB) — matches the user's "burned-into" rule.
- `golf_candle(...)` — N-candle ENGULFING (opposite colour to all N priors + wick-engulf + body ≥ 70% prior
  span). This is the user's "golf candle" (renamed engulfing in WS-I rev#2).
- classic indicators (ADX/MACD/RSI/ATR/EMA/SMA/RMA) in `indicators/classic.py`.

**What is MISSING / not yet explicit:**
- **LL/HL/HH/LH labeled tables** (the concrete new deliverable) — `market_structure` gives raw pivots but
  no per-swing classification table.
- **IFVG** (inverse FVG) — not a named detector.
- **Breaker block as a tradeable signal** — only the OB→breaker *retirement* exists, not a breaker entry.
- **CISD** (Change In State of Delivery) — absent.
- **Key levels** as a structure (partly covered by the price-range registry).

**Deliverables for task B:** `DEFINITION_BOOK.md` (user-def vs standard vs project-impl, ambiguities flagged),
`PLAN_structure_tables.md` (the LL/HL/HH/LH build), then `structure_tables.py` after the clarify gate.
**Gate:** clarify ambiguities with the user BEFORE building (brainstorming HARD-GATE + user's explicit "clarify
then create definition book then plan then proceed").

### B.UPDATE — STREAM COMPLETE (Q1/Q2/Q3/Q5/Q6 + task B all done)
Full detail in `REPORT_STREAM_2026-06-15.md`. Summary: structure detectors (swing_labels/ifvg/breaker/cisd)
built+tested; registry trend switched to relative HH/LL (Q5); split SL/TP threaded through fast_engine/core/
optimizer/build_payload (Q3, golden 6/6 + T4 parity); split sweep found no asymmetric edge (Q1, symmetric
champion wins) → wsh5 free search pinned (task #217); charts built (Q2); entry-rules plan written (Q6).
Open: task #217 (wsh5 split run) + `PLAN_entry_rules.md` (awaiting go-ahead).
