# Meta-Prophet — Forecasting tournament

Read-only research subproject. Compares **naive / Prophet / ARIMA** on a **1-bar-ahead walk-forward** forecast of NQ 4h close (target: log-returns; price reconstructed for eval). NeuralProphet was the 4th planned entry but was dropped due to a dependency-stack incompatibility.

## Final result (TL;DR)

**Naive wins.** Tuned Prophet and ARIMA both lose to "previous close" by ~0.2% RMSE — within noise but consistently signed negative. Full write-up: `notes/08_final_report.md`.

| Rank | Model | RMSE ($) | MAPE (%) | Hit-rate (%) | Lift vs naive (%) |
|---:|---|---:|---:|---:|---:|
| 1 | **naive** | **133.59** | 0.377 | — | 0.00 |
| 2 | prophet (tuned) | 133.89 | 0.380 | 51.62 | −0.22 |
| 3 | arima (auto) | 133.95 | 0.378 | 53.50 | −0.26 |

## Why this matters

The original `legacy/prophet_test.py` reported **RMSE = $5,625** — that was a row-index misalignment bug, not an actual forecast error. The honest naive RMSE on a properly walk-forward-aligned eval is **$133.59 (42× smaller)**. Beating *that* is structurally hard for any point-forecast model on 4h equity-index-futures log-returns.

## Subproject layout

```
subprojects/meta-prophet/
├── README.md                      # this file
├── NQ_4h.csv                      # reference (full series, 2025-01-01 → 2026-05-19)
├── NQ_4h_2025.csv                 # train pool (1534 bars)
├── NQ_4h_2026.csv                 # eval pool  (585 bars, held-out)
├── requirements.txt
├── .venv/                         # subproject-local Python 3.14 venv
├── notes/
│   ├── 00_research_report.md      # Prophet literature review + citations
│   ├── 01_data_jump_investigation.md
│   ├── 02_mape_and_relative_error_explained.md
│   ├── 03_design.md               # locked design (5 phases)
│   ├── 04_implementation_plan.md  # TDD plan
│   ├── 04_phase1_baseline.md      # naive baseline result
│   ├── 05_phase2_prophet_tuned.md # Prophet result
│   ├── 06_phase3_arima.md         # ARIMA result
│   ├── 07_phase4_neuralprophet_BLOCKED.md
│   └── 08_final_report.md         # ← read this for the verdict
├── scripts/
│   ├── common/                    # shared eval harness (data/features/metrics/walkforward)
│   ├── 01_baseline_naive.py
│   ├── 02_prophet_tuned.py
│   ├── 03_arima.py
│   ├── 04_neuralprophet.py        # exists but blocked — see BLOCKED note
│   ├── 05_compile_leaderboard.py
│   └── legacy/                    # original prophet_train.py + prophet_test.py preserved
├── tests/                         # 19 tests, all green incl. no-lookahead invariant
├── outputs/                       # per-model CSVs + leaderboard.csv
└── plots/                         # 5 PNGs (4 trajectories + 1 leaderboard + 1 error-dist)
```

## Phase status

| # | Phase | Status |
|---|---|---|
| 0 | Scaffold | ✅ |
| 1 | Naive baseline + harness | ✅ RMSE $133.59 |
| 2 | Prophet tuned | ✅ RMSE $133.89, lift −0.22% |
| 3 | ARIMA (pmdarima) | ✅ RMSE $133.95, lift −0.26%, hit-rate 53.5% |
| 4 | NeuralProphet | 🔒 **PERMANENTLY DROPPED** — see `notes/09_neuralprophet_root_cause_report.md`. Structural incompatibility (uniform-cadence assumption vs. CME weekend gaps; maintainer-confirmed in NP Discussion #1521; library marked Inactive on Snyk). |
| 5 | Initial leaderboard + interim report | ✅ |
| **B** | **SARIMAX × 2 (plain + regressors)** | ✅ both lose to naive (−0.34%, −0.45%) |
| **C** | **Nixtla StatsForecast AutoARIMA** | ✅ loses to naive (−0.99%) |
| **D** | **Darts × 6 (RNN/NBEATS/TFT × plain/regressors)** | ⏸️ PAUSED — 1/6 done (rnn-plain −0.47%); awaiting GPU server |
| **E** | **Final price leaderboard + verdict** | ⏸️ blocked on D |
| **F1** | **Range/volatility forecasting (4h)** | ✅ **HAR +16.3%, EWMA +15.3% — FIRST models to BEAT naive** |
| **F2** | **Realized volatility from 1-min data** | ✅ **HAR-RV +16.3%, cleaner target (RMSE 61 vs 102 pts)** |
| **G** | **Backtest vol model via CLONED engine (original untouched)** | ✅ levers cut drawdown ~50% (gate halves it); P/L gains are overfit (calibration sweep non-monotonic) — use as risk overlay, not profit optimizer |
| **G5** | **Clone dashboard (standalone HTML)** | ✅ `dashboard/index.html` — trades view + vol/SL-TP/gate/equity panels, config dropdown; open in browser |

> **The pivot that worked:** after 11 price-forecasting models all lost to naive (direction is
> unpredictable, ACF 0.07), Phase F switched the target to **range/volatility** (ACF 0.56) and
> immediately beat naive by **+16%**. See `notes/23_is_return_useful_synthesis.md` (why) and
> `notes/25_phase_F1_results.md` (the result). Volatility forecasts feed the live engine's
> stop-loss / position-sizing directly.

> **Expansion plan:** `notes/10_expansion_plan.md` lays out the 4-phase add-on (B → C → D → E) that replaces the single NeuralProphet entry with 9 new entries via libraries that natively support irregular timestamps. Final leaderboard: 12 models.

## Reproduce

```bash
cd subprojects/meta-prophet
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/01_baseline_naive.py        # ~30 s
.venv/bin/python scripts/03_arima.py                 # ~5-10 min
.venv/bin/python scripts/02_prophet_tuned.py         # ~10-20 min
.venv/bin/python scripts/05_compile_leaderboard.py   # ~10 s

.venv/bin/pytest tests/ -v                           # 19 passing, ~1 s
```

## Constraints honored

- No edits to `src/`, `frontend/`, `docs/`, `tests/`, or any other subproject.
- Imports `src.strategy.simple_strategy` not required for this study; meta-prophet stays standalone.
- No look-ahead in any feature: verified by `tests/test_features.py::test_no_lookahead_*` and `tests/test_walkforward.py::test_walk_forward_first_prediction_uses_train_only`.
