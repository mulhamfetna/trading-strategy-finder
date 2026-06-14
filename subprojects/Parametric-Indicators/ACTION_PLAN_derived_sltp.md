# Action Plan — Derived (self-recalibrating) SL/TP

**Date:** 2026-06-14 · **Status:** DESIGN APPROVED, awaiting plan sign-off · **Companions:**
`REVIEW_atr_sizing_contradiction.md`, `COUNCIL_RULING_atr_sizing.md`, `COUNCIL_RULING_reoptimization.md`,
`optimize/sub/STUDY_sub_optimizer_*.md`.

---

## 0. Goal (baby + precise)
Today's SL/TP are **fixed point values** (e.g. 149.8 / 167.1 / 120.2). They were optimal for the data they
were fit on; as price levels and volatility drift over the years they go stale and need re-optimizing.

**The idea:** stop storing an *absolute* number and instead express SL/TP as a **ratio to a live market
quantity** — `SL_points = k · D_t` — so there is no fixed number left to decay. As `D_t` (volatility/price)
moves over months and years, the points auto-rescale. That is the **robustness win** (primary goal). Any
out-of-sample *performance* gain over the fixed champion is a **bonus** (secondary) — we will not ship
anything that is worse than fixed.

This is NOT "throw manual values out of the system." The backtester keeps **both** a **Manual** mode (fixed
points, exactly as today) and a new **Auto** mode (fully derived, no manual base). Auto **replaces** the
current ATR-multiplier mode — but only *after* Auto is validated; the ATR mode stays in place during the
transition.

---

## 1. The model

### 1a. Approach A — the relative formula (the spine)
At each decision bar `t`, with a causal driver `D_t` in **price-points** (evaluated at the last-closed
1-minute bar — no look-ahead):
```
SL_soft(t) = k_sl_soft · D_t        TP_soft(t) = k_tp_soft · D_t
SL_hard(t) = k_sl_hard · D_t        TP_hard(t) = k_tp_hard · D_t
constraint: k_sl_hard ≥ k_sl_soft ≥ 0 , k_tp_hard ≥ k_tp_soft ≥ 0
```
- `D_t` = the **driver**, selected by the study among `{HAR-RV vf, ATR(240)@dec, %·price}` (all already
  computable; `vf` and the 1-min sampling exist in `runner.indicator_source_1min`).
- `k_*` = the only fitted numbers (dimensionless). Note: if the deployed champion uses a single TP line,
  `k_tp_soft == k_tp_hard` collapses to one coefficient — confirm against the live `StrategyParams` in Stage 1.
- Simpler than the ATR-multiplier it replaces: **no mean-normalization / no clip band** — `points = k·D_t`
  directly. (The R1 expanding-ref machinery was specific to the multiplier and is NOT carried into Auto.)

### 1b. Approach B — pluggable `SizingPolicy` (the seam)
A tiny interface so A→B is a *policy swap*, not an engine rewrite:
```
class SizingPolicy:  coeffs(t) -> (k_sl_soft, k_sl_hard, k_tp_soft, k_tp_hard)
  • ConstantPolicy(k...)      # Approach A: the 4 numbers the study fits
  • FittedPolicy(model, feats)# Approach B: k from a fit of market-state features → best-SL/TP,
                              #   trained on the rolling-window table, retrained on a trailing window
```
Same interface, same engine, same validation protocol for A and B.

---

## 2. Engine integration
- New `sltp_mode = 'relative'` (alongside existing `'fixed'` and `'atr'`). In the engine, set the per-bar
  base `points = policy.coeffs(t) · D_t` and feed the existing per-bar line machinery (reuse `engine.py`
  ~L450–457). **`'fixed'` stays byte-identical to all 6 golden baselines — hard parity gate.**
- `'atr'` (multiplier) mode: **left untouched** for now (removed in a later cleanup once Auto wins).

---

## 3. UI (dashboard `frontend/index.html`)
One parent group **"SL / TP"** with a **Manual / Auto** toggle (parent choice). **Two sub-boxes, both
always rendered for visual consistency**; the toggle **enables one and disables/greys the other**:
- **Manual sub-box:** `SL soft · SL hard · Take-profit` (today's inputs) — **disabled** when Auto is selected.
- **Auto sub-box:** `Driver` (vf / ATR(240) / %price) + `k_sl_soft · k_sl_hard · k_tp_soft · k_tp_hard`
  — **editable**, **defaulting to the study's best-fit values** (Stage 0 first, later `wsh5`). Disabled when
  Manual is selected.
- A read-out chart showing the **live SL/TP points** the Auto formula produces over time (replaces the
  multiplier chart while ATR mode is still present; both can coexist during transition).
- Reset/profile-load must set both sub-boxes coherently (extends the setForm defaults fix already in place).

---

## 4. Staged plan (each stage is an approval gate)

### Stage 0 — Feasibility (offline, cheap, NO engine change) → GO/NO-GO
On the existing 27-window `optimize/sub/results/subopt_table*.csv`:
- For each candidate driver `D ∈ {vf-proxy via harv_mean, atr_mean, price-based}`, compute the **ratio**
  `best_sl_soft/D`, `best_sl_hard/D`, `best_tp/D` per window and measure **stability across the 25 months**
  (CV / dispersion, trend, regime split). Stable ratio ⇒ the robustness thesis holds and yields rough `k`.
- Deliverable: `optimize/sub/feasibility_relative_sltp.py` + a short report (`STUDY_relative_feasibility.md`)
  with the per-driver stability verdict and the seed `k` values. **If no driver gives a stable ratio, STOP**
  and reconsider before any GPU spend.

### Stage 1 — Engine + UI (Manual/Auto, ConstantPolicy)
- `SizingPolicy` + `ConstantPolicy`; `sltp_mode='relative'` in `engine.py` (parity-guarded) and `strategy.py`
  (`validate_params` + `build_payload`); driver computation (causal, 1-min sampled).
- UI restructure (§3). Manual stays byte-identical; Auto defaults `k` to Stage-0 seeds.
- **Verify:** golden 6/6 byte-identical (fixed); Auto smoke vs champion on full + 2026; parity anchor
  (a degenerate `k·D ≡ champion points` config reproduces a known result).

### Stage 2 — Joint study `wsh5` (the real validation; honors the re-opt council)
- Fresh prefix **`wsh5`** (NSGA-III + Optuna, Postgres, walk-forward — NEVER reuse `wsh4`).
- **Search space (joint, two-sided — NOT pre-clamped):** `{driver, k_sl_soft, k_sl_hard, k_tp_soft,
  k_tp_hard}` ∪ optionally `{gate_pct, k-of-N}` so the rest of the strategy can adapt to the new risk profile.
- **Objective:** same multi-objective frame the champion was selected under (return AND drawdown), judged on
  **return/DD across folds**, not raw PnL.
- **Protocol:** causal features only; **multi-fold** walk-forward (not a single 2026 slice); frozen
  data/windows/seed/schema; parity anchor.
- **Pre-registered adopt rule:** adopt Auto only if a jointly-optimized point **OOS-dominates or matches**
  the fixed champion (≥ return AND ≤ DD) across folds. **Pilot on 4h first**; fan out to all TFs only if the
  4h probe at least matches fixed profit OOS. Otherwise keep fixed.

### Stage 3 — Approach B (FittedPolicy)
- Swap `ConstantPolicy` → `FittedPolicy` (ridge / shallow tree over the table features; retrain cadence =
  rolling 3-month). Re-validate through the **same** Stage-2 protocol and adopt rule.

### Stage 4 — Cleanup (only after Auto is adopted)
- Remove the ATR-multiplier mode + its now-unused clip/period/ref controls; update docs.

---

## 5. Validation & anti-overfit discipline (carried from both councils)
- Causal driver only (last-closed 1-min); no look-ahead anywhere.
- Multi-fold walk-forward; judge on **return/DD**, never raw PnL.
- Keep A's coefficient count tiny; B uses low-variance models + scheduled retrain.
- **Fixed champion remains the deployed default until something OOS-dominates it.**
- Every engine change re-runs the golden byte-match (fixed mode) as a hard gate.

## 6. Risks
- 27 label-windows is thin (esp. for Stage 3 ML) — mitigated by starting at A (≤4 params).
- "Best SL/TP per window" labels are in-sample optima — Stage 0 ratio-stability test is the honesty check.
- Driver = %price ignores vol regime; vf/ATR preferred — but the study chooses.
- Joint `wsh5` is GPU-expensive — gated behind Stage-0 GO and a 4h pilot before fan-out.

## 7. Revert / safety
- All work behind `sltp_mode`; `'fixed'` provably untouched (golden gate). Auto is default-OFF until adopted.
- ATR mode retained until Stage 4, so nothing is lost during the transition.
