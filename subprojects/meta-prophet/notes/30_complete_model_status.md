# Complete Model Status — Every Method, Tested vs Paused vs Blocked

> You asked: *are you sure every model in the reports was actually tested? Are paused trainings
> counted as failed or paused? Make sure LSTM / NBEATS / TFT etc. are real.*
>
> Honest audit below, derived from which **output files actually exist** on disk (an output CSV =
> the model genuinely ran end-to-end). **Three distinct statuses — do not conflate them:**
> - ✅ **TESTED** — ran to completion, produced results.
> - ⏸️ **PAUSED** — never ran (queued in the batch the OOM crash killed); awaiting a GPU server. **Not a failure.**
> - 🚫 **BLOCKED** — attempted but structurally cannot run on this data/stack (documented root cause).

---

## 1. The honest correction up front

- **LSTM (darts-rnn-plain) WAS tested** — it completed and is on the leaderboard (−0.47% vs naive).
- **NBEATS and TFT were NEVER tested** — they were queued right after the run that exhausted memory
  and rebooted the machine (`15_system_crash_postmortem.md`). They produced **no output**. They are
  **PAUSED awaiting a GPU server**, *not* failed.
- **darts-rnn-regressors** also never completed — it hit a real code issue (Darts `RNNModel` needs
  `future_covariates`, not `past_covariates`) AND was in the crashed batch. Status: paused + needs a
  one-line fix.
- **NeuralProphet is BLOCKED, not paused** — a structural incompatibility (it demands a uniform time
  grid; our data has weekend gaps), fully root-caused in `09_neuralprophet_root_cause_report.md`.

So earlier report tables that listed all six Darts cells were describing the **plan**; only the LSTM
cell actually produced a number. This document is the authoritative status.

---

## 2. PRICE / DIRECTION forecasting models (the "can we predict the next price?" question)

| # | Model | Library | Status | Result (lift vs naive) | Output file |
|---|---|---|:--:|---|---|
| 1 | **naive** (previous close) | — | ✅ TESTED | 0.00% (the benchmark) | `01_naive.csv` |
| 2 | **Prophet** (tuned, 40-config CV) | prophet 1.3 | ✅ TESTED | −0.22% | `02_prophet.csv` |
| 3 | **ARIMA** (auto, d=0) | pmdarima 2.1 | ✅ TESTED | −0.26% | `03_arima.csv` |
| 4 | **SARIMAX** (plain) | statsmodels 0.14 | ✅ TESTED | −0.34% | `06_sarimax_plain.csv` |
| 5 | **SARIMAX + 14 regressors** | statsmodels 0.14 | ✅ TESTED | −0.45% | `07_sarimax_regressors.csv` |
| 6 | **StatsForecast AutoARIMA** | nixtla 1.7 | ✅ TESTED | −0.99% | `08_statsforecast_autoarima.csv` |
| 7 | **LSTM (RNN)** plain | darts 0.44 | ✅ TESTED | −0.47% | `09_darts_rnn_plain.csv` |
| 8 | **LSTM (RNN) + regressors** | darts 0.44 | ⏸️ PAUSED | — (code fix: use `future_covariates`) | — |
| 9 | **NBEATS** plain | darts 0.44 | ⏸️ PAUSED | — (crashed batch; awaiting GPU) | — |
| 10 | **NBEATS + regressors** | darts 0.44 | ⏸️ PAUSED | — | — |
| 11 | **TFT** plain | darts 0.44 | ⏸️ PAUSED | — | — |
| 12 | **TFT + regressors** | darts 0.44 | ⏸️ PAUSED | — | — |
| — | **NeuralProphet** (AR-Net) | neuralprophet 0.8 | 🚫 BLOCKED | structural (uniform-grid vs weekend gaps) | `09_neuralprophet_root_cause_report.md` |

**Tested price models: 7** (naive, Prophet, ARIMA, SARIMAX×2, StatsForecast, LSTM).
**Verdict from the 7 that ran: unanimous — none beats naive.** Direction is unpredictable (ACF 0.07).
The 5 paused deep nets would, on the price/direction target, hit the same wall (no signal to learn) —
but that is a *prediction*, not a tested result, and is labelled as such.

---

## 3. VOLATILITY / RANGE forecasting models (the "how big is the next move?" question — the pivot)

| Model | Target | Library | Status | Result (lift vs naive) | Output |
|---|---|---|:--:|---|---|
| **naive-range** | range (4h) | — | ✅ TESTED | 0% | `15_range_forecast.csv` |
| **EWMA-range** | range (4h) | numpy | ✅ TESTED | **+15.3%** | `15_range_forecast.csv` |
| **HAR-range** | range (4h) | numpy | ✅ TESTED | **+16.3%** | `15_range_forecast.csv` |
| **GARCH(1,1)** | range (via σ) | arch 8.0 | ✅ TESTED | −3.5% (wrong-target scaling) | `15_range_forecast.csv` |
| **naive-RV** | realized vol (1-min) | — | ✅ TESTED | 0% | `16_rv_forecast.csv` |
| **EWMA-RV** | realized vol (1-min) | numpy | ✅ TESTED | **+15.0%** | `16_rv_forecast.csv` |
| **HAR-RV** | realized vol (1-min) | numpy | ✅ TESTED | **+16.3%** | `16_rv_forecast.csv` |

**Tested volatility models: 7.** **Verdict: HAR/EWMA beat naive by ~15–16%** — the real, repeatable
win. (GARCH "lost" only because it was scored on range rather than its native variance target.)

---

## 4. BACKTEST configurations (vol forecast → cloned single-contract engine)

| Config | Levers | Status | P/L (full) | Max DD | Output |
|---|---|:--:|---:|---:|---|
| baseline | none (manual) | ✅ TESTED | −$13,420 | $57,160 | `backtest_matrix.csv` |
| S | adaptive SL/TP | ✅ TESTED | −$10,778 | $68,649 | `backtest_matrix.csv` |
| G | regime gate | ✅ TESTED | +$3,685 | $26,650 | `backtest_matrix.csv` |
| S+G | both | ✅ TESTED | +$21,396 | $27,360 | `backtest_matrix.csv` |
| P / S+P / P+G / S+P+G | sizing combos | 🚫 EXCLUDED | — | — | violate single-contract rule |

Plus: 3-calibration deep-dive on S (✅ tested, 6 runs, `calibration_sweep.csv`) and the per-window
runs (2025 / 2026 / full, ✅ tested, in `dashboard/data.js`).

---

## 5. Tally

| Status | Count | Which |
|---|---:|---|
| ✅ **Tested (produced results)** | **21 model-runs** | 7 price + 7 volatility + 4 backtest configs + (calibration/window variants) |
| ⏸️ **Paused (awaiting GPU)** | 5 | LSTM+reg, NBEATS×2, TFT×2 |
| 🚫 **Blocked (structural)** | 1 | NeuralProphet |
| 🚫 **Excluded (rule)** | 4 | sizing-lever backtest combos |

**Bottom line:** the project's *conclusions* rest entirely on **tested** models. The headline findings
— (a) no model beats naive on price direction, (b) HAR beats naive ~16% on volatility, (c) the vol
overlay halves drawdown in backtest — are all from models that actually ran. The paused deep nets
(NBEATS/TFT) are an *open extension on the price task where the answer is already known to be "no
signal,"* and on the *volatility* task (where they'd be more interesting) they were never queued —
that's the genuine next experiment when a GPU is available.

---

## 6. What to run when the GPU server is available

1. **Fix `darts-rnn-regressors`** (use `future_covariates`) and run it — cheap, completes the LSTM row.
2. **Run NBEATS ×2 and TFT ×2** on the price target — completes the 12-cell price leaderboard for the record (expected: all ~tie naive, but worth confirming).
3. **The actually-interesting one:** run LSTM / NBEATS / TFT on the **volatility (RV) target**, head
   to head with HAR-RV. HAR is the standard to beat; a deep net *might* add a few % — this is the
   only place deep learning has a real chance on this data.
4. Re-run with **memory caps** (`torch.set_num_threads(2)`, one model at a time) per the crash
   post-mortem so it doesn't OOM again.
