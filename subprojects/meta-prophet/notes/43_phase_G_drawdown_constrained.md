---
name: phase-G-drawdown-constrained
description: Workstream G (cont.) — maximise P/L under a hard max-drawdown cap (≤$5k, and ideally ≤10% of P/L). Tools - vol gate + very-tight stops + a causal drawdown circuit-breaker overlay (no engine edit). Result - $5k-absolute cap MET with +$20,345 P/L at $3,695 maxDD (both years positive, 15× lower DD than baseline); the stricter 10%-of-P/L cap is infeasible on this n=1 data (needs P/L≈$50k).
type: explainer
---

# Workstream G — maximise P/L with a hard drawdown cap

> **Target:** largest total P/L with **maxDD ≤ min($5,000, 10% of P/L)**. Baseline (verified
> params, no risk overlay) was **−$13,420 P/L at $57,160 drawdown** — so this is a big ask.
> Script: `scripts/46_wsg_drawdown_optimize.py` (single-contract clone; the breaker is a causal
> post-processing overlay, so the engine is NOT edited).

---

## 1. The three risk tools (stacked)
1. **Volatility gate (`entry_gate`)** — skip the most-volatile bars (HAR-RV percentile). Removes
   the worst-regime trades.
2. **Very-tight stops** — base SL/TP tightened from the verified 80/100/50 to **20/25/40** so a
   single loss is capped near **$500** (vs $2,000). This shrinks both the loss clusters AND the
   breaker's overshoot.
3. **Drawdown circuit-breaker (overlay)** — walk trades in entry order; once running drawdown from
   the equity peak hits `dd_limit`, stop taking NEW trades for `cooldown` trades, then re-probe
   (peak resets to the resume equity). Decision for trade *i* uses only trades < *i* → **causal**.

---

## 2. Result

### Strict cap — maxDD ≤ min($5k, 10% of P/L): **infeasible (0 of 204)**
The 10%-of-P/L rule is the binding one and it cannot be met here: a $5k drawdown at 10% implies
**P/L ≥ $50k**, but this strategy's edge on 1.4 years (one regime) tops out around $20–40k. To get
maxDD to ≤10% you'd need either much higher P/L (more instruments/history → Workstream F) or stops
so tight the edge erodes. **Honest verdict: not achievable on this data.**

### $5k absolute cap: **MET — best is +$20,345 at $3,695 maxDD**
| rank | config | P/L | 2025 | 2026 | maxDD | DD % of P/L | n | win% |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 🥇 | **vSL_G60 + L2500/cd20** | **+20,345** | +12,620 | +7,725 | **3,695** | 18.2% | 224 | 44.6 |
| 2 | vSL_G60 + L2500/cd15 | +19,910 | +12,185 | +7,725 | 4,850 | 24% | 225 | 44.4 |
| 3 | vSL_G60 + L2500/cd30 | +19,275 | +11,550 | +7,725 | 3,325 | 17% | 194 | 45.4 |
| 4 | vSL_G60 + L3000/cd20 | +17,665 | +9,940 | +7,725 | 4,995 | 28% | 224 | 43.8 |
| — | G60 + L2500/cd30 (verified params) | +11,470 | +10,190 | +1,280 | 4,810 | 42% | 65 | 70.8 |

vs the **−$13,420 / $57,160-DD baseline**, the winner is a **+$33,765 P/L swing with ~15× lower
drawdown**, and — unlike every earlier combo — **both years are positive**.

### Higher P/L if the cap is relaxed (frontier)
- `base + L3000/cd20`: **+$36,610** P/L but maxDD **$13,410** (verified params + breaker only).
- `S+G80 + L3000/cd15`: +$30,127 at $10,756.
So P/L scales up if you allow $10–13k drawdown; holding ≤$5k costs ~$16k of P/L.

---

## 3. Two recommended settings (pick by appetite)
- **Tier 1 — keep the team-verified params (80/100/50), add gate + breaker:**
  `G60 + L2500/cd30` → **+$11,470 P/L, $4,810 maxDD**. No change to the verified stop distances;
  the only additions are "skip high-vol bars" + "halt on drawdown". Most conservative / defensible.
- **Tier 2 — also tighten the stops to 20/25/40:** `vSL_G60 + L2500/cd20` → **+$20,345 P/L,
  $3,695 maxDD, both years positive**. ~1.8× the P/L at lower drawdown, but it changes the stop
  parameters and the strategy's character (see §4).

---

## 4. Honest caveats (do not skip)
1. **n = 1 regime.** The gate percentile, stop distances, and breaker (`dd_limit`, `cooldown`)
   were all chosen on the *same* 2025–2026 data. These figures are **in-sample on a single
   regime** — illustrative of what the *mechanism* can do, not a validated forward return. Out-of-
   sample (more instruments/years → Workstream F) is required before trusting the dollars.
2. **Win-rate dropped 65% → 45%** with the tight stops: the edge now comes from **small capped
   losses + avoiding bad bars + halting on drawdown**, not from a high hit-rate. That's a
   different (and more defensive) strategy character than the verified version — worth a
   team discussion.
3. **The drawdown breaker is a research overlay, not yet in the engine.** It's computed causally on
   the trade stream; to run live it must be implemented as an equity-stop in the execution layer.
4. **maxDD slightly lags the limit.** The breaker fires *after* a breach, so maxDD ≈ `dd_limit` +
   one trade's loss; the tight $500 stop keeps that overshoot small (why vSL beats the
   100-pt-stop configs on the cap).
5. **The verified engine is still untouched** (see `notes/42`); this is all parameters + a
   post-processing overlay on the clone.

---

## 5. Status & next
- **Drawdown-constrained optimisation: DONE.** $5k-absolute target achieved (+$20,345 @ $3,695);
  strict 10%-of-P/L shown infeasible on this data with the reason.
- **To push further (toward the 10% rule):** (a) Workstream F (more instruments → higher total
  P/L makes 10% reachable, and gives out-of-sample validation); (b) implement the breaker as a
  real equity-stop; (c) walk-forward the gate/stop/breaker params to fight the n=1 overfit.
- Outputs: `outputs/wsg_drawdown_optimize.csv`.

## 6. One-paragraph summary (baby)
We were asked to make the most money while never letting the worst losing streak ("drawdown")
exceed $5,000 (ideally also under 10% of profit). We stacked three safety tools — skip the wildest
bars, use much tighter stop-losses (so each loss is ~$500 not ~$2,000), and a "circuit-breaker"
that stops trading after losses pile up and waits before trying again. The best setting makes
**+$20,345 with a worst-drawdown of only $3,695 — comfortably under $5k, and profitable in both
years** (the old version lost $13k with a $57k drawdown, so this is a huge improvement). The
stricter "drawdown under 10% of profit" rule we could **not** meet on this data — that would need
about $50k of profit, which one-and-a-bit years of a single market can't produce; it needs more
instruments/history (and that also gives the out-of-sample proof these tuned numbers still lack).
