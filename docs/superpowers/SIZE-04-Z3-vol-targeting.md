# SIZING · 04 — Z3: volatility-targeting the contract count (PROMISING, needs OOS)

**Z2 settled the fraction; Z3 asks the method — fixed contracts vs scaling contract count by 1/volatility.
My prior (from D4) was that the fixed-point stop already normalizes risk, so vol-targeting wouldn't help.
The disciplined test says otherwise: leverage-matched and after costs, vol-targeting improves Sharpe
3.19 → 3.94 and holds in both chronological halves. It is NOT the same lever D4 rejected, and it is
promising — but it is in-sample, its mechanism is unclear, and it adds turnover, so it is NOT adopt-ready.**

Date: 2026-07-15 · Branch `fundamental-analysis` · Code: `optimize/fundamentals/study_vol_target.py` ·
Raw: [`results/vol_target_nq.txt`](results/vol_target_nq.txt) · 4,099 NQ edge-champion trades.

---

## ⚡ THE 60-SECOND VERSION

| | |
|---|---|
| **Vol-targeting improves Sharpe** | 3.19 → **4.01** (leverage-matched), **3.94** after a turnover cost. return/DD 5.55 → 7.34. |
| **It held in BOTH halves** | Sharpe edge +0.55 (1st half), +0.37 (2nd half) — not a single-cluster artifact. |
| **But the mechanism is unclear** | corr(pnl, σ) = **−0.021** ≈ 0 — no strong *linear* vol-edge, so *why* it helps is murky (likely the strategy's vol-gate already selects low-σ entries and this concentrates on the cleanest ones). |
| **It's different from D4's reject** | D4 rejected vol-scaling the **stop distance** (broke the gambler's-ruin race). Z3 scales **contract count** — it preserves the race and just reweights $ exposure. A legitimately different, workable lever. |
| **Verdict** | 🟡 **PROMISING, not adopt-ready.** In-sample (both halves are 2025–2026), murky mechanism, 57% per-trade turnover. **Needs a true OOS test (GC, or a longer frame) + real cost modelling before adoption.** |

---

## 1 — The comparison (leverage-matched, so totals are fair)

| Method | total (pts) | maxDD (pts) | Sharpe~ | return/DD |
|---|---|---|---|---|
| **FIXED** | 9,772 | 1,761 | 3.19 | 5.55 |
| **VOL-TARGET (matched)** | 14,022 | 1,865 | **4.01** | **7.52** |
| **VOL-TARGET − costs** | 13,790 | 1,878 | **3.94** | 7.34 |

Leverage-matched (mean weight = 1) so the totals are comparable exposure. A turnover cost (~0.1 pt per unit
size change) barely dents it (Sharpe 4.01 → 3.94) — but that cost is a *proxy*; a realistic spread/slippage
cost on 57% per-trade rebalancing could be larger.

## 2 — The robustness check (the reason it's not dismissed)

| Half | FIXED Sharpe | VOL-TGT Sharpe | edge |
|---|---|---|---|
| 1st | 3.48 | 4.04 | **+0.55** |
| 2nd | 1.02 | 1.39 | **+0.37** |

The Sharpe advantage **persists in both halves** — so it is not one lucky cluster. That is why this is
flagged *promising* rather than *rejected*. (Note the 2nd-half Sharpe is much lower for both methods — the
edge itself decayed across 2025→2026, consistent with the fluke-window caution.)

---

## 3 — Why I am NOT declaring a win (the discipline)

1. **In-sample.** Both halves are *within* 2025–2026 — the fluke window this project keeps flagging. "Both
   halves" is a stability check, **not** a true out-of-sample test. The whole workstream's lesson is that
   in-sample improvements in this window often don't survive (silver, magnitude, the Asia cell).
2. **Murky mechanism.** corr(pnl, σ) ≈ 0 means there is no strong *linear* reason vol-targeting should
   help. The plausible real story — the strategy's volatility **gate** already selects low-σ entries, and
   vol-targeting concentrates further on the cleanest (lowest-noise mean-reversion) ones — is a hypothesis,
   not a demonstrated mechanism. An edge you can't explain is an edge you should distrust until OOS.
3. **Turnover.** 57% mean size change per trade is real rebalancing; my cost model is optimistic.
4. **Contrast with D4.** D4's vol-scaled *stop* was cleanly rejected (it broke the fixed-stop/TP gambler's-
   ruin balance). Z3 is a *different* lever (contract count, not stop distance), which is *why* it can help
   where D4 couldn't — but that also means it must clear its own OOS bar.

---

## 4 — VERDICT & next

**🟡 Keep vol-targeting alive as a PROMISING sizing method — do not adopt yet.** It is the one sizing
refinement that showed a possible improvement, and unlike D4's rejected stop-scaling it is a mechanically
valid lever. But it is in-sample, unexplained, and turnover-heavy. **Before adoption it needs:**
- a **true out-of-sample** test — ideally on **GC** (a different instrument), or a longer NQ frame if we
  can run the champion there without changing it;
- a **realistic transaction-cost** model (spread + slippage on the actual rebalancing);
- ideally, a **demonstrated mechanism** (does low-σ-at-entry genuinely predict a cleaner outcome for a
  box/mean-reversion strategy?).

**The core sizing answer is unchanged (Z2): risk ~quarter-to-half Kelly, edge-champions only, hard cap.**
Vol-targeting is a *method* refinement layered on top of that *fraction* — worth pursuing, not shipping.
Nothing adopted; production byte-identical; $0.

**→ Z4 (last sizing refinement):** recompute the fraction for our **PnL:DD** objective (Maier-Paape–Zhu
drawdown frontier) rather than raw log-growth — expected to confirm the lower (half-Kelly) end, since it
penalizes drawdown directly.
