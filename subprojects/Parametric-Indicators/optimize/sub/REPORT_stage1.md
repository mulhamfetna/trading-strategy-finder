# Sub-Optimizer — Stage 1 Results & Read (SL/TP per rolling 3-month window)

**Date:** 2026-06-13 · branch `dev` · spec `/sub_optimizer.md` · plan `optimize/ACTION_PLAN_sub_optimizer.md`
**Status:** Stage 1 COMPLETE → **HARD STOP for review before Stage 2** (per the plan).
**Table:** `optimize/sub/results/subopt_table.csv` (27 rows).

---

## 1. What was run (method)
- **Frozen** the `wsi1m_4h` champion (TF 4h · gate 86.9 · dd_limit 4747 · cd 0 · flip off · k1 · 8 indicators);
  searched **only** `sl_soft, sl_hard, tp`.
- **Freeze-once:** the champion's signal + gate layer computed ONCE over the full 29-month series
  (2024-01→2026-05), correct warm-up; **proven byte-exact** vs the canonical recompute
  (`check_freeze_parity.py`: pnl/dd/n/win/locks all match).
- **Rolling 3-month windows stepped monthly** → 27 windows (anchor 2024-03 … 2026-05).
- **Widened bounds** (3× the full-history caps) so high-price windows aren't clipped; **400 Optuna
  trials/window**; objective = window P/L with min-trades guard (≥3); breaker frozen at the champion's.
- Engine path = the parity-locked `core.backtest_metrics` (`fast_backtest` + breaker) — champion behaviour exact.

**Reference baseline** (fixed champion SL/TP over the full 29 months): **P/L $108,748 · 342 trades · win 62.9% · maxDD $34,411.**

---

## 2. Headline finding — the per-window optima do NOT show a clean price/volatility relationship

| Predictor | r(best_sl_soft) | r(best_sl_hard) | r(best_tp) |
|-----------|----------------:|----------------:|-----------:|
| price_mean | **+0.26** | −0.00 | **−0.30** |
| HAR-RV (vol) | +0.20 | −0.08 | −0.14 |
| ATR(14) | +0.19 | −0.08 | −0.13 |

- **All correlations are weak (|r| ≤ 0.30).** `best_tp` is *negatively* related to price — the **opposite** of
  the premise that TP should widen as price rises.
- **SL/TP as a % of price is not a stable constant either:** sl_soft 1.33 % (CV **0.40**), tp 1.98 % (CV **0.50**).
- **Trades/window: 5–38 (median 18);** 3 low-trade windows (2024-06, 2025-07, 2025-08); 1 bound-clip (2025-08).
- **Degenerate optima appear** where trades are few + bounds wide: e.g. 2026-01/02/03 → tiny TP (~35–66) with
  wide SL, 2024-05 → SL 25. The optimizer exploits a handful of trades to find extreme SL/TP that win
  in-sample — classic per-window overfit.

> **Baby read.** We asked each 3-month window "what SL/TP would have won best here?" and lined the answers up
> against price. They **don't line up** — the answers jump around and don't grow with price (TP even shrinks a
> bit as price rises). With only ~5–38 trades per window, each "best SL/TP" is mostly luck-fitting, not a real
> law. So a naive "SL/TP = formula(price)" would be fitting noise.

---

## 3. What this means for Stage 2 (which is HELD for your decision)
The raw monthly optima are **too noisy to fit a trustworthy SL/TP-vs-price (or vs-volatility) law** as-is.
A naive regression would have low R² and could *hurt* out-of-sample. Options to weigh at the Stage-2 gate:

1. **Robustify the per-window objective** — penalise extreme SL/TP, require stability across sub-folds within
   the window, or add a min-trades floor higher than 3 — so each window's "best" is a *stable* optimum, not a
   lucky one. Then re-examine the relationship.
2. **Theory-driven ratio instead of fitting noise** — set SL/TP as a fixed **ATR/volatility multiple** (which
   scales with the range automatically) and *validate* it OOS, rather than regressing the noisy optima. This
   directly serves the premise ("range was smaller back then") without trusting per-window points.
3. **Aggregate before fitting** — smooth the optima (rolling median) and fit the trend, accepting it's coarse.
4. **Reconsider necessity** — the fixed champion already makes **$108,748 / 62.9 % win** across 2024-26; a
   dynamic rule must beat that **out-of-sample** (the S2.4 gate) or it isn't worth the added complexity.

My recommendation: **(2)** — define SL/TP as an ATR-multiple and OOS-validate vs the fixed champion — because
the Stage-1 data shows the per-window optima themselves are not a reliable signal to fit.

---

## 4. Caveats / limitations (carried from the plan, now evidenced)
- Few trades/window → noisy optima (**confirmed**: degenerate extremes appear).
- Widened bounds let the optimizer reach extreme SL/TP → amplifies the overfit (only 1 hit the cap, so bounds
  are wide enough; the problem is *trade count*, not bound width).
- Single-objective P/L (no DD penalty beyond the frozen breaker) rewards a few big wins — a robustness-weighted
  objective (option 1) would temper this.
- Gate threshold frozen to the champion's full-series percentile; warm-up correct (freeze-once).

---

## 5. Deliverables
- `optimize/sub/results/subopt_table.csv` — the 27-window table (price/ATR/HAR-RV + best SL/TP + P/L/DD/n/win +
  SL/TP-%-of-price + clip flag).
- Code: `data_2024_2026.py` (bundle), `windows.py` (rolling windows), `suboptimizer.py` (freeze-once +
  per-window search), `check_freeze_parity.py` (correctness gate).

## 6. ⏸ HARD STOP
Stage 1 is done. **Review the table + this read, then choose the Stage-2 path** (signal + robustification
approach). No Stage-2 modelling/engine change until you decide.
