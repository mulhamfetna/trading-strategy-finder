# SIZING · 02 — Z1: the Kelly fraction on our ledger (small, and hugely uncertain)

**The first on-data sizing test. SIZE-01's illustrative formula gave f\* ≈ 6.7% using an assumed 44% win
rate. Computed on our REAL NQ champion ledgers, full Kelly is **2.5%** of capital-risked-per-trade pooled —
and its 95% confidence interval is **[0.3%, 4.4%]**. The research's loudest warning (Kelly is dominated by
edge-estimation error) is made concrete: our realized edge is thinner and far more uncertain than the
illustration, so the honest size is a *small fraction* of an already-small number.**

Date: 2026-07-15 · Branch `fundamental-analysis` · Code: `optimize/fundamentals/study_kelly.py` · Raw:
[`results/kelly_nq.txt`](results/kelly_nq.txt) · 7,356 NQ champion trades.
`f` = fraction of capital **risked per trade** (a full stop-out loses `f × capital`).

---

## ⚡ THE 60-SECOND VERSION

| | |
|---|---|
| **Full Kelly, pooled** | **f\* = 2.5%** (numeric, dispersion-aware; binary formula 2.2%) |
| **95% CI on f\*** | **[0.3%, 4.4%]** — the edge is so uncertain the safe fraction could be as low as 0.3% |
| **Realized win rate** | **39.8%** (not the illustrative 44%) — the thinner edge is why f\* is 2.5%, not 6.7% |
| **5m & 2m champions** | **f\* ≈ 0** — win% × payoff gives no Kelly edge; do **not** size them up |
| **Honest size** | quarter-Kelly ≈ **0.6%**, bounded by the **0.3%** CI floor, **then** a tail/gap haircut + hard cap |

---

## 1 — Per-champion Kelly, and the uncertainty

| TF | n | win% | B (w/l) | full Kelly f\* | **95% CI** | half | quarter |
|---|---|---|---|---|---|---|---|
| 4h | 642 | 41.9% | 1.61 | **6.0%** | [0.0%, 12.9%] | 3.0% | 1.5% |
| 2h | 616 | 40.3% | 1.64 | 4.1% | [0.0%, 11.0%] | 2.1% | 1.0% |
| 1h | 1157 | 41.4% | 1.61 | 5.3% | [0.1%, 10.1%] | 2.7% | 1.3% |
| 15m | 1685 | 40.1% | 1.60 | 3.0% | [0.0%, 6.8%] | 1.5% | 0.7% |
| **5m** | 988 | 37.9% | 1.64 | **0.0%** | [0.0%, 5.1%] | 0.0% | 0.0% |
| **2m** | 2268 | 38.8% | 1.59 | **0.1%** | [0.0%, 3.9%] | 0.1% | 0.0% |
| **POOLED** | **7356** | **39.8%** | **1.61** | **2.5%** | **[0.3%, 4.4%]** | 1.2% | 0.6% |

> **🍼 In plain words** — three things jump out. **(1)** Even at *full* Kelly the number is small (2.5% of
> capital risked per trade) because the edge is tiny. **(2)** The confidence interval is *enormous relative
> to the estimate* — nearly every champion's CI reaches down toward 0%, meaning the data cannot rule out
> that the true edge (and thus the safe bet) is near zero. **(3)** The fastest champions (5m, 2m) have a
> Kelly fraction of **essentially zero** — their ~38% win rate against a 1.6 payoff barely breaks even, so
> Kelly says *don't add size to them at all.*

---

## 2 — Why this matters: the research's warning, made concrete

SIZE-01 K3: *Kelly is ~10–20× more sensitive to the EDGE than to variance, and errors in the win rate are
the most damaging.* Here it is, live:

- The illustrative p = 44% gave f\* ≈ 6.7%; our **realized** p = 39.8% gives f\* ≈ **2.5%.** A ~4-point
  change in the win-rate estimate more than **halved** the Kelly fraction.
- And p itself is estimated on **2025–2026 only** — the fluke window this whole project keeps flagging. The
  bootstrap CI [0.3%, 4.4%] captures the *sampling* uncertainty; it does **not** capture regime risk (that
  p could simply be lower going forward), which would push f\* lower still.

**Conclusion: sit well below full Kelly for the edge alone.** The parameter-safety floor (the CI lower
bound) is **0.3%**; quarter-Kelly is **0.6%.** Anything near full Kelly (2.5%) is betting that a
fluke-window win rate is exactly right — precisely the mistake K3 warns against.

---

## 3 — VERDICT & next

**The honest sizing endpoint is small and bounded:** risk on the order of **0.5–1% of capital per trade**
(≈ quarter-Kelly, floored by the CI), **only on the champions with a real edge** (the slower TFs; not 5m/2m),
**with a further tail/gap haircut and a hard contract cap still to come.** This is deliberately conservative
— and correctly so: a tiny, uncertain, fluke-window edge on a fat-tailed instrument does not justify size.

This also lands the project's through-line one more time: **the edge is real but small and fragile; the
right response is modest, capped sizing, not leverage.**

| Next | What |
|---|---|
| **Z2** | Simulate the ledger with **gap-through-stop fills** (overlay the D2/D3 EVT tail on the stop) → read off the fraction that holds ruin probability below a threshold (the tail/gap haircut K6 demands, which Z1 has *not* yet applied). |
| **Z3** | A/B **fixed-fractional vs volatility-targeting** contract scaling on the ledgers, net of costs + integer contracts. |
| **Z4** | Recompute for our **PnL:DD** objective (Maier-Paape–Zhu drawdown frontier) instead of raw log-growth. |

**Guardrail (unchanged):** no sizing change ships without Z2 (tail-safe) and Z3 (OOS) — and the prior is a
small fixed fraction with a hard cap. Nothing adopted; production byte-identical; $0.
