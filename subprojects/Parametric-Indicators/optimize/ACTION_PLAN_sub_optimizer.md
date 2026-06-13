# Action Plan — SL/TP Sub-Optimizer + Dynamic SL/TP relationship (`sub_optimizer.md`)

**Date:** 2026-06-13 · branch `dev` · source spec: `/sub_optimizer.md`
**Status:** PLAN — not started. Approval-gated per step. Parity-locked to the frozen champion.
**Decisions captured (from clarification):** ① Stage-2 signal **HELD** — chosen from the Stage-1 table, not
now. ② Chunking = **rolling 3-month windows stepped monthly** (smoother optima). ③ Search bounds =
**widened (price-relative / 2–3×)**. ④ SL/TP coupling (shared vs independent multiplier) = **decided after
Stage 1**.

> Goal: discover how the best SL/TP move over time, then make SL/TP **dynamic** so they widen as the
> market's price/range widens (the premise: the strategy still wins on 2024 but needs *narrower* SL/TP back
> then because the range was smaller; the future range is wider).

---

## 0. Governing principles

1. **Freeze the champion; vary only SL/TP.** Pin every `wsi1m_4h` value (TF 4h · gate 86.9 · dd_limit 4747 ·
   cooldown 0 · flip off · k=1 · the 8 indicators + `gen` · dd_cap 5000 · pv 20). The sub-optimizer searches
   **only `sl_soft`, `sl_hard`, `tp`**.
2. **Compute the frozen layer ONCE.** Indicators/gate/signal are param-independent of SL/TP → compute the
   1-min votes + gate + Stage-1 signal over the FULL 29-month series a single time; each trial only re-runs
   the engine walk on the window slice. Fast + no per-window cold-start (warm-up comes from full context).
3. **Engine stays byte-identical.** Reuse `engine.SimpleStrategy` unchanged for Stage 1; Stage 2's dynamic
   application uses the existing `sl_tp_mult` hook (engine already supports it). No trade-math change in Stage 1.
4. **Approval-gated, documented, reversible.** One step = one commit = one `UPDATE_*` note. Stage 2 is a
   separate gate (held until Stage-1 results are reviewed).

---

## 1. Data & freeze inventory (verified)

| Item | Value |
|------|-------|
| Coverage | 2024 (full) + 2025 (full) + 2026 (Jan→May 19) via per-year files `data/{2024,2025,2026}_data/NQ_{4h,1m,full_data}_*.csv` |
| Months | 12 + 12 + 5 = **29** (2026 May partial) |
| Champion frozen | `wsi1m_4h`: sl 149.8 / 167.1 / tp 120.2 (to be replaced), gate 86.9, dd_limit 4747, cd 0, flip F, k1, 8 inds (sma_trend, keltner, obv, cci, mfi, bollinger, structure_trend, order_block), gen swing_l 10 |
| 2024 box | use the **shifted** `NQ_full_data_2024.csv` (the −1 BDay box already applied; not `.preshift.csv`) |
| Dynamic hook | `engine.SimpleStrategy.backtest(sl_tp_mult=…)` — per-4h-bar multiplier on all four SL/TP (1.0 = unchanged) |

---

## 2. STAGE 1 — per-window SL/TP sub-optimizer → results table  · RISK: MED

### 2.1 Build the 29-month bundle
- [ ] **S1.1** `optimize/sub/data_2024_2026.py` — concat the per-year 4h + 1m + box (2024+2025+2026) into one
      `(df4, df1, box, vf, month_index)` bundle, sorted/deduped, mirroring `strategy.load_inputs` but spanning
      3 years. HAR-RV `vf` computed over the **full** series (causal). Assert continuity (no gaps at year joins).

### 2.2 Freeze the champion layer once
- [ ] **S1.2** Compute, ONE time over the full series, with the champion params: the per-decision-bar
      **signal** (`decision_signals`), the **indicator votes** + **K-of-N gate / veto / entry-resolver mask**
      (`runner.build_layer`), and the **vol-gate threshold** = the champion's `gate_pct=86.9` percentile taken
      on the **full-history `vf`** (one fixed absolute threshold reused for every window — no per-window drift).
- [ ] **S1.3** Define the **rolling windows**: trailing 3 calendar months stepped by 1 month → ~27 windows
      (anchor = the window's last month; first anchor = month 3 = 2024-03, last = 2026-05). Each window = the
      decision-bar index range whose `Date` ∈ [anchor−2mo … anchor].

### 2.3 The sub-optimizer
- [ ] **S1.4** `optimize/sub/suboptimizer.py` — for each window: Optuna study searching ONLY
      `sl_soft ∈ B, sl_hard = sl_soft+δ, tp ∈ B` with **widened price-relative bounds** (S1.5); objective =
      **window P/L** with `dd_limit` breaker frozen on, **min-trades guard** (skip/flag windows with < N
      trades), DD ≤ `dd_cap` as a constraint. Each trial calls `engine.SimpleStrategy.backtest` on the window
      slice reusing the precomputed gate/resolver/votes (no indicator recompute). Store studies in Postgres
      (`WSH_STORAGE_URL`) under prefix `subopt_<anchor>` (one study per window) — reuses the Tier-1/3 infra.
- [ ] **S1.5** **Widened bounds:** start from `sl_tp_bounds.json` 4h lower bounds; raise the upper caps to
      `≈ base_cap × max(1, price_window / price_ref) × 1.0–1.5` (price-relative) and additionally allow up to
      ~2.5–3× the full-history cap, so high-price 2026 windows can reach wider SL/TP. Log when an optimum hits
      a bound (clip warning).

### 2.4 The results table (the Stage-1 deliverable)
- [ ] **S1.6** `optimize/sub/results/subopt_table.csv` — one row per window:
      `anchor_month, win_start, win_end, price_start, price_end, price_mean, atr_mean, harv_mean,
       best_sl_soft, best_sl_hard, best_tp, n_trades, pnl, max_dd, win_rate, sl_pct_of_price, tp_pct_of_price,
       bound_clipped`. (Price + ATR + HAR-RV columns are pre-staged so Stage 2 can fit against any of them —
       the *choice* of signal stays held.)
- [ ] **S1.7** `optimize/sub/REPORT_stage1.md` — verbose: method, the table, per-window plots
      (best SL/TP vs price, vs ATR, vs HAR-RV), trade-count caveats, bound-clip flags, and a plain-language read.

**Acceptance S1:** the table covers all valid windows; a known window reproduces via a direct
`build_payload` re-run (spot parity); bound-clips and low-trade windows flagged; no engine change (golden
6-TF still byte-identical).

---

## 3. STAGE 2 — fit the relationship + make SL/TP dynamic  · RISK: MED-HIGH · HELD until Stage-1 reviewed

> The **signal choice is deferred** to here (your call after seeing the table). Steps below are the menu.

- [ ] **S2.1** Exploratory fit on the Stage-1 table: regress `best_sl/tp` against candidate predictors
      (price level, ATR, HAR-RV, indicators) — report R²/stability for each; pick the predictor(s).
- [ ] **S2.2** Decide **coupling** (shared multiplier vs independent SL/TP) from whether SL & TP track the
      predictor the same way.
- [ ] **S2.3** Encode the relationship as a per-4h-bar `sl_tp_mult` (and, if independent, a small engine
      extension `sl_mult`/`tp_mult` — gated, parity-tested). Default base = the champion's SL/TP.
- [ ] **S2.4** **Walk-forward validation:** fit on 2024→mid-2025, test out-of-sample on the held-out tail;
      compare dynamic-SL/TP vs the fixed-SL/TP champion (P/L, DD, robustness). A relationship only ships if it
      beats fixed OOS.
- [ ] **S2.5** Report + (optional) dashboard toggle for dynamic SL/TP.

**Acceptance S2:** the dynamic rule beats the fixed champion **out-of-sample**; engine changes (if any)
parity-tested; documented + reversible.

---

## 4. Integration limitations & mitigations (the risks)

| # | Risk | Mitigation in this plan |
|---|------|--------------------------|
| 1 | Few trades/window → noisy optima | **rolling 3-month** windows (~3× trades) + min-trades guard + flag low-n windows |
| 2 | Full-history bounds clip recent-month optima | **widened price-relative bounds** (S1.5) + clip-warning column |
| 3 | `sl_tp_mult` is a single factor (SL & TP together) | coupling decided in S2.2; independent path = small gated engine extension (S2.3) |
| 4 | Per-window warm-up / gate drift | compute votes/gate over the **full series once**; gate threshold **frozen** to the champion's full-history percentile (S1.2) — no cold-start, no drift |
| 5 | DD-breaker state across window edges | each window backtested independently (documented); breaker frozen at champion `dd_limit` |
| 6 | "Price" ambiguity | table pre-stages price + ATR + HAR-RV; signal choice **held** to Stage 2 |
| 7 | 2026 May partial month | flagged in the table; treated as a short window |
| 8 | Overfit SL/TP per window | OOS walk-forward validation gate in S2.4 (ship only if it beats fixed) |

---

## 5. Files (new, isolated under `optimize/sub/`)
`data_2024_2026.py` · `suboptimizer.py` · `windows.py` (rolling-window indexer) · `results/subopt_table.csv` ·
`REPORT_stage1.md` · (Stage 2) `fit_relationship.py` · `UPDATE_*` notes. **No change** to `engine.py` /
`strategy.py` in Stage 1; any Stage-2 engine extension is gated + parity-tested.

---

## 6. Sequencing & gates
```
S1.1 bundle → S1.2 freeze-once → S1.3 windows → S1.4 sub-optimizer → S1.5 bounds → S1.6 table → S1.7 report
   [GATE: review the Stage-1 table with you — choose the Stage-2 signal + coupling]
S2.1 fit → S2.2 coupling → S2.3 encode (sl_tp_mult) → S2.4 OOS validation → S2.5 report/toggle
```
- Stage 1 is self-contained and runs on the server (Postgres infra already deployed) or locally (29-month
  1-min compute is modest; per-trial is just the engine walk).
- **Hard stop after S1.7** to review results before any Stage-2 modeling/engine change.

---

## 7. Open decisions (deferred by design)
- **Stage-2 signal** (price / volatility / indicators / ML) — pick from the Stage-1 table.
- **SL/TP coupling** (shared vs independent multiplier) — pick from the table.
- **Per-window objective detail** (pure P/L vs expectancy vs multi-objective) — default = P/L + DD≤cap +
  min-trades; confirm at S1.4.
