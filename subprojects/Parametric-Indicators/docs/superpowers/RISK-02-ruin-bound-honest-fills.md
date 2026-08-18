# RISK-02 — the risk budget is bounded by SINGLE-TRADE RUIN, not by drawdown

**Date:** 2026-07-29
**Issue:** #3 (re-cut the position-sizing risk budget on gap-aware drawdowns)
**Supersedes:** [RISK-01](./RISK-01-sizing-recut-honest.md) (2026-07-22) — right method, wrong inputs
**Status:** complete. Verdict below is measured on the deployed book, honest fills, cap-aware.

---

## Verdict in one line

**Size the book at ≤0.40% of capital per trade — but the constraint that binds is not drawdown, it is a
single natural-gas trade that can lose 183× its own stop. Size NG at 0.3% and everything else at 1.0%,
and the book-wide limit rises from 0.40% to 1.0%.**

RISK-01's operating range (0.25–0.5%) survives. Its **hard ceiling of ~1% does not**: at f=1% the whole
book has a **1.67% chance of outright ruin**, not merely a deep drawdown.

---

## 1. Why RISK-01 had to be redone

Its method was sound and is reused here unchanged (per-trade normalisation by each champion's own hard
stop; the mandatory multi-seed noise check). Three inputs were wrong:

| | RISK-01 | RISK-02 |
|---|---|---|
| champion set called "deployed" | `wsh4_*` — **retired since 2026-07-14** | `best_*`, resolved via `payload._instrument_champions_path()` |
| slots covered | 8 (NQ+GC × 4 edge TFs) | **54** (9 markets × 6 TFs) |
| NG | **absent** | isolated and reported separately, as #3 asked |
| time-caps / breaker | not applied ("a worthwhile refinement") | **applied** — each champion's own cap |

All 54 slots differ between `wsh4_*` and `best_*`. Many differ only in precision, but many differ
materially — NQ 2h `sl_hard` 86 → 182, NQ 15m cap `none` → `eod`. Caps are not a detail here: on NQ 4h,
**213 of 541 trades exit on the cap**, and expectancy moves from +0.054R to +0.031R. A cap truncates
exactly the long losing holds that drive the tail sizing depends on.

## 2. The measurement that changes the answer

Pooled over all 54 deployed champions, honest fills, 128,443 trades:

> **21.8% of trades lose MORE than their hard stop.** 0.36% lose more than 2×. The worst loses **183×**.

That single fact invalidates the inherited Z2/Z4 sizing model. Pre-GAP-01 the engine filled a gapped stop
*at the line*, so no trade could lose more than 1 risk unit; with bounded loss, median drawdown is a
sufficient constraint and the Z2/Z4 machinery is correct. With honest fills the loss is unbounded, and
two assumptions inside that machinery become fatal:

- wealth is computed as `cumprod(max(1 + f·R, 1e-9))` — a bankrupting trade becomes "wealth ≈ 0, now
  keep compounding". **Ruin is not absorbing, so it never registers as ruin.**
- the statistic reported is the **median path**, which by construction never experiences the rare
  catastrophic trade. The tail that decides sizing is exactly what the average discards.

Run faithfully on the honest ledger, the old model returns an absurdity: PnL:DD rising monotonically to
the edge of the grid, recommending **f = 4.0% at 72% median drawdown**. That is not an optimum, it is an
objective that cannot see ruin.

## 3. The ruin-constrained result

Bankruptcy made absorbing; ruin and deep-drawdown probabilities reported instead of hidden behind a
median; averaged over 4 seeds.

**Whole deployed book** — worst trade −182.84R, so `f_survive = 1/183 = 0.547%`:

| f | med growth | med dd | **P(ruin)** | P(dd≥50%) |
|---|---|---|---|---|
| 0.20% | 1.235× | 5.2% | **0.00%** | 0.0% |
| 0.40% | 1.512× | 10.3% | **0.00%** | 1.7% |
| 0.60% | 1.835× | 15.2% | **0.85%** | 2.7% |
| 1.00% | 2.632× | 24.3% | **1.67%** | 5.6% |
| 2.00% | 5.592× | 44.2% | **3.91%** | 34.4% |
| 4.00% | 13.148× | 72.3% | **10.16%** | 96.5% |

Largest f with **no ruin** and P(dd≥50%) < 5%: **0.400%**.

**Excluding NG** — worst trade −36.37R, `f_survive` = 2.749%:

P(ruin) is **0.00% at every fraction up to 2.0%**. Largest safe f: **1.000%** — two and a half times the
whole-book figure.

## 4. NG alone sets the limit for the entire book

| market | trades | worst R | f_survive | safe f |
|---|---:|---:|---:|---:|
| YM | 8,894 | −2.12 | 47.3% | 2.0% |
| ES | 10,620 | −2.93 | 34.2% | 1.5% |
| GC | 15,871 | −9.08 | 11.0% | 1.0% |
| RTY | 9,858 | −14.99 | 6.7% | 1.0% |
| CL | 13,558 | −17.96 | 5.6% | 1.0% |
| SI | 18,267 | −23.06 | 4.3% | 1.0% |
| NQ | 6,615 | −24.14 | 4.1% | 1.0% |
| HG | 21,671 | −36.37 | 2.7% | 1.0% |
| **NG** | 23,089 | **−182.84** | **0.547%** | **0.3%** |

Every other market tolerates ≥2.7%. NG tolerates 0.55%. Issue #3's instruction to "treat NG separately"
is not a nicety — **applying one book-wide fraction lets NG cut every other market's size by 2.5×.**

## 5. The trade that does it — verified, not assumed

The entire conclusion rests on one trade, so it was traced to the raw data:

| | |
|---|---|
| slot | NG 5m, hard stop **0.001017** |
| entry | short at **3.368** — the real close of the 5m bar ending Fri 2025-01-03 16:55 |
| exit | **3.554**, Sun 2025-01-05 18:00, `STOP_LOSS_HARD` |
| gap | **+5.52%** across the weekend reopen |
| loss | 0.186 points = **182.84 risk units** |

It is a short held over the weekend into a 5.5% natural-gas gap. The entry price is a price that genuinely
traded; the hard stop (0.03% of price) was never going to be relevant to a 5.5% gap. **This is real
weekend gap risk, not a data artefact.**

That is the mechanism in one line: **NG's champion stops are an order of magnitude tighter than NG's
overnight gap distribution, so on NG the "hard stop" does not bound the loss at all.**

## 6. Recommendation

1. **Per-market risk fractions, not one book-wide number.** NG **0.3%**; NQ/GC/SI/HG/CL/RTY **1.0%**;
   ES 1.5%, YM 2.0%. This is the whole finding: one number costs 2.5× size on eight markets to protect
   against one.
2. **If a single fraction must be used, it is 0.40%** — not RISK-01's ~1% ceiling, which carries a 1.67%
   chance of ruin.
3. **Stop quoting median drawdown as the sizing constraint.** Under honest fills report **P(ruin)** and
   **P(dd≥50%)**. Median drawdown was the right statistic only while stops actually held.
4. **The real fix for NG is not smaller size, it is the stop.** A 0.001 stop on a market that gaps 0.19
   over a weekend is not a risk control. Widening NG's stop, or refusing to hold NG over a weekend
   reopen, would recover far more than sizing down ever can. That is a strategy change and belongs in
   its own issue.

## 7. What went well / what to watch

- **Went well:** reusing RISK-01's normalisation and noise check meant only the inputs had to change;
  the cap-aware ledger removed its largest caveat; the driving trade was traced to raw bars rather than
  trusted.
- **Watch:**
  1. **iid bootstrap** — still ignores cross-instrument correlation and clustering of stop-outs. Real
     drawdowns can cluster worse than these medians suggest; a block bootstrap would tighten it.
  2. **Equal weighting** — pooling treats every slot's trade as one draw, i.e. equal capital per trade
     across 54 slots. A different allocation changes the pooled tail.
  3. **One trade drives the whole-book bound.** It is verified and real, but n=1 on the extreme: the
     honest reading is "NG can do this", not "NG does this 0.004% of the time" — the tail is estimated
     from a handful of weekend gaps, so treat 0.3% as an upper bound on NG, not a precise optimum.
  4. The synthetic Pareto gap overlay from Z2/Z4 is **off** here by default: with honest fills the real
     gaps are already in the ledger, so applying it would double-count them. Both are reported in
     `risk_recut_v2.py` output for comparison.

## 8. Reproduce

`optimize/reports/risk_recut/risk_recut_v2.py` (ledger + Z2/Z4-style curve, cap-aware/cap-blind) and
`risk_ruin_v3.py` (the ruin-constrained bound). Champion set is resolved, never named; stops are read
strictly and every stop, cap and file used is printed.
