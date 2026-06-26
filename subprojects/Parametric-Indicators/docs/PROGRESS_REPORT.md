# Project Progress — Numerical Report

**Scope:** all tracked tasks since project start · **Generated:** 2026-06-25 (workstream 12 added
2026-06-26)

## Headline

| Status | Count | % |
|---|--:|--:|
| ✅ Done (completed) | 183 | 96.8% |
| 🟡 In progress | 0 | 0.0% |
| ⏸️ On hold / backlog (pending) | 6 | 3.2% |
| **Total tracked** | **189** | 100% |
| 🔭 On the horizon (not yet ticketed) | ~5 | — |

## By phase / workstream

| # | Phase | Done | Backlog | Total |
|---|---|--:|--:|--:|
| 1 | Optimizer infra foundation (Optuna, schemas, SSE, persistence) | 9 | 0 | 9 |
| 2 | Backtester engine — dual-TF SL/TP, graphics docs, strategy spec | 19 | 0 | 19 |
| 3 | Box CSV — Stage 1 / Stage 2 generation | 12 | 0 | 12 |
| 4 | Forecasting research (Meta-Prophet, ARIMA/Darts/GARCH, WS-A…G) | 28 | 5 | 33 |
| 5 | Per-timeframe generalization (WS-H, 1m→4h) | 9 | 0 | 9 |
| 6 | Indicator engine (WS-I + revisions) | 16 | 0 | 16 |
| 7 | Multi-instrument export (WS-AS, 6 instruments) | 9 | 0 | 9 |
| 8 | Split SL/TP + optimizer algorithms + optimizer dashboard | 19 | 1 | 20 |
| 9 | Two-layer system (L2 + combined + unified 3-tab dashboard) | 21 | 0 | 21 |
| 10 | Strategy semantics + production hardening (flip, defaults, security, perf) | 10 | 0 | 10 |
| 11 | Observability (verbose logs, time-cap, candle taxonomy, totals) | 31 | 0 | 31 |
| | **Total** | **183** | **6** | **189** |

## ⏸️ Backlog (6 pending)

- **Forecasting models (5):** WS-B OHLC multi-target · WS-D flip/regime committee · WS-E Kalman family · WS-F instruments/data acquisition *(blocked on a user data source)* · WS-G/D per-bar flip schedule follow-up
- **Backtester (1):** Q6 step 2-3 — entry-placement policy + confirmation + focused study

## 🔭 Horizon (known, not yet ticketed)

- End-of-trading-day exit cap *(currently in design)*
- `cap_1min` / EOD cap into the optimizer search space
- Port verbose-logs + taxonomy + time-cap into the shareable bundles
- `wsh6` optimizer run *(user's call to launch)*
- Optimizer-dashboard deploy on the AMD server

## Workstream 12 — Two layers + time-cap + cold-start (2026-06-26)

**Milestone doc:** `docs/MILESTONE_two_layers_time_capped.md` (centerpiece) ·
**Spec results:** `docs/superpowers/specs/2026-06-25-optimizer-cap1min-search-design.md` →
`## Results (2026-06-26)` · **Optimizer map:** `docs/OPTIMIZER_MAP.md` (cap_1min + cold-start sections).

This workstream turned hold-time into a searched parameter, then discovered — and corrected — a seeding
bias in the warm-started global search.

- **Time-cap feature.** `cap_mode ∈ none|bars|eod` wired through **both** parity-locked engines
  (`engine.py` slow, `optimize/fast_engine.py` fast); golden 6/6 green; exit precedence
  hard-SL ▸ hard-TP ▸ soft-SL ▸ cap. `bars` = N traded 1-min bars; `eod` = end-of-trading-day exit
  (trading day 18→17; full days exit 15 min before close, partial at close).
- **`cap_1min` as a searched dimension** (L1 + L2; L1 non-split = **57 dims**); `recommended_trials =
  dims × 100`; warm-start seeds enqueued.
- **Cold-start discovery (headline).** Warm `wsh6` cap search (11,407 trials / 8,650 feasible) → "a cap
  only costs PnL". A **cold-start control** `wsh6cold` (`--no-warm-start`, 22,868 trials / 17,807
  feasible) found a moderate **`cap=448`** config the warm search skipped → exposed a mild **seeding
  bias** (warm-start is a floor, not a freeze).
- **wsh6cold verified + triple-confirmed.** Reproduced **$153,321 / $9,589 DD** to the cent; **beats the
  old champion on 2026 OOS** (+$2,459, payoff 1.32 vs 0.74, PF 2.02 vs 1.93). Cap is load-bearing
  (127/211 trades exit via TIME_CAP; same config uncapped = $114,438 / $18,755 DD). `wsh7` re-opt
  (24,237 trials warm-started from **both** peaks) converged back to the cold seed (trial #2) — unbeaten.
- **L2.** l2v3 (L2 on old L1) **overfit** (+$78,651 in-sample → −$6,651 OOS) → **not promoted**, L2 stays
  l2v2. **l2v4** (L2 cold-start on wsh6cold's 569 residuals) **RUNNING / pending**, OOS-gated.
- **Infra shipped.** `--l1-champion` flag; candidate-L1 disk cache (**406×** faster reload);
  `warm_start_seeds` enqueues old champ + cold winner; wsh6cold as side-by-side preset + L1-tab profile
  (`profiles/l1_profiles.json`); verified shareable bundle `shareable/wsh6cold_4h_backtester`.

### Status table

| item | state |
|---|---|
| Time-cap (`none\|bars\|eod`), both engines, golden 6/6 | ✅ done |
| `cap_1min` searched dimension (57 dims) | ✅ done |
| wsh6 warm cap search (11,407 / 8,650 feasible) | ✅ done — "cap only costs PnL" (seed-biased) |
| wsh6cold cold-start (22,868 / 17,807 feasible) → `cap=448` | ✅ done |
| wsh6cold verify $153,321/$9,589, OOS +$2,459, triple-confirm (wsh7) | ✅ done |
| Infra: `--l1-champion`, disk cache, seeds, preset/profile, bundle | ✅ done |
| l2v3 (L2 on old L1) | ❌ overfit → NOT promoted (L2 stays l2v2) |
| l2v4 (L2 cold-start on wsh6cold residuals) | 🟡 RUNNING / pending (OOS-gated) |
| Production default / parity anchors | unchanged (additive) |

**Commits:** `c831320` (preset + seed) · `617c610` (`--l1-champion`) · `5c5c67f` (L1 profile) ·
`c03ed8a` (disk cache).

## Notes

- "On hold" = `pending` tasks not currently being worked. Only one is hard-blocked (WS-F, awaiting a data source); the rest are deliberately deferred research branches.
- 0 in progress at the 2026-06-25 snapshot; workstream 12 (above) opened and largely closed on 2026-06-26, with **l2v4** the one live in-flight item.
- Counts are exact from the task tracker; horizon items are estimates and not part of the 189 total.
