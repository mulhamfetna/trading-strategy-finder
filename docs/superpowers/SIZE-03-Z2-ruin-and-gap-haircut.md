# SIZING · 03 — Z2: the tail/gap haircut (drawdown binds, not ruin)

**Z1 gave the Kelly fraction from the bounded-loss backtest. Z2 overlays the live gap-through-the-stop risk
(D2/D3) and Monte-Carlos the equity path to find the tail-safe fraction. The honest result: at any sensible
fraction, **ruin from the modeled gap tail is negligible — the binding constraint is DRAWDOWN**. Full Kelly
gives a >50% drawdown most of the time; you need quarter-to-half Kelly for a tolerable ride. The gap tail
adds a modest caution and a reason for a hard cap against the *un-modeled* black-swan.**

Date: 2026-07-15 · Branch `fundamental-analysis` · Code: `optimize/fundamentals/study_ruin.py` · Raw:
[`results/ruin_nq.txt`](results/ruin_nq.txt) · 4,100 edge-champion trades (4h/2h/1h/15m; 5m/2m dropped per
Z1). 4,000 paths × 1,000 trades. Gap model: Pareto(α=3) on a fraction g of stop-outs, capped at 4–6× the stop.

---

## ⚡ THE 60-SECOND VERSION

| | |
|---|---|
| **Ruin is not the binding constraint** | P(ruin, wealth<10%) stays **< 1%** up to f ≈ 2.5% even with a 10% gap rate. A 4–6× gap on a bounded −40 stop is a survivable single-trade loss. |
| **DRAWDOWN is what binds** | P(50% drawdown): **~0%** at quarter-Kelly (0.6%), **~5–9%** at half-Kelly (1.2%), **58–73%** at full Kelly (2.5%). Full Kelly is punishingly volatile — exactly the research warning (K4). |
| **The gap tail matters modestly** | It lowers the ruin threshold from f≈4% (no gap) to f≈3% (g=10%). Real, but not dominant at small f. |
| **The un-modeled black-swan** | My gap caps at D3's extreme (~160 pts). A larger flash-crash/halt gap isn't modeled → **that** is what a hard exposure cap protects against (K6). |
| **The converged sizing** | **quarter-to-half Kelly (~0.6–1.2% of capital risked per trade), edge-champions only, hard contract cap.** |

---

## 1 — The Monte Carlo (P(ruin) / P(50% DD) by fraction and gap rate)

| f (risk/trade) | P(ruin), no gap | P(ruin), g=5% | P(ruin), g=10% | P(50% DD), g=5% |
|---|---|---|---|---|
| **0.6% (quarter)** | 0.00% | 0.00% | 0.00% | **0.0%** |
| **1.2% (half)** | 0.00% | 0.00% | 0.00% | **5.2%** |
| 2.0% | 0.00% | 0.03% | 0.00% | 39.4% |
| **2.5% (full Kelly)** | 0.07% | 0.07% | 0.33% | **66.6%** |
| 3.0% | 0.25% | 0.88% | **1.18%** 🔴 | 83.7% |
| 4.0% | 2.97% 🔴 | 4.58% 🔴 | 7.80% 🔴 | 98.1% |

> **🍼 In plain words** — read the two right-hand columns together. **Ruin** (losing ~everything) barely
> registers until you're risking 3–4% per trade — because even a gap that quadruples a loss is still a
> bounded, survivable hit. But **drawdown** tells the real story: at full Kelly (2.5%) you'd sit through a
> 50%+ equity drop about **two times in three** — a ride almost no one survives psychologically or
> operationally. Cut to **half-Kelly** and that 50%-drawdown chance falls to ~5%; to **quarter-Kelly** and
> it's essentially nil. **The fat tail doesn't ruin you at sensible size; the *volatility of full Kelly*
> does.**

---

## 2 — The synthesis: what to actually risk

Three independent constraints, and you take the **minimum**:

| Constraint | Source | Says |
|---|---|---|
| **Edge uncertainty** | Z1 | f\* = 2.5% but CI floor 0.3%; quarter-Kelly 0.6% for parameter safety |
| **Drawdown tolerance** | Z2 | f ≤ ~1.2% (half-Kelly) to keep P(50% DD) < ~10% |
| **Gap-ruin (modeled)** | Z2 | f ≤ ~2.5–3% to keep P(ruin) < 1% |
| **Black-swan (un-modeled)** | K6 | a **hard absolute cap** on contracts, independent of f |

**⇒ The binding pair is edge-uncertainty and drawdown, both pointing at ~quarter-to-half Kelly.** The
recommended sizing: **risk ~0.6–1.2% of capital per trade** (start at quarter-Kelly ≈ 0.6%, floored by the
Z1 CI; go to half-Kelly ≈ 1.2% only if the drawdown is acceptable and the edge is confirmed OOS), **on the
edge-champions only** (4h/2h/1h/15m — not 5m/2m, whose Kelly edge is ~0), **with a hard contract cap** for
the catastrophe the model can't see.

> **The through-line, one last time:** a small, uncertain, fluke-window edge on a fat-tailed instrument
> yields a small, capped, conservative bet. Every strand of this project — the priced-in news, the fair-
> martingale stop, the rejected assist, the truncated P&L, and now the Kelly math — converges on the same
> counsel: **modest size, hard caps, no leverage.**

---

## 3 — Caveats (do not over-read)

- The gap rate `g` and cap are **assumptions from D2/D3, not measured live fills.** Sensitivity is shown
  across g (5–10%) and cap (4–6×); the conclusion (drawdown binds, ruin is modest at small f) is stable
  across them. **A real fraction needs real fill/slippage data** — which we do not have.
- The edge (p≈40%) is a **2025–2026 estimate**; if it's lower going forward, every fraction here shrinks.
- This is **not adopted.** Production is byte-identical; $0. It is a *recommendation with a bound*, pending
  the remaining checks.

---

## 4 — What remains (refinements, not the core answer)

| Next | What |
|---|---|
| **Z3** | A/B **fixed-fractional vs volatility-targeting** contract scaling on the ledgers, net of costs + integer contracts — the sizing *method*, given the *fraction* is settled here. |
| **Z4** | Recompute for our **PnL:DD** objective (Maier-Paape–Zhu) rather than raw log-growth — likely nudges toward the lower (half-Kelly) end, since it penalizes drawdown directly. |

**The core sizing question — how much to risk per trade — is answered: ~quarter-to-half Kelly, capped.**
