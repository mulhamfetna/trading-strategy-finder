# Study — Fixed-window SL/TP sub-optimizer + can market-state PREDICT the best SL/TP (point or distribution)?

**Date:** 2026-06-15 · **Prompted by:** "the rolling 3-month optimizer generated noise — repeat on FIXED
quarters, export best SL/TP + price/data, then find a relationship (absolute, or a probability distribution
with an error margin) mapping SL/TP to price/indicators; re-evaluate on the moving window too." · **Scripts:**
`fixed_window_subopt.py`, `relation_fit.py`. · **Data exported:** `results/fixed_window_subopt.csv` (9 windows,
best + near-best band), `results/fixed_window_trials.csv` (3,600 trials), `results/rolling_band_subopt.csv` (27).

> **TL;DR — NO-GO holds, now tested four ways.** (1) Fixed quarters did **not** reduce the noise — the per-window
> best SL/TP still swing wildly (sl_soft 151→447, tp 35→680, sl_hard 217→905) on 5–34 trades/window. (2) A
> distribution/band framing was captured (it doesn't fix the core problem). (3) A multi-feature map **overfits**
> (negative OOS skill). (4) The one tantalizing signal — best-SL vs same-quarter price-change, r **−0.81**, OOS
> skill **+0.49** — is **look-ahead**: it describes the quarter in hindsight. The **causal (lagged)** version,
> using only the *previous* quarter's data, **collapses to −2.23 skill (worse than fixed).** Rolling windows show
> no skill either. **You can always quote "SL ± margin", but conditioning on causal features does not shrink the
> margin below the global fixed value — no usable predictive certainty exists in this data.**

---

## 1. What was run
- **Fixed quarters** (non-overlapping, complete): 2024 Q1–Q4, 2025 Q1–Q4, 2026 Q1 = **9 windows**. Per window,
  an Optuna TPE study (400 trials) over the widened SL/TP bounds, on the frozen champion layer (gate + indicators
  + breaker held fixed) — identical machinery to the rolling study.
- **Distribution capture:** for every window we kept **all 3,600 completed trials**, and defined the *near-best
  band* = trials within 85% of the window's best P/L → its mean ± std ± p10/p90 = the "probability distribution
  of good SL/TP" the request asked for.
- **Relationship fit** (`relation_fit.py`): features = `price_change_pct, range_pct, atr_mean, harv_mean,
  price_mean`. Targets = best SL/TP and band centers. Evaluated **leave-one-window-out (LOWO)** vs the only honest
  baseline — *predict the global mean* (= using a single fixed value). Skill = 1 − SSE(model)/SSE(mean); >0 means
  features beat fixed OOS. Re-run on the **rolling** windows too.
- **Causal check:** re-fit predicting quarter *t* from quarter *t−1* features (the only information available
  when you'd actually set the stop).

## 2. Results

### 2a. Fixed windows did not tame the noise
Best SL/TP per quarter (400 trials): sl_soft **150.8 → 446.8**, sl_hard **216.9 → 905.0**, tp **35.1 → 680.2**,
on **5–34** trades/window. Dispersion is as large as the rolling study — the noise is from *few trades per
window* (a noisy argmax), which fixed tiling does not change. (Fixed tiling does make the 9 windows *independent*,
which is statistically cleaner, but gives fewer points to fit.)

### 2b. Multi-feature map → overfits (LOWO, fixed windows)
| target | uncond σ | OOS resid σ | σ ratio | OOS skill | verdict |
|---|--:|--:|--:|--:|---|
| best_sl_soft | 108 | 299 | 2.76 | **−6.69** | NO gain |
| best_sl_hard | 227 | 242 | 1.07 | −0.23 | NO gain |
| best_tp | 209 | 246 | 1.17 | −0.70 | NO gain |
5 features on 9 points → wild extrapolation. In-sample r looks strong (sl_soft vs price-change **−0.81**, tp vs
vol **−0.66**) but does not generalize.

### 2c. Single best feature (steelman) — contemporaneous vs CAUSAL (lagged)
| relation | in-sample r | OOS skill (same-quarter) | OOS skill (lagged t−1) |
|---|--:|--:|--:|
| best_sl_soft ~ price_change | −0.81 | **+0.49** | **−2.23** |
| best_sl_hard ~ price_change | −0.75 | +0.38 | −2.30 |
| best_sl_soft ~ ATR | — | — | +0.08 (trivial) |
| best_tp ~ HAR-RV vf | −0.66 | +0.09 | −1.58 |
| best_tp ~ ATR | −0.63 | +0.03 | −1.58 |

**The crux:** the only strong predictability is **contemporaneous** — the best SL fits the *realized* quarter
(big down-quarter → wide optimal stop). That is **hindsight, not forecast.** Restricting to **causal** (prior-
quarter) information — what you'd have when setting the stop — every relationship **loses to the fixed value**.

### 2d. Rolling windows (27) — no skill either
best_sl_soft skill −0.21, best_tp −0.29, sl_hard marginal +0.03; price-change correlation only −0.35 (vs −0.81
fixed). The fixed-quarter correlation does **not** replicate under rolling tiling — a robustness red flag that the
fixed-quarter signal is tiling-specific, not a stable law.

## 3. Answering the request's deep question
*"Can't we find a probability distribution — no matter how many parameters — that produces a value with an error
margin / certainty?"*
- **You can always produce a distribution** (we did: the near-best band, mean ± std per window). But "useful
  certainty" means the **conditional** error margin (given features) is **narrower** than the **unconditional**
  one (just the fixed value ± its spread). Here the **σ ratio ≥ 1** for every causal target → conditioning on
  market state **does not shrink the margin**. More parameters make it *worse* (overfit), not better.
- So the probabilistic framing is sound and was tested — it simply finds **no information**: the best SL/TP is
  not causally predictable from price/vol state in this data beyond what the single fixed number already encodes.

## 4. Verdict & caveats
- **Confirms the NO-GO** from `STUDY_relative_feasibility.md`, now via four independent angles (fixed tiling,
  distribution band, multi-feature map, single-feature causal test) + a rolling cross-check.
- **Also recall:** even *if* the best SL/TP were predictable, the Stage-2 study + councils already showed that
  *using* dynamic SL/TP did not beat fixed on profit (only reduced drawdown). Predicting the label ≠ improving live P/L.
- **Caveats:** n=9 fixed windows is tiny (the +0.49 contemporaneous skill is itself fragile); only price/vol
  features were tested, not all 8 indicator readings — but the **causal collapse** (2c) and the rolling null (2d)
  make richer features low-odds, and the look-ahead distinction would apply to them too. A genuinely different
  result would need **far more history** (multi-year, multi-regime) and a **causal, lagged, OOS** protocol — and
  must still be judged on **live P/L**, not on fitting the noisy per-window optimum.
- **Decision unchanged:** keep the FIXED champion; refresh by periodic re-optimization (cadence measured, trials
  capped). The dynamic/derived SL/TP avenue stays closed on the evidence.

## 5. Reproduce
`python3 optimize/sub/fixed_window_subopt.py --trials 400` (fixed) and `--rolling` (rolling band) →
`python3 optimize/sub/relation_fit.py fixed|rolling`. CSVs in `optimize/sub/results/`.
