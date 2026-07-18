# Experiment 2b — Sizing PROMOTED (equal-risk, OOS, scale-robust)

**2026-07-18, server.** Follow-up to [EXP2_SIZING.md](EXP2_SIZING.md), addressing its three caveats
(borderline / arbitrary scale / drawdown rose). **Verdict: GREEN — a validated positive.**

## The honest, equal-risk result
Exp2 raised Return/DD 5.52 → 5.90 but also raised absolute drawdown ($27.5k → $31.0k). Reframed at
**identical risk** — scale the ramped book so its max-drawdown equals the flat book's $27,508 — the ramp is a
clean **profit uplift at the same drawdown**:

| ramp (calm→turbulent size) | Return/DD | **P/L at equal risk** (DD held = $27,508) | vs flat $151,872 |
|---|--:|--:|--:|
| flat | 5.52 | $151,872 | — |
| 0.7 → 1.3 | 5.76 | $158,380 | **+$6,508** |
| **0.5 → 1.5** | **5.90** | **$162,228** | **+$10,356 (+6.8%)** |
| 0.3 → 1.7 | 5.89 | $162,144 | +$10,272 |

## The three caveats, closed
1. **Scale is not cherry-picked** — every ramp steepness helps (+$6.5k to +$10.4k at equal risk); the benefit
   saturates past 0.5→1.5, so that's a sensible default, not a tuned peak.
2. **Out-of-sample holds** — with the a-priori ramp fixed, it helps both in-sample (2024–25: 3.79 → 4.19) and
   on the **held-out 2026** (10.76 → 10.85).
3. **Drawdown concern resolved** — the equal-risk framing *holds max-DD constant* and still earns +$10.4k, so
   the win isn't just "more risk for more return."
4. **Random control strengthened** — beats **96%** of random regime→size maps (median 5.16).

## Why it works (the mechanism, restated)
The strategy is **vol-seeking** — its edge lives in turbulent regimes (Return/DD 4.15 there vs −0.17 in the
calmest). Sizing **up** where it earns and **down** where it bleeds re-weights toward the edge. The textbook
*inverse*-vol targeting does the opposite and **hurts** (4.06). This is the constructive payoff of the whole
vol-model arc: three methods proved you can't *avoid* volatility here; this proves you should *lean into* it.

## Remaining limit (stated)
Still the single **2024–26 book** (box levels only exist from 2024). The equal-risk + OOS-2026 + scale-robust +
96%-random evidence is strong, but a multi-year (bear-inclusive) confirmation needs the 2010–23 box levels.

## Deployable spec (for wiring into L1/L2 — default OFF, opt-in)
> At each entry, look up the day's **causal (filtered) HMM regime** (fit on daily NQ returns + realized-vol +
> volume, params trained on history ≤ the trade date). Apply a size multiplier = a **linear ramp by the
> regime's realized-vol rank**, calmest **0.5×** → most turbulent **1.5×**, then **normalize the ramp so the
> book's max-drawdown stays within the flat risk budget** (≈ scale by flat_DD / ramped_DD). NQ-validated;
> re-derive the ramp per instrument. Ship behind a flag; golden-safe when off.

Script: `promote_sizing.py` (reuses `research-regime-hmm/regime_baseline.py`).
