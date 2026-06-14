# Council Ruling — Dynamic ATR sizing vs Fixed champion (which experiment is correct)

**Convened:** 2026-06-14 · 6 independent expert lenses + chief adjudicator · companion to
`REVIEW_atr_sizing_contradiction.md`. **Vote: 6–0 "study-correct", mean confidence 0.857.**

## Final verdict
**The STUDY is the correct experiment.** It is the only *valid measurement* of "does dynamic ATR
sizing beat fixed?", and its answer stands: **ATR sizing does NOT beat fixed on profit out-of-sample;
it is a drawdown-reducer, not an alpha source.** The dashboard's "+21%" is a confounded in-sample
artifact that collapses to fixed-parity (172k → 144k → 142k) the instant it is held to honest
conditions.

## Vote tally
| Lens | Verdict | Conf. | One-line |
|---|---|--:|---|
| Logic / epistemology | study-correct | 0.85 | Only the study isolates the variable under test; +21% is a confound, not a finding. |
| Statistician / econometrician | study-correct | 0.86 | Held to honest OOS, +21% evaporates to fixed-parity and goes negative — sampling, not signal. |
| Quant finance / risk | study-correct | 0.86 | Study's OOS, leak-free, frozen-param verdict (DD-reducer) is what a risk desk sanctions. |
| Futures trader / microstructure | study-correct | 0.82 | +21% is an artifact of look-ahead + permissive band + in-sample; sizing 4h risk off 14-min vol is incoherent. |
| ML / overfitting skeptic | study-correct | 0.85 | Textbook free-DOF in-sample artifact; vanishes once you remove look-ahead / constrain band / go OOS. |
| Software-correctness / data-integrity | study-correct | 0.90 | Four compounding correctness defects; stripping them collapses it onto fixed. |

## Where the council agrees (the consensus core)
- **The reconciliation fact IS the case.** Same engine, same data: dashboard 1-min defaults
  (period 14, band 3.0 → 172k) → study config (period 240, band 1.05 → 144k) lands on fixed (142k).
  **When fixing the parameters erases the effect, the effect *was* the parameters.** This is an ablation.
- **OOS is the only arbiter, and it falsifies the dashboard.** On 2026, every honest config loses to
  fixed (4h −16%/−25%, 1m-study-config −22%). The dashboard "full" window is entirely in-sample.
- **Four bundled confounds** (in-sample vs OOS · look-ahead ref vs train-only · 3× expansion vs
  shrink-only · 14-bar vs 240-bar) → the +21% cannot be attributed to ATR sizing; the experiment is
  not well-posed.
- **Period-14 is a unit/semantics bug, not tuning:** 14 bars on the 1-min frame = **14 minutes** of
  volatility driving a **4-hour** risk decision. The study's 240 (= one 4h bar) is the coherent estimator.
- **The look-ahead leak is real but exculpatory for the headline** (~6%, pushes the multiplier
  *smaller*, i.e. *against* the increase). It does not cause +21% — but it still disqualifies the
  dashboard as a *causal* measurement (a normalizer that sees the future is uncertifiable at trade time).

## The honest steelman for the dashboard (where it disagrees / nuances)
- The study's **shrink-only band may pre-rig its own conclusion**: a TP that can only shrink can almost
  never beat fixed on profit, so "DD-reducer only" might be an artifact of an over-conservative clip
  rather than a property of ATR sizing.
- The **one OOS expansion result is genuinely held-out**: `1m clip0.3-3.0 p14` posts **+15% PnL on 2026**
  (33,189 vs 28,899) — not in-sample luck.
- **Decisive rebuttal:** that +15% is bought with **+34% drawdown** (14,082→18,825); return/DD degrades
  **2.05 → 1.76**. Risk-adjusted performance gets *worse*. That's leverage-via-target-stretching —
  replicable by just trading more contracts on fixed, without the fragility. The steelman justifies
  *running a proper test*, not *believing the headline*.

## The distinction that matters — "correct" on three axes
- **(a) Valid measurement?** Only the study (one factor, frozen coefficient, train-only ref, OOS). The
  dashboard *mines*; the study *measures*.
- **(b) Answers the deployment question?** Only the study → "deploy fixed; ATR only as a shrink-only DD
  overlay." The dashboard answers an unfalsifiable in-sample retrodiction → licenses no deployment claim.
- **(c) What the dashboard IS good for:** a hypothesis generator / exploratory ceiling. It even
  *triangulates* the study (its own honest config 1m-p240-band1.05 = 144k ≈ fixed corroborates "no edge").

## Ruling for the operator
**Deploy:** the **fixed champion** as production sizing. Optionally add the study's **4h-ATR / HAR-RV
`vf` shrink-only overlay (band 0.33–1.05, period 240, train-only ref) purely as a drawdown governor** —
size *down* in high vol, never up — accepting ~8% PnL haircut for ~33% less DD. (n=1-regime caveat.)

**Fix before the dashboard touches any decision surface (R1–R3 from the review):**
1. **Kill the look-ahead** — `strategy.py:342` ref → train-only / causal mean (match `stage2.py`).
2. **Decouple `atr_period` by source** — 1m defaults to **240**, surface the unit in the UI.
3. **Default the clip band to 0.33–1.05** (shrink-only); require explicit opt-in for any expansion.
4. Label the dashboard **in-sample exploration**; add an OOS toggle.

**Never trust:** the "+21%" headline in any form; any in-sample dashboard PnL as evidence of edge; any
expansion-band result until re-run through the study's protocol (fit-then-freeze coefficient,
train-only ref, **multi-fold walk-forward** not one 2026 slice, selection-adjusted significance, 2024
regime restored) and judged on **return/DD, not raw PnL**.

**Bottom line:** Fixed is champion. ATR sizing is a drawdown knob, not a profit engine. The dashboard is
a sketchpad, not a verdict.
