# Council Ruling — Do recent changes require RE-OPTIMIZATION?

**Convened 2026-06-14 · 6 expert lenses + chief adjudicator · companion to REVIEW_atr_sizing_contradiction.md / COUNCIL_RULING_atr_sizing.md**

# COUNCIL RULING — Re-Optimization Decision (ATR Sizing vs. Fixed Champion)

## 1. Final Verdict

**(a) Does the DEPLOYED FIXED champion need re-optimizing? — NO. Unanimous, high confidence.**
The champion (`wsi1m_4h` and per-TF siblings) runs in `sltp_mode='fixed'`, which is **byte-identical to all 6 golden baselines** and is verified inert in code: strategy.py line 330 sets `sl_tp_mult=None` unless `sltp_mode=='atr'` (line 332), and the optimizer (optimizer.py line 146) never emits an `sltp_mode`/`atr_*` key, so every wsh4 trial resolved to the fixed path. Re-optimization is triggered only when (i) the objective/data the champion was scored on changed, or (ii) the feasible set it lives in changed. **Neither happened.** Re-running wsh4 would reproduce the same champion while spending GPU-hours and re-incurring multiple-comparison/overfitting risk. Do nothing.

**(b) Does ADOPTING ATR sizing require a joint re-optimization? — YES, but only if you decide to adopt it. Unanimous: "only-if-adopting".**
The ATR multiplier `m_t = clip(a·ATR_t / expanding_mean(ATR)_t, lo, hi)` is a **genuinely new degree of freedom** that the wsh4 search space never contained (SL/TP were static points only). Because the band is shrink-only (≤1.05), the multiplier systematically reduces the effective SL/TP the base values (sl_soft=149.8, sl_hard=167.1, tp=120.2) were co-tuned for against the gate, dd-breaker, and K-of-N layer. The jointly-optimal `(base SL/TP + coefficient a + band)` point was **never searched** and cannot be assumed equal to `champion + a`. Do **not** adopt ATR sizing off the dashboard number or off the freeze-base study. If adoption is a goal, fund a fresh joint study (prefix `wsh5`).

## 2. Vote Tally

| Lens | fixed-needs-reopt | atr-needs-joint-reopt | Confidence |
|---|---|---|---|
| Optimization / search-space design | no | only-if-adopting | 0.86 |
| Statistician / overfitting & validation | no | only-if-adopting | 0.88 |
| Quant / production-risk & change-control | no | only-if-adopting | 0.86 |
| Software / systems & reproducibility | no | only-if-adopting | 0.90 |
| Pragmatic trading-desk / ROI | no | only-if-adopting | 0.78 |
| Devil's-advocate / experimental-design purist | no | only-if-adopting | 0.82 |
| **Consensus** | **no (6/6)** | **only-if-adopting (6/6)** | **mean 0.85** |

Zero dissent on either axis.

## 3. WITHIN Existing Conditions vs. NEW Search Space

**WITHIN the existing optimizer conditions (safe, NO re-opt required):**
- The deployed fixed champion in its entirety — box-trigger params, SL_soft/SL_hard/TP as fixed points, HAR-RV `gate_pct`, dd-breaker (`dd_limit`/cooldown), K-of-N confirm/veto, indicators, swing_l, flip. These are byte-identical to golden and live in exactly the static-sizing space they were searched in.
- **R1** (causal expanding-mean ATR ref), **R2** (source-keyed ATR period 4h→14 / 1m→240), **R3** (shrink-only 0.33–1.05 band) — all gated behind `if P['sltp_mode']=='atr'` (strategy.py ~330–353). They cannot execute on the fixed path, so they cannot move the fixed objective surface, the golden baselines, or the optimizer's objective.
- The **UI changes** (reset/defaults bugfix, resizable panel, wider inputs) — presentation layer only; no path into decision math or the optimizer.

**A NEW search space (the multiplier dimension the optimizer NEVER saw — re-opt required before adoption):**
- The multiplier coefficient `a`, the clip band edges `clip_lo`/`clip_hi`, `atr_source`, and `atr_period`.
- **Critically:** the base SL_soft/SL_hard/TP themselves *re-enter the search space* once the multiplier is active, because they were optimal only for `m≡1`. A per-bar, volatility-state-dependent rescaling of the very axes the base was tuned for is a **different parameter manifold**, not a re-point in the old one. None of these joint combinations were ever in wsh4.

## 4. The Key Insight — Why "No Edge" May Be Manufactured

The prior dynamic-SL/TP study **froze the champion's 12 base dimensions and fit only a single global scalar `a` on train**, then scored OOS — under a **shrink-only band** that, by construction, can only make stops/targets smaller and so **can never let ATR express upside**. This is a 1-dimensional line search through a ≥15-dimensional joint space, evaluated *at the old space's optimum* — a starting point with no reason to be near the new optimum.

That design **structurally biases toward the null**:
- With base params frozen at the fixed optimum, the only way `a` beats fixed is if a global rescale of already-optimal stops helps — a near-measure-zero event.
- The shrink-only clip removes the entire upside half of the dimension, so "DD-reducer only" is partly a property of the **clip**, not of ATR sizing. The council flagged this as "pre-rigging."
- The dossier's own evidence cuts both ways but supports the under-test reading: opt1 reduced DD by ~32% (ret/DD 5.61 vs 4.17) even in this worst-case crippled configuration, and a genuinely-held-out **expansion** config posted **+15% PnL** (bought with +34% DD, worse ret/DD) — proof that return *exists* in the space, rejected only because a 3× multiplier was bolted onto a base tuned for 1×.

**What this means for trusting "no edge":** the study cleanly answers *"does bolting one shrink-coefficient onto the frozen champion beat it?"* (answer: no on profit, yes on DD). It does **not** answer *"does any jointly-tuned sized config beat fixed on return/DD?"* (untested). The negative prior is informative about adding a lone coefficient — **not** about the unsearched joint optimum. Treat the study as a hypothesis filter, never as the adoption decision.

## 5. Decision Tree for the Operator

**Branch A — Keep deploying FIXED (default, recommended now):**
- Action: **nothing.** Ship the UI/bugfix changes; ship ATR as default-off experimental. The byte-identity verification *is* the validation; wsh4 studies and golden baselines remain authoritative.
- Lock first: formalize a **CI gate** asserting byte-identity to all 6 golden baselines with `sltp_mode` unset (keep `test_axisB_signal_equiv` + `test_speedopt_equiv` green at the launch commit), so any future edit that leaks into the fixed path fails loudly.

**Branch B — You want lower drawdown only (no profit claim):**
- Action: ship the study-sanctioned **shrink-only HAR-RV/vf overlay as an explicit DD governor** on the unchanged champion (~8% PnL haircut for ~33% less DD), labeled as a risk overlay. Re-validate the *combined* config OOS as a unit; size conservatively. This is overlay calibration + acceptance test, **not** a re-opt of base.

**Branch C — You want to seriously evaluate/adopt ATR sizing as a performance feature:**
- Run a fresh **NSGA-III + Optuna walk-forward study under a NEW prefix `wsh5`** (never reuse `wsh4` — its CSV/PNG/Pareto outputs assume the old schema; new `atr_*` keys would silently corrupt comparability) on fresh per-TF `wsh_<tf>.db` files.
- **Search space (JOINT):** base `sl_soft`, `sl_hard_delta`, `tp` (existing wsh4 bounds) **UNION** `{a ∈ [0.3, 2.0], clip_lo ∈ [0.3, 1.0], clip_hi ∈ [1.0, 3.0], atr_source, atr_period}`, optionally `gate_pct`/`k` so the gate can adapt to the new risk profile. The band must be **two-sided / NOT pre-clamped shrink-only** — otherwise you re-bias toward the study's own conclusion.
- **Objective:** the SAME multi-objective frame the champion was selected under (return AND drawdown/DD-discipline), judged on **return/DD, not raw PnL**. Do not pre-bake a DD budget into the band; let a DD-constrained Pareto front emerge.
- **Protocol:** causal expanding-mean ref baked in (R1, no look-ahead), source-correct period (R2, 1m→240), **multi-fold walk-forward** (not the single 2026 OOS slice), parity anchor that `m≡1` reproduces the fixed champion, frozen data provenance/windows/folds/seed/schema-version so the search space is the only changed variable.
- **Decision rule (pre-registered):** adopt only if a jointly-optimized point **OOS-dominates** the fixed champion on the Pareto front (≥ return AND ≤ DD) across folds; otherwise keep fixed — now the rejection is *earned*.
- **Cost vs ROI:** a full all-TF sweep is GPU-hours-expensive and the prior is weak (no demonstrated profit edge; only DD reduction). **Pilot on ONE timeframe first (4h)**; fan out to all 6 only if the probe at least matches fixed profit on held-out folds. Spend is justified only by a standing drawdown-reduction mandate or the n=1-regime hedge (a multiplier that *widens* stops when ranges widen could survive the wider-future-range failure mode static SL/TP faces). If no one is asking for lower DD and the 1-TF probe can't match fixed profit, **stop and keep the champion.**

## 6. Bottom Line

The deployed fixed champion needs **no re-optimization** — it is provably byte-identical to its golden baselines, lives in the unchanged static-sizing search space, and every substantive change this session (R1/R2/R3) plus the multiplier itself is gated to the ATR path it never touches; re-running wsh4 would only reproduce it at the cost of GPU-hours and fresh overfitting risk. ATR sizing, however, is a **categorically new search dimension** that rescales the very SL/TP the base was co-tuned for, and the existing "no edge" verdict comes from a freeze-base, single-coefficient, shrink-only experiment that *structurally could not* observe a profitable sized configuration — so it is a valid hypothesis filter but an invalid adoption decision. Keep shipping fixed; do not adopt ATR off the dashboard or the rigged study; and **only if** drawdown reduction is an explicit, funded objective, launch a fresh joint `wsh5` NSGA-III walk-forward study with a two-sided band and risk-adjusted scoring, piloted on 4h, that must OOS-dominate the champion before any swap.
