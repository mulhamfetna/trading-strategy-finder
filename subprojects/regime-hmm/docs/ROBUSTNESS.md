# Stage 3–4 + Verdict — regime detection adds no DURABLE edge to this (vol-seeking) strategy

**2026-07-15, server.** Tested whether the regime signal yields a robust *policy* improvement, with a
**random-regime control**, **per-year** breakdown, and — for the Jump Model — a **penalty grid**. Filtered/
online (causal) regimes only.

## HMM (4 states) — the inverted policy is WEAK, not robust
Sit-out the model's **calmest** regime (an a-priori realized-vol ranking, not P/L-fitted):

| policy | keep | Ret/DD | vs base 5.52 | beats random | per-year Δ |
|---|--:|--:|--:|--:|---|
| sit-out calmest 1 (−15 trades) | 524 | **5.89** | +0.37 | **81%** (< 95%) | 2024 +0.20, 2025 +0.20, **2026 −0.18** |
| sit-out calmest 2 (−125) | 414 | 4.80 | **−0.72 (hurts)** | 57% | 2025 +1.83, **2026 −2.37** |

The best case removes 15 tiny losing trades for +0.37 Ret/DD, beats only 81% of random removals (not the
>95% "special" bar), and **hurts 2026**. Not a durable edge.

## Jump Model — penalty-sensitive = OVERFITTING (the prior-art's favored method, given a fair shot)
Same sit-out-calmest-1 policy, swept over penalty and #states:

| n | penalty | trades/regime | sit-out-calmest-1 Ret/DD |
|--|--|--|--|
| 2 | 0 / 1 | [39,500] / [38,501] | 5.77 / 5.96 |
| 2 | 3 / 5 / 10 | [387,152]… | **7.12 / 4.15 / 4.38** |
| 3 | 0 / 1 | [23,376,140]… | 6.28 / 5.90 |
| 3 | 3 / 5 / 10 | [337,188,14]… | **7.30 / 4.56 / 5.52** |

Ret/DD ranges **4.15 → 7.30** purely by changing the penalty, and every "good" number (7.12, 7.30) gets
there by **removing 60%+ of the trades** (the vol ranking flips at higher penalties). Selecting the winning
penalty on this one book is textbook backtest overfitting — the exact failure our SOP exists to catch.

## Verdict: NO-GO (for this strategy) — but a valuable diagnostic
- **No robust regime policy improves the box-fusion strategy.** The HMM signal is weak and year-fragile; the
  JM "wins" are penalty-cherry-picked. On the available book (2024–26, n=1) there is **no durable regime edge.**
- **Root cause (the real discovery):** the strategy is **vol-seeking / regime-robust** — its edge lives across
  regimes, best in the *most turbulent* one; the only weak regime is a tiny calm slice that doesn't hold OOS.
  This **mechanistically explains the [TimesFM NO-GO](../../timesfm-fusion/docs/ROBUSTNESS.md)**: a high-vol
  veto backfires because high-vol is where this strategy *earns*. Two independent methods (TimesFM vol-band,
  HMM/JM regimes) reach the same conclusion → high confidence in the *diagnosis*, if not a deployable signal.

## Honest limits / not-definitive
- **n=1 book (2024–26).** A clean test needs a longer trade book (blocked on 2010–23 box levels, same as TimesFM),
  and a *train-period* trade book to pick the regime-to-cut and the JM penalty out-of-sample (we don't have one).
- **Strategy-specific, not a verdict on regime detection generally.** Prior-art shows regime-switching helps
  *allocation* OOS; it just doesn't help THIS vol-seeking intraday breakout. A mean-reversion strategy (which
  dies in trends) is the natural place a regime filter *would* help — a separate hypothesis.

## Salvage / next options
1. **Reframe as SIZING, not veto** — upsize in turbulent regimes / downsize in calm (the strategy's edge is in
   vol) — but this needs the longer book + OOS penalty selection to avoid the overfit shown above.
2. **Apply to a different (vol-hurt) strategy** — e.g. a mean-reversion or the L2 layer — where a regime filter
   has a real mechanism.
3. **Feed the regime as a covariate** into a covariate-aware forecaster (Chronos-2 / Moirai-2) — bridges to the
   TSFM-alternatives backlog.
