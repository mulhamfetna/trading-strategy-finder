# Phase F — Volatility / Range Forecasting (the productive pivot)

> Triggered by the synthesis in `23_is_return_useful_synthesis.md`: returns are useless for
> *direction* but gold for *magnitude*. Phase F forecasts the magnitude — the thing that's actually
> predictable (range ACF 0.56) and actually useful (feeds the live engine's stops + sizing).
>
> **Two passes (user-locked):**
> - **F1 — Range from 4h data** (this pass): quick, uses only `NQ_4h.csv`, no GPU/torch → no crash risk.
> - **F2 — Realized volatility from 1-min data** (second pass): more accurate vol; needs 1-min CSV.

---

## Why this is the right pivot (one paragraph)

The whole price-forecasting arc (Phases 1–D) proved the *direction* of the next bar is ~unpredictable (autocorrelation 0.07) and no model beats naive. But the *size* of the next bar — its range / volatility — has autocorrelation 0.30–0.56 because volatility clusters. That signal is real, and it's exactly what the dual-SL/TP engine needs: how far to place a stop, how big to size a position. Phase F forecasts size, scored honestly as lift-over-naive, with classical lightweight models (no torch → no OOM repeat).

---

## F1 — Range forecasting on 4h data

**Target:** next-bar **range in points** `range_t = high_t − low_t`. (Points, not normalized, because that's directly the unit a stop-distance is set in. We'll also log the normalized `(high−low)/open` for cross-regime comparison.)

**Causality:** at decision time = open of bar t, we forecast that bar's range using only bars `≤ t−1`. Same no-look-ahead discipline as the price study.

**Models (all scored on the same range target):**

| Model | What it is | Why include |
|---|---|---|
| **naive-range** | `r̂_t = range_{t−1}` | the baseline to beat (range's own persistence) |
| **EWMA-range** | exponentially-weighted mean of past ranges (RiskMetrics λ=0.94) | the classic volatility baseline; often the model to beat |
| **HAR-range** | regression on avg range over last 1, 6, 30 bars (Heterogeneous AutoRegressive) | the standard realized-volatility model; captures short+medium+long memory |
| **GARCH(1,1)** | models return variance; forecast σ_t, scale to range via fitted `c = mean(range)/mean(σ)` | the textbook volatility-clustering model |

**Metrics:**
- **RMSE / MAE on range** (points) — dollar-scale miss.
- **Lift over naive-range** — the headline (does the model beat range-persistence?).
- **QLIKE** — the standard volatility-forecast loss (penalizes under-prediction of vol more than over-prediction; robust to the fact that the "true" vol is latent).
- **Correlation(pred, actual range)** — signal check.

**Walk-forward:** train on 2025, test on 2026, refit GARCH every 20 bars; EWMA/HAR/naive update every bar (cheap).

**Success criterion:** at least one model beats naive-range with **positive lift** (unlike the price study, where everything was negative). Given range ACF 0.56, we expect EWMA/HAR to win clearly — that would be the first genuine "beats naive" result in the whole project.

**Deliverables:** `scripts/15_range_forecast.py`, `outputs/15_range_*.csv`, `outputs/range_leaderboard.csv`, `plots/range_*.png`, `notes/25_phase_F1_results.md`.

---

## F2 — Realized volatility from 1-min data (second pass)

**Idea:** the *true* volatility of a 4h bar is best measured by summing squared 1-minute returns inside it (**realized variance**). This is far more accurate than the high−low range proxy.

**Plan (after F1):**
1. Locate / wire in the 1-min NQ CSV (the main project already references one for the dual-timeframe engine — check `data/`).
2. For each 4h bar, compute **realized volatility** `RV_t = √(Σ r²_1min)` over its constituent minutes.
3. Re-run the F1 models with `RV` as both a **more accurate target** and a **feature** (HAR-RV is literally built on realized vol).
4. Compare: does 1-min-based RV forecasting beat the 4h-range forecasting from F1? (Expected: yes — RV is a cleaner signal.)

**This is where 1-minute data finally earns its keep** (per `16_..._explained.md` §5 and `17_ohlc_will_it_help.md`): not for price direction, but for accurate volatility measurement.

**Deliverables:** `scripts/16_realized_vol.py`, `outputs/16_rv_*.csv`, `notes/26_phase_F2_results.md`.

**Dependency / risk:** needs the 1-min CSV. If unavailable in the subproject, F2 is blocked until the file is provided — F1 stands alone and is the immediate deliverable.

---

## What Phase F feeds back into the live system

A working range/volatility forecast is directly actionable in `simple_strategy`'s dual-SL/TP engine:
- **Stop-loss distance** ∝ predicted range (wider stops in turbulent regimes, tighter in calm).
- **Take-profit distance** likewise.
- **Position sizing** ∝ 1/predicted-volatility (constant-risk sizing).
- **Regime gate** — only trade (or flip) when predicted volatility is in a favorable band.

Unlike a price forecast (which this project showed can't be made accurate), a volatility forecast is both achievable and immediately useful — closing the loop with the actual trading system.

---

## Status

- **F1:** in progress (this pass).
- **F2:** queued, pending 1-min CSV.
- **Darts Phase D (price):** paused, awaiting GPU server — unrelated to Phase F.
