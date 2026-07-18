# Experiment 3b — the REAL second-layer (L2) book

**2026-07-18, server.** Follow-up to [EXP3_VOLHURT.md](EXP3_VOLHURT.md), using a real profitable second layer
(the mtf book's `position_owner` = L1 primary 1h / L2 secondary 4h) instead of a toy mean-reversion.
**Verdict: the Exp3 veto hypothesis is UNTESTABLE (no vol-hurt book exists in our system); and a caveat on the
promoted sizing surfaced.**

## Per-layer, conditioned on the causal HMM regime
| Layer | n | Ret/DD | calm | turbulent | + vol VETO p85 | + vol SIZE-RAMP |
|---|--:|--:|--:|--:|--:|--:|
| **L1** (primary 1h) | 369 | 6.94 | 0.95 | 1.66 | 6.94 → **6.25** (hurts) | 6.94 → **6.21** (hurts) |
| **L2** (secondary 4h) | 170 | 1.81 | **−0.52** | **3.93 (best)** | 1.81 → **1.27** (hurts) | 1.81 → **2.13 (helps)** |

## Findings
1. **Both layers are vol-seeking** — each earns best in the turbulent regime and loses in the calm one. So our
   whole box-strategy family (breakout on 1h and 4h) is vol-seeking; **there is no vol-hurt book in our system**
   to test "does the veto help a vol-hurt strategy?" (consistent with Exp3: a naive NQ fade just loses — NQ
   rewards momentum). The Exp3 hypothesis stays **untestable on our real strategies.**
2. **The vol veto HURTS both layers** (L1 6.94→6.25, L2 1.81→1.27) — the NO-GO extends cleanly to L2.
3. **The vol size-ramp helps L2 independently** (1.81 → 2.13, +18%) — an *independent* corroboration of the
   promoted sizing ([EXP2b_SIZING_PROMOTED.md](EXP2b_SIZING_PROMOTED.md)) on a second layer.

## ⚠️ Caveat this raised on the promoted sizing (#1)
The size-ramp **hurts L1-standalone** (6.94 → 6.21) even though it helps the *combined* book and L2. On this
2024–26 split, **L1's best regime is *mid*, not the most turbulent** (L1 turbulent 1.66 < mid 4.02), so the
a-priori "upsize the most turbulent" ramp misfits L1 alone. The combined-book win (Exp2b, robust: equal-risk
+$10.4k, OOS, 96%-random) **leans on the L2 + mid-regime structure**, not on L1's tail.

**Consequence — honest scoping of the deploy:** the promoted sizing is validated **on the combined book we
actually trade**, and independently on **L2**, but it is **not uniform per-layer**. If applied per-layer, the
ramp must be **re-derived per layer** (L1 favors mid, L2/combined favor turbulent) — don't port one ramp
blindly. Deploy on the combined book (where it's robust); treat per-layer sizing as its own re-derivation.

Script: `l2_experiment.py`.
