# SIZING · 05 — Z4: the fraction for our PnL:DD objective (I predicted wrong; the constraint is absolute DD)

**The last sizing refinement, and it corrected me. I predicted the PnL:DD *ratio* would decline with size,
favoring the smallest fraction. It doesn't — the ratio is roughly flat from half-Kelly to 3% (~2.2). But at
those fractions the median max-drawdown is 30–62%, which is intolerable. The honest lesson: the PnL:DD
*ratio* is a poor sole guide (it trades bigger drawdowns for bigger growth at a constant ratio); the real
binding constraint is the *absolute* drawdown you can stomach — which, with edge-uncertainty, still lands at
~quarter-to-half Kelly. The Z1/Z2 answer holds, but for the right reason.**

Date: 2026-07-15 · Branch `fundamental-analysis` · Code: `optimize/fundamentals/study_kelly_pnldd.py` ·
Raw: [`results/kelly_pnldd_nq.txt`](results/kelly_pnldd_nq.txt) · Monte Carlo, 4,000 paths × 1,000 trades.

---

## ⚡ THE 60-SECOND VERSION

| | |
|---|---|
| **My prediction** | PnL:DD ratio declines with f → favors the smallest fraction. **WRONG.** |
| **What actually happened** | The ratio is **~flat (2.1–2.23) from half-Kelly (1.2%) to 3%**, dropping only at over-leverage (4% → 1.73). |
| **The catch** | At those "optimal" fractions the **median max-drawdown is 30–62%** — brutal and, for most, intolerable. |
| **Why the ratio misleads** | A ratio treats a 60%-DD/2.4× path the same as a 30%-DD/1.67× path. It does **not bound absolute drawdown.** |
| **The correct constraint** | **Absolute drawdown tolerance** (+ edge-uncertainty from Z1). Cap DD at ~25% → ~half-Kelly (1.2%) or below. **Z1/Z2 answer confirmed.** |

---

## 1 — The curve

| f (risk/trade) | median growth | median maxDD | PnL:DD ratio | |
|---|---|---|---|---|
| 0.3% | 1.16× | 8% | 1.89 | |
| **0.6%** | 1.32× | 16% | 1.95 | quarter-Kelly |
| 0.9% | 1.49× | 23% | 2.08 | |
| **1.2%** | 1.67× | **30%** | **2.23** | half-Kelly |
| 1.5% | 1.79× | 37% | 2.15 | |
| 2.0% | 2.00× | 47% | 2.14 | |
| **2.5%** | 2.20× | **55%** | 2.17 | FULL Kelly |
| 3.0% | 2.39× | **62%** | 2.23 | ratio-optimal (≈ tied with half) |
| 4.0% | 2.30× | 76% | 1.73 | over-leverage penalty |

> **🍼 In plain words** — the "growth per drawdown" ratio barely changes whether you risk 1.2% or 3% per
> trade (it's ~2.2 across that whole band), then falls off a cliff at 4%. So the *ratio* doesn't tell you to
> size small. **But look at the drawdown column:** at the ratio-optimal 3%, the *typical* worst drawdown is
> **62%** — you'd routinely watch most of your account evaporate before it recovers. The ratio is happy
> because the growth is also big; a real trader is not. **The number that should decide your size is the
> absolute drawdown you can actually live through, not the ratio.**

---

## 2 — The honest correction, and why the answer still holds

**I predicted the PnL:DD ratio would push toward the smallest fraction. It didn't — flagging that so the
record is accurate.** The ratio is a *scale-free* quantity; it cannot, by construction, prefer a smaller
absolute drawdown when the growth scales with it. So the Maier-Paape–Zhu intuition ("optimize growth vs
drawdown") does **not** reduce to "the ratio picks the size" — you must optimize growth *subject to an
absolute drawdown cap*, which is the real decision.

**With that cap, the sizing answer is unchanged and now triangulated three ways:**

| Constraint | Points to |
|---|---|
| Edge-uncertainty (Z1: CI floor 0.3%, quarter-Kelly 0.6%) | ~quarter-Kelly |
| Catastrophic-DD probability (Z2: P(50% DD) < ~10%) | ~half-Kelly (1.2%) |
| **Absolute DD tolerance (Z4: half-Kelly ⇒ ~30% median DD; more ⇒ 50–62%)** | **~half-Kelly or below** |

**⇒ ~quarter-to-half Kelly (0.6–1.2% of capital risked per trade), edge-champions only, hard cap.** Every
angle — parameter safety, ruin/drawdown probability, and now the absolute-drawdown-under-PnL:DD view —
converges on the same small, capped fraction. Full Kelly (2.5%) delivers a 55% typical drawdown; that is
the trade a PnL:DD-focused trader should refuse.

---

## 3 — VERDICT: the sizing FRACTION question is CLOSED

**Risk ~quarter-to-half Kelly (~0.6–1.2% of capital per trade), on the edge-champions (4h/2h/1h/15m; not
5m/2m), with a hard contract cap for the un-modeled black-swan.** Start at quarter-Kelly (parameter safety),
move toward half-Kelly only if the edge is confirmed out-of-sample and a ~30% drawdown is acceptable.

- **Vol-targeting (Z3)** is a promising *method* layered on top of this fraction — pending a true OOS test.
- **Caveats stand:** the edge (p≈40%) is a 2025–2026 estimate; the gap parameters are D2/D3 assumptions, not
  live fills. **Nothing is adopted; production byte-identical; $0.**

**→ The sizing workstream (#17) is essentially complete** (fraction closed; one method promising-pending-OOS).
Remaining project threads: **task #16** (assess the user's external data sources) and the **long-GC-history
data decision** (which would give both the frozen GC work and Z3's OOS test a real home).
