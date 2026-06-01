# Meta-Prophet — Design Doc (locked, then expanded)

> Date: 2026-05-31. Approved through brainstorming. Subproject: `subprojects/meta-prophet/`.
> Companion docs: `00_research_report.md` (Prophet literature), `01_data_jump_investigation.md` (data sanity), `02_mape_and_relative_error_explained.md` (metric semantics).
>
> **Status update (2026-06-01):** This original 4-model design was modified post-implementation:
> 1. **NeuralProphet (Phase 4) permanently dropped** — see `07_phase4_neuralprophet_BLOCKED.md` + `09_neuralprophet_root_cause_report.md`. Structural incompatibility (uniform-cadence assumption vs. CME weekend gaps).
> 2. **4-phase expansion added** (`10_expansion_plan.md`): SARIMAX × 2 + StatsForecast × 1 + Darts × 6 = 9 new entries replace the single NeuralProphet entry. Final leaderboard is 12 models.
>
> The expansion answers the same underlying research questions the original design did, with libraries that natively support irregular timestamps.

---

## 1. Problem statement

Build a **four-model tournament** that forecasts the next 4h NQ close on the 2026 held-out window, evaluates them on a common harness, and produces a leaderboard ranked by RMSE/MAE/MAPE/lift-vs-naive. Tournament decides whether Prophet (with all known levers applied) can beat a naive previous-close baseline on this data, and if not, which alternative does.

**Use case (locked):** price-level forecast, 1-bar-ahead, walk-forward retrained.
**Headline metric (locked):** lift over naive (`(RMSE_naive − RMSE_model) / RMSE_naive`). Positive ⇒ model adds value. Plus RMSE / MAE / MAPE / directional hit-rate as supporting metrics.

---

## 2. Data

| File | Role | Rows | Span |
|---|---|---:|---|
| `NQ_4h.csv` | Reference (full series) | 2,119 | 2025-01-01 18:00 → 2026-05-19 18:00 |
| `NQ_4h_2025.csv` | Train pool | 1,534 | 2025-01-01 18:00 → 2025-12-31 14:00 |
| `NQ_4h_2026.csv` | Eval pool (held-out) | 585 | 2026-01-01 18:00 → 2026-05-19 18:00 |

- The split is clean (rows sum exactly; no overlap; 28-hour year-boundary gap is the CME Globex new-year closure).
- The +20% YoY rally is real market behaviour, with named catalysts dated and matched against the data (see `01_data_jump_investigation.md`).
- 2025 contains a V-shape (−21% drawdown → +52% recovery) including the **+8.21% 4h bar on 2025-04-09** (Trump tariff-pause announcement). This bar is a ~14σ Gaussian event and will dominate RMSE for any reasonable model.

**Target (all four models):** `y = log(close_t / close_{t-1})` — log-return, stationary, no drift. Price is reconstructed for eval: `close_hat_t = close_{t-1} · exp(y_hat_t)`.

**Eval window:** all 585 bars of 2026, with retraining as bars unfold (see §4).

---

## 3. Subproject layout

```
subprojects/meta-prophet/
├── README.md                          # subproject overview + phase table
├── NQ_4h.csv                          # reference (untouched)
├── NQ_4h_2025.csv                     # train pool
├── NQ_4h_2026.csv                     # eval pool
├── notes/
│   ├── 00_research_report.md          # Prophet literature with citations
│   ├── 01_data_jump_investigation.md  # data sanity + macro catalysts
│   ├── 02_mape_and_relative_error_explained.md
│   ├── 03_design.md                   # this doc
│   ├── 04_phase1_baseline.md          # naive baseline numbers (to be written)
│   ├── 05_phase2_prophet_tuned.md     # Prophet tournament entry
│   ├── 06_phase3_arima.md             # ARIMA entry
│   ├── 07_phase4_neuralprophet.md     # NeuralProphet entry
│   └── 08_final_report.md             # head-to-head leaderboard + verdict
├── scripts/
│   ├── common/                        # shared eval harness — one copy, all models use it
│   │   ├── __init__.py
│   │   ├── data.py                    # load + train/eval split + log-return transform
│   │   ├── walkforward.py             # rolling-origin retrain loop
│   │   ├── metrics.py                 # RMSE / MAE / MAPE / hit-rate / lift-vs-naive
│   │   └── features.py                # bar-open-known regressors
│   ├── 01_baseline_naive.py
│   ├── 02_prophet_tuned.py
│   ├── 03_arima.py
│   ├── 04_neuralprophet.py
│   ├── 05_compile_leaderboard.py      # consolidates per-model outputs → leaderboard.csv
│   └── legacy/                        # original prophet_train.py / prophet_test.py preserved
│       ├── prophet_train.py
│       ├── prophet_test.py
│       ├── forecast.csv
│       └── evaluation_results.csv
├── tests/
│   ├── __init__.py
│   ├── test_data_load.py              # CSV schema + split integrity
│   ├── test_metrics.py                # RMSE/MAE/MAPE/lift formula correctness
│   ├── test_features.py               # regressor causality (no look-ahead)
│   └── test_walkforward.py            # harness contract: history grows monotonically, no peek
├── requirements.txt                   # prophet, pmdarima, neuralprophet, pandas, numpy, matplotlib
├── outputs/
│   ├── 01_naive.csv                   # per-bar predictions
│   ├── 02_prophet.csv
│   ├── 03_arima.csv
│   ├── 04_neuralprophet.csv
│   └── leaderboard.csv                # one row per model with headline numbers
└── plots/
    ├── <model>_trajectory.png         # actual vs forecast price, one per model
    ├── leaderboard.png                # bar chart RMSE / MAPE / lift
    └── error_distribution.png         # abs-error histograms per model
```

All files stay under `subprojects/meta-prophet/`. **No edits to `src/`, `frontend/`, `docs/`, `tests/`, or any other subproject.** Imports `prophet`, `pmdarima`, `neuralprophet`, `pandas`, `numpy`, `matplotlib` only.

---

## 4. Walk-forward eval framework

**Identical for all four models.** Implemented in `scripts/common/walkforward.py`.

```
INPUTS:
    train_pool  = 2025 bars (1,534 rows)
    eval_pool   = 2026 bars (585 rows)
    retrain_every = 20            # bars (~3 days)
    model_factory = callable returning a fresh model

PROTOCOL:
    history = train_pool.copy()
    predictions = []
    for chunk_start in range(0, len(eval_pool), retrain_every):
        # fit on everything observed up to this point
        model = model_factory()
        model.fit(history)
        # produce up to retrain_every 1-bar-ahead forecasts
        for i in range(chunk_start, min(chunk_start + retrain_every, len(eval_pool))):
            target_bar  = eval_pool.iloc[i]
            features_at = build_features_at_bar_open(history, target_bar)
            yhat_ret    = model.predict_one(features_at)
            yhat_price  = history.iloc[-1].close * exp(yhat_ret)
            predictions.append((target_bar.datetime, target_bar.close, yhat_price))
            # advance history with the realised bar (only after we've recorded the forecast)
            history = pd.concat([history, target_bar.to_frame().T])
    return predictions
```

**Causality guarantee:** `build_features_at_bar_open` only uses bars with `close_time ≤ bar_open_time`. Verified by regression test (`tests/test_features.py` + `tests/test_walkforward.py`). The features that need this guarantee:

- `prior_log_return = log(close[t-1] / close[t-2])`
- `prior_range = (high[t-1] − low[t-1]) / close[t-1]`
- `rolling_20bar_vol = std(log_returns[t-20:t-1])`
- `time_of_day` one-hot (RTH-open / lunch / RTH-close / Asia / EU — based on the bar's datetime, so trivially known)
- `day_of_week` one-hot
- *(optional, if data available)* `vix_prior_close` — out of scope unless added later

**Retrain cadence:** default `retrain_every=20` (~3 calendar days at 4h cadence). Sensitivity tested at 1 (per-bar) and 100 (~3 weeks) on the naive + Prophet entries — fast enough to be feasible.

---

## 5. Hyperparameter protocol — two-tier

To keep runtime tractable, hyperparam search is one-shot on 2025 only; the winning config is then locked and used unchanged in the 2026 walk-forward.

**Tier 1 — search on 2025:** Prophet-style `cross_validation` (rolling-origin CV) on the train pool: `initial='180 days'`, `period='14 days'`, `horizon='4 hours'`. Each candidate is scored by RMSE on reconstructed price. Best config locked.

**Tier 2 — eval on 2026:** walk-forward with locked config; retrain every 20 bars. No further tuning.

**Grids (intentionally small — research found only `changepoint_prior_scale` strongly affects RMSE):**

| Model | Grid | Configs |
|---|---|---:|
| Naive    | (none — no hyperparameters)                                                                                      |   1 |
| Prophet  | `changepoint_prior_scale ∈ {0.001, 0.01, 0.05, 0.1, 0.5}` × `seasonality_prior_scale ∈ {0.01, 0.1, 1, 10}` × `seasonality_mode ∈ {add, mult}` | 40 |
| ARIMA    | `auto_arima(p∈[0,5], q∈[0,5], d=0)` AIC search                                                                  | ~30 |
| NeuralProphet | `n_lags ∈ {10, 15, 20}` × `learning_rate ∈ {1e-3, 1e-2}` × `ar_layers ∈ {[], [16]}`                          | 12 |

Prophet-locked settings (not in grid): `growth='flat'`, daily Fourier `period=6, fourier_order=4`, weekly Fourier `period=30, fourier_order=3`, all regressors from §4, session-hour restriction in `make_future_dataframe`. NeuralProphet inherits the same regressors.

---

## 6. Metrics & reporting

Computed by `scripts/common/metrics.py` on the reconstructed-price prediction series:

| Metric | Formula | Units | Role |
|---|---|---|---|
| **RMSE** | `sqrt(mean((y − y_hat)²))` | $ | Dollar-scale, outlier-sensitive |
| **MAE**  | `mean(|y − y_hat|)` | $ | Dollar-scale, outlier-robust |
| **MAPE** | `mean(|y − y_hat| / |y|) × 100` | % | Relative, scale-invariant |
| **Hit-rate** | `mean(sign(y_hat_return) == sign(y_return))` | % | Directional skill diagnostic |
| **Lift vs naive** | `(RMSE_naive − RMSE_model) / RMSE_naive × 100` | % | **Headline** — does this model add value? |

All five reported per model in `outputs/leaderboard.csv`.

---

## 7. Per-model phase plan

Each phase is small enough to be a single PR-equivalent commit, with its own write-up.

| Phase | What | Deliverable | Locks |
|---|---|---|---|
| 0 | Scaffold subproject (done in this session) | dir tree above | — |
| 1 | Naive baseline + harness skeleton | `01_baseline_naive.py`, `common/data.py`, `common/walkforward.py`, `common/metrics.py`, no-lookahead test, `outputs/01_naive.csv`, `notes/04_phase1_baseline.md` | RMSE_naive, harness API |
| 2 | Prophet tuned | `02_prophet_tuned.py`, `common/features.py`, `notes/05_phase2_prophet_tuned.md` | Prophet config + result |
| 3 | ARIMA | `03_arima.py`, `notes/06_phase3_arima.md` | ARIMA config + result |
| 4 | NeuralProphet | `04_neuralprophet.py`, `notes/07_phase4_neuralprophet.md` | NeuralProphet config + result |
| 5 | Leaderboard + final report | `05_compile_leaderboard.py`, `outputs/leaderboard.csv`, all plots, `notes/08_final_report.md` | Verdict |

Each phase note must include: hyperparam-search log, locked config, runtime, headline metrics, three trajectory plots (early / mid / late 2026), and an honest caveats section.

---

## 8. Risks & known dead-ends

**Risks:**
- **Runtime.** NeuralProphet at retrain-every-20 over 585 bars ≈ 29 retrains. If each takes >2 min the phase blows out to 1+ hour. Mitigation: cap epochs at ~50, batch-size to dataset-fit, fall back to retrain_every=40 if too slow.
- **`auto_arima` may pick d>0** even though we feed log-returns. Mitigation: force `d=0` explicitly.
- **Prophet's daily-seasonality on a 4h grid.** Mitigation: explicit Fourier seasonalities + `daily_seasonality=False`, per research recommendation.
- **+8.21% Apr-9 bar in train.** This is a real data point, not an outlier to clip. It will hurt absolute RMSE but no model should "fix" it — that's the structural fat-tail problem of forecasting equity-index futures. Documented and accepted.

**Dead-ends not pursued** (per research report):
- MCMC sampling (only changes uncertainty intervals, not point forecasts; 100× slower).
- Logistic growth with a price cap.
- Manual changepoints.
- US-equity holiday calendar (futures trade nearly 24/5 — holidays produce gaps, not features).
- Forecasting raw close. **All models in the tournament forecast log-returns and reconstruct price.**

---

## 9. Success criteria

The study is "successful" — regardless of which model wins — if the final report (`notes/08_final_report.md`) answers all of the following definitively, with numbers:

1. What is the honest naive-baseline RMSE/MAPE on the 2026 walk-forward?
2. Can a fully-tuned Prophet (with log-return target, regressors, session restriction, CV-tuned changepoint) beat the naive baseline? By how much?
3. Does ARIMA beat Prophet? Does NeuralProphet beat both?
4. What does the leaderboard look like at retrain cadences 1 / 20 / 100? Where does retrain-frequency stop paying off?
5. Given the answer to (3) — which model (if any) should be deployed, and if none beats naive, what's the recommended next step?

Quantitatively: the leaderboard CSV exists, has one row per model, every metric is populated, no NaNs, no off-by-one in the date alignment.

---

## 10. Out of scope

- Multi-step (>1 bar) forecasts. Doable later by changing `n_forecasts` in NeuralProphet and looping in the others, but not in this study.
- Forecasting volatility, range, direction-only, or any non-price target. The current target is log-return ⇒ price; switching the target is a sibling study.
- Live deployment / integration with the simple-backtest engine. This study produces an offline leaderboard only.
- Adding new exogenous data (VIX, options skew, news sentiment). The four regressors from §4 are the locked set.

---

## 11. Next step

Hand off to **writing-plans** to break this design into a sequenced implementation plan with TDD checkpoints. The plan should follow the 5-phase split in §7 — each phase its own commit / review checkpoint.
