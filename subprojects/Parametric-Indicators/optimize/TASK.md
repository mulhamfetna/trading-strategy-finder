---
name: ws-h-multi-timeframe-parameter-search
description: WS-H — find the best (profit-vs-drawdown) parameter set per ENTRY timeframe (1m…4h) for the WS-G single-contract strategy, via NSGA-II Pareto search scored by walk-forward folds. Exits stay 1m; only the decision/opening candle varies. Cooldown capped per-TF by the realized-trade-gap (≤1 day) rule.
type: project
status: ready-to-start
created: 2026-06-03
---

# WS-H — Multi-Timeframe Entry-Frame Parameter Search

## 1. Goal
For **every available decision timeframe** TF ∈ {1m, 2m, 5m, 15m, 1h, 2h, 4h}, search for the
parameter set that delivers the **highest profit at the lowest drawdown** for the WS-G
single-contract strategy (box signal + volatility gate + drawdown breaker), and report the **full
profit-vs-drawdown Pareto front per timeframe** plus a cross-timeframe comparison.

## 2. The key reframe (locked with the user)
- **Exits stay on 1-minute, unchanged.** Every place that resolves an exit — SL-soft (2 consecutive
  1m closes), SL-hard (1m touch), TP (1m touch) — keeps reading the **1m** candles exactly as today.
- **Only the entry/opening candle is variable.** Every place that today reads the **4h** candle
  (box signal, entry timing, the volatility window) becomes a **placeholder decision timeframe**.
- SL/TP are therefore **absolute point distances** resolved on 1m → the same 40 pts means the same
  move regardless of which entry TF fired it (no cross-TF rescaling needed for comparability).
- 1 contract only, NQ, point value $20 (standing constraint — no scaling/ladder).

## 3. Decisions locked (this session)
| # | Decision | Choice |
|---|---|---|
| D1 | **Cooldown cap per TF** | **Realized-trade gap**: `cap_cooldown(TF) = floor(1 trading day ÷ median wall-clock gap between consecutive TAKEN trades)`. Sparse TFs (4h) → cap ≈ 0 ("can't cool down >1 day"); dense TFs → larger cap. The breaker's `cooldown` is searched in `[0, cap_cooldown(TF)]`. |
| D2 | **SL/TP search ranges** | **Per-TF point bounds**, derived from each TF's entry→exit move distribution (finer TFs get tighter ranges). Searched in raw points. |
| D3 | **Objective / selection** | **NSGA-II multi-objective** (maximise P/L, minimise maxDD) → return the **full Pareto front per TF**. No automatic winner; keep all trials. |
| D4 | **Validation** | **Walk-forward k-folds** (equal time-span, reuse `split_folds`). Per-trial score: **median fold P/L** + **worst-fold maxDD** (conservative). State reset between folds. |

## 4. Data sources (verified present)
- Entry frames (all 7): `Full_Canldes_Data/drive-download-*/NQ_{1m,2m,5m,15m,1h,2h,4h}.csv`.
- 1m exit frame: `data/<year>_data/NQ_1m_<year>.csv` (and `Full_Canldes_Data/.../NQ_1m.csv`).
- Box levels (shared, per-date): `data/full_data/NQ_full_data.csv`.
- Signal density (hold %, full preset): 1m 99.69% → 4h 94.76% hold; actionable/day ≈ 40+ (1m) → ~3 (4h).
  *(used to sanity-check the D1 cooldown caps, not as the cap itself)*

## 5. Engine generalization (the bulk of the build)
The WS-G clone (`subprojects/wsg-strategy/engine.py`, `volatility.py`, `strategy.py`, `loader.py`)
is hardcoded to 4h. Generalize the **decision frame only**:
1. `engine.py`: replace the `df_4h` decision dataframe with a generic `df_decision` of arbitrary bar
   duration; all entry/signal/timing reads use it. **Exit walk stays on `df_1min`** with the sub-bar
   window = `[bar_start, bar_start + bar_duration)`. Re-entry gate keyed on the *next decision bar*.
2. `volatility.py`: the realized-vol window becomes the **decision-bar duration** (placeholder, not
   hardcoded `+4h`); RV still computed from 1m closes inside each decision bar; HAR lookback stays in
   decision-bar units (1 / 6 / 30 bars).
3. `strategy.py` / `loader.py`: load the chosen entry-frame CSV by timeframe (not the hardcoded
   `NQ_4h_*`); keep 1m + box loaders.
4. **Regression lock:** with TF = 4h the generalized engine must reproduce the current winner
   **bit-for-bit** (+$7,735 / $3,670 maxDD / 66 trades) — a test guards this before any search runs.

## 6. Per-TF preparation
- **D1 cooldown cap:** per TF, run a fixed reference config (gate OFF, breaker OFF, one-position) to
  get the realized taken-trade timestamps → median inter-trade wall-clock gap → `cap_cooldown(TF)`.
  *(open sub-decision §9-a: reference config for cadence)*
- **D2 SL/TP bounds:** per TF, measure the entry→exit move distribution (signed/abs move over the 1m
  bars following each actionable entry) → set point bounds spanning ~[p10, p90] of plausible moves.

## 7. Search definition
- **Params searched:** `sl_soft` (pts), `sl_hard` (via `delta ≥ 0` so `sl_hard = sl_soft + delta`),
  `tp` (pts) — per-TF bounds from §6; `gate_pct ∈ [0,100]` (0 = off); `dd_limit ($) ∈ [0, 5000]`
  (0 = off); `cooldown ∈ [0, cap_cooldown(TF)]` (int); `flip ∈ {false, true}` (categorical).
- **Sampler:** Optuna `NSGAIISampler`, directions `[maximize P/L, maximize (−maxDD)]`.
- **Scoring (per trial):** walk-forward folds (D4) → objective vector `(median_fold_pnl,
  −worst_fold_maxDD)`; prune trials with too few trades/fold.
- **Persistence:** SQLite study per TF (resumable); store every trial + the Pareto front.

## 8. Deliverables
1. Timeframe-parametric WS-G engine + volatility (with the TF=4h parity regression test).
2. Per-TF cooldown-cap + SL/TP-bound derivation utilities (logged verbosely).
3. NSGA-II driver running all 7 timeframes (one study each), walk-forward scored.
4. Outputs: per-TF **Pareto front CSV + plot**, full trials DB, and a **cross-timeframe leaderboard**
   (best profit-at-given-DD regions per TF).
5. Report (`subprojects/wsg-strategy/optimize/reports/`) — best regions per TF, fold dispersion /
   overfit diagnostics, and an explicit honest caveat (still in-sample on one instrument).

## 9. Open sub-decisions (non-blocking; sensible defaults chosen, flag in report)
- **a.** Cooldown-cadence reference config (gate-off/breaker-off vs a mid-range config). *Default:*
  gate-off + breaker-off + one-position (densest realistic cadence).
- **b.** Fold count `k`. *Default:* 5 equal time-span folds (min 30 bars/fold enforced).
- **c.** Per-TF trial budget (population × generations). *Default:* scale by search-space size; start
  ~600 trials/TF, raise for fine TFs.
- **d.** maxDD aggregation across folds. *Default:* worst-fold (conservative).
- **e.** Include `flip`? *Default:* yes (categorical) — cheap and the project explored it.
- **f. PERFORMANCE (surfaced in H.3).** Volatility precompute is now vectorised (O(M log N); 1m
  loads in ~5s). But the **engine backtest loop** is still Python-per-decision-bar: ~6s (4h) →
  ~217s (5m) → minutes (1m) per single run. NSGA-II × hundreds of trials × fine TFs is infeasible
  as-is. *Plan for H.7:* (i) precompute the **param-independent** per-bar Stage-1 signal + box
  lookup once per TF (entry direction doesn't depend on SL/TP/gate/breaker), reused across trials;
  (ii) consider a vectorised exit pass; (iii) scale trial budget down for fine TFs; (iv) optionally
  run coarse TFs (4h…15m) first. *Note for H.3:* TF=1m realized vol degenerates (bar = 1m bar, ≤1
  intrabar return) → handled by accepting the single-bar |log-return|·close as the vol proxy.

## 10. Subtask checklist (the tracked WS-H.* items)
- [ ] **H.1** Generalize engine decision-frame (4h → placeholder TF); keep 1m exits; **TF=4h parity test**.
- [ ] **H.2** Generalize volatility window to decision-bar duration.
- [ ] **H.3** Per-TF entry-frame loaders for all 7 timeframes (+ shared 1m + box).
- [ ] **H.4** D1: per-TF cooldown-cap derivation (realized-trade-gap), logged.
- [ ] **H.5** D2: per-TF SL/TP point-bound derivation (move distribution), logged.
- [ ] **H.6** D4: walk-forward fold scoring wrapper (median P/L, worst maxDD, state reset).
- [ ] **H.7** D3: NSGA-II per-TF driver (Optuna), persist Pareto front + all trials.
- [ ] **H.8** Outputs: per-TF Pareto CSV + plots + cross-TF leaderboard.
- [ ] **H.9** Report + overfit diagnostics (fold dispersion; optional 2025→2026 holdout check).

## 11. Home / where it lives
**Everything lives inside `subprojects/wsg-strategy/optimize/`** — this task doc, the per-TF
derivation utilities, the NSGA-II driver, the SQLite studies, the Pareto outputs, and the report.
The generalized engine reuses (and minimally extends) the standalone's own `engine.py` /
`volatility.py` / `loader.py`. Nothing is written outside the subproject. The verified production
engine (`src/strategy/simple_strategy.py`) is **not** touched; only this standalone's parity-tested
clone is generalized.

## 12. Honest caveats (carried from prior workstreams)
- Still **in-sample on one instrument** (NQ, ~2025–2026). Walk-forward folds reduce but do not
  eliminate overfit; fine timeframes have far more trades (more data) but also more microstructure
  noise. Treat per-TF winners as *hypotheses*, not forward promises. See `notes/49` (breaker can
  delay but not hard-cap drawdown) and the n=1 caveat throughout.
