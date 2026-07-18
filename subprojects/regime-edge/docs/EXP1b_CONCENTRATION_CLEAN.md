# Experiment 1b — Concentration, cleaner test → NO-GO (the Exp1 gradient was an artifact)

**2026-07-18, server.** Follow-up to [EXP1_CONCENTRATION.md](EXP1_CONCENTRATION.md), which flagged its
random-label *spread* control as too noisy (unequal buckets). Ran the proper tests. **Verdict: NO-GO —
concentration carries no tradeable edge here; the earlier "suggestive gradient" was a Return/DD artifact.**

## 1. High-vs-low, on a stable metric (per-trade mean P&L) → not significant
Return/DD is path-dependent and noisy in small buckets; per-trade mean P&L is stable. On it, the mega-cap
regime and the broad regime are **indistinguishable**:

| | per-trade mean P&L | n |
|---|--:|--:|
| high concentration (mega-cap) | **$294** | 360 |
| low concentration (broad) | **$286** | 65 |
| **gap** | **$8** | — |

Permutation test **p = 0.97**; bootstrap 90% CI **[−$393, +$423]** (includes zero). The Exp1 gradient
(1.66 → 4.29 in Return/DD) was an artifact of the metric + unequal bucket sizes, **not a real difference**.

## 2. Concentration as a sizing signal → hurts
Ramping size 0.5→1.5 by concentration tercile: Return/DD **6.06 → 5.28**, equal-risk P/L **−$19,308**, beats
only **34%** of random regime→size maps. Sizing by concentration is worse than doing nothing.

## 3. Does it add to the vol ramp? → no
Vol-only ramp: Return/DD 6.16 (equal-risk $154,207). Vol × concentration: **5.32** (equal-risk $133,098) —
concentration **subtracts**. It's not orthogonal-useful; it's noise here.

## Verdict: NO-GO
Concentration (QQQ/QQEW) does not carry a tradeable edge for this strategy, as a filter *or* a sizing signal,
and does not complement the vol ramp. **The lesson: a "suggestive" result on a noisy metric must survive a
clean significance test — this one didn't** (Exp1 SUGGESTIVE → Exp1b NO-GO). The one surviving positive in the
program remains the **vol size-ramp** ([EXP2b_SIZING_PROMOTED.md](EXP2b_SIZING_PROMOTED.md)).

Script: `conc_clean.py`.
