# RISK-01 — Position-sizing re-cut on the honest, per-trade-normalized NQ+GC book

**Date:** 2026-07-22
**Branch / Issue:** `fundamental-analysis` · GitHub Issue #3 (re-cut the risk budget on honest drawdowns)
**Depends on:** [GAP-01/02](./GAP-02-gap-aware-fills.md) (honest fills), [GAP-03](./GAP-03-reoptimization-before-after.md) (the adopted champions)
**Verdict:** The honest, correctly-normalized risk budget is a **broad flat plateau ≈0.1–0.8% of capital risked per trade**; the exact "optimum" is Monte-Carlo noise. **Re-optimizing the champions did not change it** — deployed and adopted books are statistically indistinguishable for sizing. Recommended operating point: **~0.25–0.5% risk-per-trade, hard ceiling ~1%.**

---

## 1. The task, in one paragraph

We size positions as a fraction *f* of capital risked per trade (a full hard-stop-out loses *f* × capital).
Earlier sizing work (the Z-series) recommended roughly "quarter-to-half Kelly." Two things made that number
untrustworthy: (a) it was derived on the **too-optimistic** pre-[GAP](./GAP-02-gap-aware-fills.md) engine
(drawdowns ~10% understated), and (b) it used a **hardcoded 40-point stop** to normalize every trade —
the same silent-default class as [BUG-01](./BUG-01-sizing-studies-ran-the-wrong-strategy.md). Issue #3 re-cuts
the budget honestly: real gap-aware fills, each trade normalized by **its own** champion hard stop, pooled
across **both** markets' [adopted champions](./GAP-03-reoptimization-before-after.md).

## 2. Method (so it reproduces)

- **Ledger:** for each edge timeframe `4h/2h/1h/15m` of **NQ and GC**, run the champion through the honest
  engine (`gap_fills=True`, `--ind-1min`) and collect every trade's P&L in points. Normalize each trade by
  **its own champion hard stop**: `R = pnl_points / sl_hard`, so a full stop-out ≈ −1 "risk unit" and *f*
  is a **true fraction of capital**. (Stops are read **strictly** — a missing stop raises, never defaults;
  every stop used is printed.)
- **Two books:** DEPLOYED (current champions) and ADOPTED (deployed + the 3 verified winners: NQ 1h, NQ 2h,
  GC 15m). Both pooled ≈10,500 trades.
- **Monte Carlo:** bootstrap 4,000 paths × 1,000 trades over a grid of *f*; report median growth, median
  max-drawdown, and their ratio (**PnL:DD** — our accepted objective, return per unit of worst drawdown).
  A synthetic fat-tail gap overlay (Pareto α=3 on 5% of stop-outs) is kept **identical** to the established
  method, so the only changes vs the old study are: honest fills, per-TF normalization, +GC, new champions.
- **Noise check (mandatory for a positive result):** re-locate the PnL:DD peak across **8 independent MC
  seeds**. A real optimum stays put; a wandering peak means the "optimum" is noise on a flat plateau.

## 3. Results

**Per-timeframe honest ledger** (note how different the real stops and stop-out rates are — this is exactly
what the old fixed-40 normalization erased):

| Market·TF | hard stop (pts) | trades | stop-outs | expectancy (pts/trade) |
|---|---|---|---|---|
| NQ 4h | 151.4 | 445 | 63 | +8.23 |
| NQ 2h *(adopted→reopt)* | 86.2 | 507 | 171 | +5.86 |
| NQ 1h *(adopted→reopt)* | 94.4 | 913 | 138 | +1.08 |
| NQ 15m | 53.1 | 1,993 | 77 | +0.63 |
| GC 4h | 57.5 | 720 | 1 | +1.19 |
| GC 2h | 13.3 | 807 | 445 | +0.54 |
| GC 1h | 21.3 | 1,305 | 16 | +0.86 |
| GC 15m *(adopted→reopt)* | 8.0 | 3,805 | 525 | +0.10 |

**Monte-Carlo sizing curve (seed 0), both books:**

| f / trade | DEPLOYED growth | DEPLOYED maxDD | DEPLOYED PnL:DD | ADOPTED growth | ADOPTED maxDD | ADOPTED PnL:DD |
|---|---|---|---|---|---|---|
| 0.2% | 1.037× | 4.0% | 0.93 | 1.039× | 4.3% | 0.92 |
| 0.4% | 1.073× | 7.9% | 0.92 | 1.078× | 8.4% | 0.92 |
| 0.6% | 1.109× | 11.5% | **0.94** | 1.114× | 12.6% | 0.91 |
| 0.8% | 1.140× | 15.4% | 0.91 | 1.155× | 16.4% | **0.95** |
| 1.0% | 1.170× | 18.9% | 0.90 | 1.181× | 20.3% | 0.89 |
| 1.5% | 1.249× | 27.4% | 0.91 | 1.243× | 29.3% | 0.83 |
| 3.0% | 1.378× | 48.7% | 0.78 *(growth-opt)* | 1.362× | 51.9% | 0.70 *(growth-opt)* |

## 4. The noise check kills the naive headline

Seed 0 alone would say "deployed optimum 0.6%, adopted optimum 0.8% → adopted lets you size up 33%." That
is **wrong**. Across 8 independent seeds the peak location wanders:

| Book | PnL:DD peak *f* per seed (%) | Flat plateau (mean ratio within 3% of best) | best mean ratio |
|---|---|---|---|
| DEPLOYED | 0.6, 0.3, 0.8, 0.4, 1.2, 1.2, 0.1, 0.1 | **0.1% – 0.8%** | 0.938 |
| ADOPTED | 0.8, 0.1, 0.3, 0.3, 0.1, 1.2, 0.8, 0.8 | **0.1% – 0.8%** | 0.935 |

The peak has no stable location — the PnL:DD ratio is a **broad flat plateau (~0.94)** from ~0.1% to ~0.8%.
And the two books' best mean ratios are **0.938 vs 0.935**: statistically indistinguishable, with the adopted
book if anything a hair *lower*. **Re-optimizing the champions did not raise the risk budget.** The
per-trade tail (a full stop-out can be 8–150 points, worsened by gaps) dominates any edge refinement — the
same "the fat per-trade tail defeats every edge" pattern seen across this project.

Why the plateau is flat at low *f*: at small fractions both growth and drawdown scale ≈linearly with *f*, so
their ratio is ≈constant. PnL:DD therefore **caps the upper bound** (it degrades hard above ~1%, where median
drawdown blows past 20%) but does **not pin a single optimum** below that. Choosing within the plateau is a
risk-appetite decision, not an optimization result.

## 5. Recommendation

- **Risk budget: ~0.25–0.5% of capital per trade** (each trade risking its own hard stop) — the lower-to-mid
  plateau, a balanced growth/drawdown point. **Hard ceiling ~1%**; above it PnL:DD falls and median drawdown
  exceeds 20%. Full "Kelly" (~3%) is far too aggressive (≈50% median drawdown) for a PnL:DD trader.
- **Do NOT size up for the adopted champions.** The re-optimization improved P&L and out-of-sample results
  (see [GAP-03](./GAP-03-reoptimization-before-after.md)) but is indistinguishable for *sizing*. Apply the
  same budget to both books.
- This *f* is a **true per-trade capital fraction** and supersedes the old ~0.6–1.2% figure, which was in
  "per-40-point" units (the STOP=40 bug) and is **not comparable**.

## 6. What went well / what to watch

- **Went well:** the per-TF normalization fix made *f* mean what it says; the mandatory noise check caught a
  spurious 33% "size-up" that seed 0 alone would have shipped — exactly the dumb-control/noise discipline the
  project runs on.
- **Watch (caveats, honest):**
  1. **Raw stop-to-stop ledger.** Following the established Z-series method, the ledger applies entry + SL/TP/
     flip only — **not** the champions' time-caps or drawdown breaker — so its trade counts (~10.5k) exceed the
     capped book's. It captures the per-trade *risk distribution* (what sizing needs), but a cap-aware ledger
     is a worthwhile refinement before treating 0.25–0.5% as final.
  2. **PnL:DD is nearly scale-invariant at low f**, so it bounds rather than pins the fraction; the operating
     point is a risk-appetite choice within the plateau.
  3. **iid bootstrap** ignores cross-instrument correlation and serial clustering of stop-outs (GC 2h/15m
     stop out >50% of the time) — real drawdowns can cluster worse than the median suggests.

## 7. Next

Feeds **v5.1.0** alongside GAP-01/02/03: gap-aware fills + adopted champions + this honest sizing budget.
Optional refinement (own issue): cap-aware sizing ledger + a correlation-aware (block-bootstrap) drawdown model.
