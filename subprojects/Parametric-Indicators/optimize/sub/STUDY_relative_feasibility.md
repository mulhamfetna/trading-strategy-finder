# Stage 0 — Feasibility: is a RELATIVE SL/TP more robust than absolute? → **NO-GO (on 2024–2026 data)**

**Date:** 2026-06-14 · Gate for `ACTION_PLAN_derived_sltp.md` · Script: `feasibility_relative_sltp.py` ·
Data: rolling-3-month sub_optimizer table (27 windows, 22 with `bound_clipped==0`), 2024-03 … 2026-05.

## The test
The robustness thesis: an absolute optimum ("SL = 150 pts") drifts as the market changes, but a **ratio**
("SL = k · driver") stays ~constant if the driver explains the drift. Operationalized: compare the dispersion
(CV = std/mean across windows) of the **raw absolute** best SL/TP vs the **ratio** best/driver. If
`ratio CV << absolute CV`, the ratio is the stable quantity → relative sizing self-recalibrates → GO.

## Result (guarded table; wide-bounds table agrees)
| target | absolute CV | /ATR | /HAR-RV(vf) | /price | best | drift (½-split) |
|--------|:-----------:|:----:|:-----------:|:------:|------|:---------------:|
| sl_soft | **0.317** | 0.349 | 0.353 | 0.335 | price (barely) | 13% |
| sl_hard | **0.151** | 0.302 | 0.304 | 0.202 | price | 13% |
| tp | **0.527** | 0.570 | 0.572 | 0.563 | price (barely) | 17% |

**Dividing by a volatility driver makes the optimal SL/TP MORE dispersed, not less.** For every target, the
ratio CV is ≥ the absolute CV (ATR/vf are *worse*; %-price is at best a wash). Correlations are weak:
`r(best_sl_soft, ATR)=+0.44` (moderate), but `sl_hard +0.05`, `tp +0.29` — volatility does **not** track the
optimal stop.

## Why the premise fails here
1. **The absolute optimum barely drifts.** `sl_hard` CV is **0.151** and `sl_soft` **0.317** across 25 months —
   the "best" absolute SL/TP were already fairly stable. There is little drift for a driver to "explain away."
2. **Volatility doesn't explain the drift that exists** (weak/near-zero correlations).
3. **Dividing two quantities adds noise.** ratio = noisy-label ÷ noisy-driver → higher CV. So vol-relative
   sizing would make the stop *less* stable, the opposite of the goal.

## Verdict
**NO-GO for the simple volatility-relative formula (Approach A with ATR/vf/price drivers) as a robustness
play, on the available data.** The pre-registered gate fires: **do not spend GPU on the `wsh5` joint sweep
expecting a robustness win** — the premise (absolute decays, ratio is stable) is not supported over 2024–2026.

## Honest caveats (what this does NOT prove)
- **Horizon:** 25 months, ~one macro regime. "Goes stale after a year" could still be real over *multi-year*
  regime shifts (rate cycles, vol regimes) the data can't see. The thesis is **unsupported here, not disproven**
  for long horizons.
- **Noisy labels:** "best SL/TP per window" are in-sample optima (the councils' caveat); noise inflates the
  ratio CV, so this test is *conservative* against the ratio.
- **Granularity:** drivers are per-window means; a per-bar live driver might track better — but the label is a
  window-level quantity, so window-mean is the right granularity for this test.
- **Performance (the bonus goal) is untested here** — Stage 0 only tests robustness. The councils already found
  no profit edge for vol sizing.

## Options (operator decision)
1. **STOP / keep fixed** *(recommended)* — the data says the optimal SL/TP are stable enough that absolute
   values don't meaningfully decay over a year; the cheap, proven answer to staleness is a **periodic `wsh5`
   re-optimization** (rarely even needed), not a vol-relative reformulation.
2. **Re-scope the robustness test** before any build — longer history if obtainable, per-bar drivers,
   de-noised/regularized per-window labels — then re-gate.
3. **Proceed as a pure performance bet** (not robustness) into a `wsh5` joint sweep — but two councils + this
   study put the odds low; **not recommended** without a new hypothesis.
4. **Pivot the goal** — address staleness operationally (scheduled re-opt cadence) rather than structurally.

**The fixed champion remains the deployed default. No engine change was made. No GPU was spent.**

> **Follow-up (2026-06-15):** re-tested on **FIXED non-overlapping quarters** + a **probability-distribution
> (near-best band)** framing + multi/single-feature maps + a **causal lagged** test — see
> `STUDY_fixed_window_sltp_mapping.md`. Same conclusion: fixed windows don't reduce the noise; the one strong
> signal (best-SL vs price-change, r −0.81) is **look-ahead** and collapses to negative OOS skill when lagged.
> No causally-predictable, error-margin-shrinking mapping exists in this data.
