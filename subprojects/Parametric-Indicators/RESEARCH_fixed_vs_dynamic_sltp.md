# Research Report — Fixed vs Dynamic SL/TP, and Re-Optimization Cadence (internal + external harvest)

**Date:** 2026-06-14 · **Question:** keep **FIXED** SL/TP refreshed by periodic (≈6-month) re-optimization, or
adopt **dynamic/adaptive** SL/TP? · **Sources:** (A) our local codebase + research docs, (B) external
literature. · **Companions:** `DECISION_derived_sltp_options.md`, `STUDY_relative_feasibility.md`,
`COUNCIL_RULING_atr_sizing.md`, `COUNCIL_RULING_reoptimization.md`.

> **Verification status (read first).** External literature was harvested AND **adversarially verified** (3
> independent skeptic votes per claim; need ≥2 refutes to kill). The first run's verification failed on a
> session rate-limit; this report reflects the **completed re-run**: **7 claims confirmed** (mostly 3-0), **9
> over-broad claims rejected** — the rejected ones are listed in §B-rejected so you can see what did NOT survive.
> Part A (internal) is from our own verified code/studies. Confidence labels are per-claim below.

---

## 0. Bottom line
**The decision stands: keep FIXED SL/TP, refresh by re-optimization — with two refinements from the literature.**
Internal evidence and external theory agree that *adaptive SL/TP **placement*** has no demonstrated profit edge
on our data and only helps under specific regime structure we don't observe. Two refinements: (1) **don't assume
6 months** — set the cadence empirically (walk-forward) or by a drift trigger; our data suggests drift is slow,
so re-opt may be *less* frequent than 6mo; (2) the one literature-supported adaptive lever for a risk asset like
NQ is **volatility-targeted position *sizing*** (scale exposure ∝ 1/vol) — a *different* lever than SL/TP lines,
untested here, and whose robust benefit is **drawdown/tail reduction, not higher Sharpe**.

---

## PART A — Internal evidence (our codebase + research) — HIGH confidence

| # | Fact | Source (file) |
|---|------|---------------|
| A1 | **Fixed champion (4h):** sl_soft=149.8, sl_hard=167.1, tp=120.2, gate_pct=86.9, dd_limit=4747; full-window P/L $108,748, 342 trades, DD $34,411. Produced by **NSGA-III walk-forward** (`wsh4`). | `optimize/results/wsh4_champions_full.json`, `STUDY_sub_optimizer.md §4.7` |
| A2 | **ATR sizing (opt1), OOS:** −33% drawdown, +3pt win-rate, **−8% profit**; ret/DD 4.17→5.61. A **drawdown-reducer, not a profit engine.** | `STUDY_sub_optimizer.md §6.3–6.4` |
| A3 | **Shrink-only band binds:** the studied multiplier range is `m ∈ [0.33, 1.05]` (40/120.2 … 175/167.1) — can only tighten SL/TP. | `vol_source_compare.py:25` |
| A4 | **Stage-0 feasibility = NO-GO:** dividing best-SL/TP by ATR/vf/price makes it **more** dispersed (sl_soft absCV 0.317 vs /ATR 0.349). Absolute optima already stable (sl_hard CV **0.151**). Vol weakly tracks the optimum (r: sl_soft +0.44, sl_hard +0.05, tp +0.29). | `STUDY_relative_feasibility.md §1–4` |
| A5 | **Per-window optima are noise-dominated** (5–38 trades/window, median 18); `tp` correlates **−0.30** to price (opposite of the premise). | `REPORT_stage1.md §2` |
| A6 | **Council (ATR sizing): 6–0** "study-correct" — the dashboard "+21%" was an in-sample/look-ahead artifact; honest config lands on fixed-parity. | `COUNCIL_RULING_atr_sizing.md` |
| A7 | **Council (re-opt): 6–0** — fixed champion needs **NO** re-opt (byte-identical, gated changes); ATR sizing **is a new search dimension** (joint `wsh5` only if adopting). | `COUNCIL_RULING_reoptimization.md` |
| A8 | **Infra ready:** NSGA-III + Optuna walk-forward on **Postgres**, per-TF DBs; fresh runs use a **new prefix** (`wsh5`); SQLite-contention incident fixed. | `optimize/server/INCIDENT_*`, `MIGRATION_per_tf_db.md` |
| A9 | **HAR-RV `vf` is our best volatility forecast** (beat GARCH/EWMA/LSTM/NBEATS; RMSE 0.000222, QLIKE 0.535) and already drives the vol gate; it was the lowest-DD sizing driver in the study. | `meta-prophet/notes/40_phase_A_volatility_tournament.md`, `volatility.py:63-77` |

**Internal verdict:** adaptive **SL/TP placement** = no profit edge, only DD reduction; the fixed optimum is
stable; fixed needs no re-opt now.

---

## PART B — External literature (harvested + **adversarially verified**; vote shown, ≥2/3 refutes kills)

### B1. Do stops help, and is a *fixed* stop fine?
- **[verified 3-0, high] A FIXED 10% stop more than doubled momentum Sharpe** (0.165→0.369), raised mean return
  0.99%→1.69%/mo, cut std 6.01%→4.58% (CRSP 1926–2013). **Direct evidence FOR fixed stops** — the authors leave
  *dynamic/conditional* stops to future work. *(Han, Zhou & Zhu, "Taming Momentum Crashes" — cicfconf.org/.../paper_811.pdf)*
  *Caveat preserved by the verifiers: in-sample, gross of costs, multiple levels searched.*
- **[verified 3-0, high] Stops are regime-dependent, not universally good:** under a **random walk (IID)** the
  stopping premium is **always ≤ 0** ("no conditions under which a simple stop adds value to an IID portfolio");
  it is **positive only under momentum/serial correlation.** Whether a stop helps depends on the *return process*
  → the argument for **periodic re-fitting to the current regime, NOT per-trade vol-scaling.**
  *(Kaminski & Lo, J. Financial Markets 2014 — SSRN 968338 / MIT DSpace)*

### B2. Volatility targeting (the genuinely-supported "dynamic" lever — but it's position *SIZING*, not stop lines)
- **[verified 3-0, high] Vol targeting raises Sharpe for *risk assets* (equities, credit)** — US equities
  1927–2017 **0.40 → 0.48–0.51** (intercept 0.64bp, **t=3.05**, NW-30) — but **negligible for bonds, FX,
  commodities.** Asset-class-specific, via the **leverage effect.** This is **notional sizing, not SL/TP exit
  levels.** *(Harvey et al. 2018, J. Portfolio Mgmt — people.duke.edu/~charvey/.../P135; Man Group)*
- **[verified 3-0, high] Vol targeting's broadest, most robust benefit is tail-risk / drawdown reduction**
  across all 60+ assets (equity vol-of-vol 4.6%→1.8%; lower max-DD), *even where Sharpe doesn't improve*, because
  tails cluster in high-vol periods when a vol-targeted book already holds small exposure. *(Harvey et al. 2018; Man Group)*
- **Relevance:** NQ index futures ARE a "risk asset" → vol-based **sizing** is the supported dynamic lever — a
  *different question* from whether SL/TP **price levels** should be dynamic (which we tested and rejected).

### B3. Re-optimization cadence / overfitting discipline
- **[verified 3-0, high] Cadence & walk-forward window length are first-order:** performance is highly sensitive
  to window size, so a **6-month re-fit cadence is a parameter that must itself be validated, not assumed.** *(arXiv 2602.10785)*
- **[verified 2-1, medium] Parameter decay is real but strategy-specific:** standard frameworks don't model
  staleness; in one study parameters **held up ~2 years** without retraining — so decay is **not pinned to any
  6-month figure.** *(arXiv 2602.10785)*
- **[verified 3-0, high] Re-optimization is double-edged — Minimum Backtest Length:** searching enough configs
  (incl. stops/targets) fits a backtest to *any* Sharpe. **5 yrs of data supports ≲45 independent configs; 2 yrs
  only ≈7;** beyond that in-sample Sharpe→1 while true OOS Sharpe→0. **Any re-fit must report/limit trial count.**
  *(Bailey & López de Prado, "Pseudo-Mathematics… / Probability of Backtest Overfitting" — davidhbailey.com; SSRN 2460551)*

### B-rejected (claims that did NOT survive adversarial verification — do not rely on these)
- *Rejected 0-3:* the headline **crash-protection magnitude** (worst momentum month −49.79%→−11.36%) — the Sharpe
  figures above survived, this extreme-loss figure did not.
- *Rejected 0-3:* "vol targeting improves risk-adjusted returns **across multi-asset classes**" (over-broad — it's
  risk-asset-specific, per the verified B2).
- *Rejected 0-3:* stop-loss "**up to 30× lower variance**" (OMX thesis) and a generic WFO definition claim.
- *Not confirmed (1-2):* the OMX-Stockholm stop-loss empirical results; "responsive vol targeting helped through
  March-2020"; "vol-managed > constant-notional Sharpe" (general phrasing); "one-shot OOS is best practice"; the
  *proportionality* form of the momentum stopping-premium. → treated as unsupported here.

---

## PART C — Reconciliation (where internal & external meet)

1. **They agree on the core.** Fixed SL/TP is a sound, literature-blessed default; adaptive **stop placement**
   shows no profit edge on our NQ data (A2, A4), and theory says stops only add return under
   **momentum/regime structure** (B1, Kaminski–Lo) — structure our per-window study did **not** find (A4/A5).
   So "no dynamic SL/TP for now" is consistent with both.
2. **Two different "dynamic" levers — don't conflate them.** The external *positive* vol result (B2) is about
   **position *sizing*** (scaling exposure by 1/vol), **not** stop-line distance. We tested the latter and it
   failed; the former is **untested here**. NQ is a risk asset, so vol-targeted *sizing* could in principle help
   per Harvey — **but** (a) its robust benefit is **drawdown/tail reduction, not Sharpe**, and (b) our strategy
   already has a **HAR-RV vol gate + drawdown breaker** doing part of that job, so the marginal gain may be small.
3. **The DD-reduction we measured is exactly what the literature predicts.** Our shrink-only ATR overlay gave
   **−33% DD for −8% PnL** (A2); Harvey/Man say vol-scaling's *cross-asset* benefit **is** tail/drawdown
   reduction, not higher Sharpe (B2). Consistent. So *if* drawdown reduction ever becomes the goal, the
   literature supports a vol-scaled **overlay**, accepting the profit haircut — not as a profit play.
4. **The cadence needs evidence, not a calendar guess.** External best practice (B3): set re-opt frequency by
   walk-forward, treat it as a tunable, use double-OOS. Internal (A4): the absolute optimum drifts slowly
   (sl_hard CV 0.15; half-split drift 13–17%) → re-opt may be needed **less** often than 6 months, and a
   **drift-trigger** ("smoke alarm", `DECISION` Option 4) likely beats a fixed calendar.

---

## PART D — Verdict on the decision + refinements

**Confirmed:** keep **FIXED** SL/TP; do **not** adopt dynamic SL/TP now. Both our evidence and the external
literature support it (no edge in adaptive *placement*; stops help only under regime structure we don't see).

**Refinements the literature adds:**
- **R-a (cadence):** don't hard-code 6 months. Run a **walk-forward study to choose the re-opt interval**, and/or
  drive it by a **drift monitor** (re-opt when live metrics leave tolerance). Our data hints the safe interval is
  ≥6 months. *(B3 + A4)*
- **R-b (use double-OOS + pre-registration)** for any future re-opt or sizing test, to avoid the
  multiple-testing inflation the literature warns about. *(B3)*
- **R-c (future avenue, distinct from what we rejected):** if a *drawdown-reduction mandate* appears, evaluate
  **volatility-targeted position *sizing*** (not SL/TP lines), driven by **HAR-RV `vf`** (A9), as an overlay —
  expecting lower DD/tails at a small profit cost, validated joint-`wsh5` walk-forward with the pre-registered
  OOS-dominance rule. *(B2 + A2 + COUNCIL_RULING_reoptimization §5C)*

**Net:** the plan is sound; tighten it by *measuring* the cadence instead of assuming it, and park "vol-scaled
position sizing" (not stop placement) as the only literature-supported adaptive idea worth a future look.

---

## Methodology & caveats
- **Internal (Part A):** harvested by a read-only mining agent across the PI subproject + sibling research dirs,
  with `file:line` citations; cross-checked against this session's own studies/councils. High confidence.
- **External (Part B):** deep-research harness (parallel web search → fetch → extract → **3-vote adversarial
  verification** → synthesize). First run's verification failed on a session rate-limit; **re-run completed** —
  7 claims confirmed (mostly 3-0), 9 rejected (§B-rejected). Confirmed claims trace to reputable primary sources
  (Harvey et al./Duke, Man Group, Han-Zhou-Zhu/CICF, Kaminski-Lo/SSRN-MIT, Bailey & López de Prado, arXiv).
  102-agent run, ~2.3M tokens.
- **Scope:** external equity/momentum studies are *analogues*, not NQ-4h-box-specific; they inform priors, the
  internal NQ results govern the decision.
