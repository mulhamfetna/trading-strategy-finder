# Experiment 2 — Sizing, not veto

**2026-07-18, server.** **Verdict: PROMISING (the first positive in the program) — tempered.** Regime-scaled
sizing improves risk-adjusted return where every veto failed, because it *leans into* the strategy's
vol-seeking edge instead of fighting it.

## Method
Reuse the causal HMM regime (4 states, filtered). Apply an **a-priori** linear size ramp by regime — calmest
**0.5×** → most turbulent **1.5×** (upsize where the strategy earns, downsize where it loses). Not tuned on
P/L (no selection overfit). Max-DD computed honestly on the scaled equity curve.

## Result
| sizing | P/L | maxDD | Return/DD |
|---|--:|--:|--:|
| flat (baseline) | $151,872 | $27,508 | 5.52 |
| **regime ramp 0.5→1.5** | $182,927 | $31,018 | **5.90** |
| classic vol-targeting (∝1/vol) | $129,007 | $31,775 | 4.06 |

- **Regime ramp: Ret/DD 5.52 → 5.90 (+7%), P/L +$31k (+20%).**
- **Beats 95% of random-multiplier assignments** (same multipliers, shuffled regime mapping; median 5.19) —
  right at the significance bar → the *regime ordering* carries real information.
- **Helps all 3 years:** 2024 1.15→1.37, 2025 7.24→9.35, 2026 10.76→10.85.

## The clean insight (dumb control)
**Classic textbook vol-targeting (inverse-vol sizing) HURTS here (4.06 < 5.52).** It downsizes exactly the
turbulent trades where this strategy makes its money. For a **vol-seeking** strategy you must size **WITH**
volatility, not against it — the opposite of the textbook. This is the mechanistically-correct use of the
regime signal, and it's why the veto (a hard version of "avoid vol") failed while sizing (lean into vol) works.

## Honest caveats
- **Borderline** (exactly 95% vs the random control) and **n=1** book — not overwhelming.
- The ramp *scale* (0.5/1.5) is a-priori but arbitrary; a steeper/shallower ramp changes the magnitude. The
  control tests the *ordering*, not the scale — picking the scale on this book would be overfitting.
- **Absolute max-DD increased** ($27.5k → $31.0k): upsizing turbulent trades raises the drawdown; Ret/DD
  improves only because P/L rises faster. Under a hard DD limit this matters — size *within* the risk budget.

## Verdict: PROMISING — pursue with discipline
The first direction that beats its control. To promote it: (a) select the ramp scale **out-of-sample** (train
slice / a-priori risk budget), (b) re-test on a **longer book** (needs 2010–23 box), (c) cap absolute DD.
This is the actionable form of the program's core discovery (the strategy is vol-seeking → lean into vol).

Script: `sizing_experiment.py` (reuses `research-regime-hmm/regime_baseline.py`).
