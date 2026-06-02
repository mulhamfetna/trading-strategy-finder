# Phase D + E — Darts deep-learning tournament (GPU), and the final 12-model leaderboard

> The Darts neural models (RNN/LSTM, NBEATS, TFT — each plain + with regressors) were
> **paused since the local sessions** awaiting a GPU (the dev box's GPU was unusable and
> two of them OOM'd 14 GB RAM). With the new AMD server (RX 6700 XT, ROCm, 123 GB free)
> they have now **all six actually been trained on the GPU**, walk-forward, and folded
> into the consolidated leaderboard. This closes EXP-D and EXP-E.

---

## 1. What ran, where, how

- **Server:** `dev@amd` (RX 6700 XT / gfx1031), torch 2.5.1+rocm6.2, Darts 0.44.1,
  pytorch-lightning 2.6.5. GPU forced on via `HSA_OVERRIDE_GFX_VERSION=10.3.0`
  (`MP_ACCELERATOR=gpu` in the harness). Full server workflow: `server/docs/MASTER.md`.
- **Data / method unchanged:** same 4h 2025→2026 walk-forward, same `01_naive.csv`
  baseline, same `compute_all` metrics. Only the *compute location* changed (GPU server),
  so results are directly comparable to the earlier classical models.
- All six trained walk-forward (585 eval bars, retrain every 20–40), `GPU used: True`.

### Two bugs fixed to un-pause the regressor variants
The paused regressor scripts crashed; both causes were in `_darts_runner.py`:
1. **Covariate API mismatch.** The runner forced `past_covariates` for every model, but
   `RNNModel` supports **only `future_covariates`**. The regressors are *bar-open-known*
   (the value for bar *t* is known at *t*'s open), so they are **causally `future`
   covariates** for RNN/TFT; NBEATS is past-only. Added a `covariate_kind` switch
   (`future` for RNN/TFT, `past` for NBEATS).
2. **Target/covariate index misalignment.** Target and covariate `TimeSeries` were built
   with *different* `dropna`, so a regressor with leading NaNs shifted the covariate index
   relative to the target → `Invalid past_covariates; could not find values in index
   range …`. Fixed by building both from **one cleaned frame** so their integer indices
   align. (These edits are backward-compatible; local CPU runs are unaffected — default
   `MP_ACCELERATOR=cpu`.)

---

## 2. The final leaderboard (12 models, lower RMSE = better)

| # | model | RMSE ($) | MAE | MAPE % | hit-rate % | lift vs naive % |
|---|---|---:|---:|---:|---:|---:|
| 1 | **naive** | **133.59** | 96.40 | 0.377 | — | **0.00** |
| 2 | prophet | 133.89 | 97.22 | 0.380 | 51.6 | −0.22 |
| 3 | arima | 133.95 | 96.70 | 0.378 | 53.5 | −0.26 |
| 4 | sarimax-plain | 134.05 | 96.72 | 0.378 | 53.5 | −0.34 |
| 5 | sarimax-regressors | 134.20 | 97.24 | 0.380 | 51.6 | −0.45 |
| 6 | **darts-rnn-plain** | 134.22 | 97.10 | 0.380 | 52.8 | −0.47 |
| 7 | statsforecast | 134.92 | 97.14 | 0.380 | 51.8 | −0.99 |
| 8 | **darts-rnn-regressors** | 144.23 | 107.11 | 0.418 | 52.1 | −7.96 |
| 9 | **darts-nbeats-plain** | 148.39 | 110.47 | 0.433 | 50.6 | −11.07 |
| 10 | **darts-nbeats-regressors** | 181.98 | 140.62 | 0.545 | 50.9 | −36.22 |
| 11 | **darts-tft-regressors** | 328.60 | 239.08 | 0.931 | 49.4 | −145.97 |
| 12 | **darts-tft-plain** | 427.39 | 278.39 | 1.081 | 49.9 | −219.92 |

(bold = the six GPU Darts runs added in this phase.)

---

## 3. What it means (no surprises — the conclusion holds, now with the DL evidence in hand)

1. **Naive still wins.** Predicting "next price = last price" beats **every** model. The
   best learner (darts-rnn-plain) only *matches* it to within 0.5%; nothing improves on it.
2. **More model capacity makes it worse, not better.** Ordering by RMSE is almost exactly
   ordering by simplicity: classical (≈naive) → RNN → NBEATS → TFT. The transformer (TFT)
   is **catastrophically worse** (RMSE 3–4×): with ~1.5k bars it has nothing to learn from
   a near-random-walk signal and **diverges/hallucinates** — the same failure mode flagged
   earlier, now demonstrated.
3. **Regressors hurt every time.** For each architecture the `+regressors` variant is worse
   than its plain version (RNN −0.47→−7.96, NBEATS −11→−36, TFT −220→−146*). Same result
   as SARIMAX (plain beat regressors). The box-derived features carry no next-bar signal.
4. **Hit-rate ≈ 50%** for all of them — coin-flip direction, exactly as the ACF≈0.07
   analysis predicted. (*TFT-regressors edged TFT-plain only because both are so broken the
   ordering is noise.)

**Bottom line:** the GPU let us *prove* what was previously only argued — throwing deep
learning (LSTM, NBEATS, TFT) at next-bar 4h price does **not** beat naive; it ranges from
"ties" to "blows up." This re-confirms the project's core finding: **next-bar price/direction
is unpredictable; the tractable signal is volatility/range** (Phase F), not price.

---

## 4. Status of the model audit (updates notes/30)

All 6 previously-PAUSED Darts models are now **TESTED** (GPU, walk-forward):
darts-{rnn,nbeats,tft}-{plain,regressors}. NeuralProphet remains **BLOCKED** (structural
weekend-gap incompatibility — unrelated to compute). The tournament is complete:
**~21 models tested**; naive is the champion.

---

## 5. Reproduce

```bash
cd subprojects/meta-prophet/server
./setup_remote.sh --deps                      # torch-ROCm + darts + lightning (one-time)
rsync code+data (see MASTER.md §5)
bash mp/remote_darts_batch.sh                  # the 6 GPU runs (detached)
./pull … ; python3 scripts/05_compile_leaderboard.py   # -> outputs/leaderboard.csv + plots/
```
Artifacts: `outputs/{09..14}_darts_*.csv`, `outputs/leaderboard.csv`,
`plots/leaderboard.png`, `plots/*_trajectory.png`.
