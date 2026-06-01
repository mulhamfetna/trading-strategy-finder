# Expansion Plan — 4-Phase Add-On to the Tournament

> Triggered after the NeuralProphet root-cause investigation (`09_neuralprophet_root_cause_report.md`) recommended 4 alternative paths. This plan executes **all four** sequentially: 4 → 1 → 2 → 3.

## Locked decisions (from user, 2026-06-01)

- **Darts: run all three architectures** (LSTM, NBEATS, TFT) — full evidence on which AR family works best.
- **SARIMAX and Darts: run *both* with and without regressors** — tests whether Phase-2's 14 bar-open-known regressors add value beyond pure AR.
- **Leaderboard regenerated after every new entry** — incremental visibility.
- All new entries use the **same walk-forward harness** (`scripts/common/walkforward.py`), **same `retrain_every=20`**, **same log-return target**, **same train/eval split** as Phases 1-3.

## Final leaderboard projection (12 entries)

| # | Phase | Model | Regressors? | Library |
|---:|---|---|---|---|
| 1 | 1 | naive (previous-close) | — | — |
| 2 | 2 | prophet (tuned) | ✅ 14 | prophet 1.3 |
| 3 | 3 | arima (auto) | ❌ | pmdarima 2.1 |
| 4 | **B** | sarimax-plain | ❌ | statsmodels 0.14 |
| 5 | **B** | sarimax-regressors | ✅ 14 | statsmodels 0.14 |
| 6 | **C** | statsforecast-autoarima | ❌ | nixtla statsforecast |
| 7 | **D** | darts-rnn-plain | ❌ | darts (LSTM) |
| 8 | **D** | darts-rnn-regressors | ✅ 14 | darts (LSTM) |
| 9 | **D** | darts-nbeats-plain | ❌ | darts (NBEATS) |
| 10 | **D** | darts-nbeats-regressors | ✅ 14 | darts (NBEATS) |
| 11 | **D** | darts-tft-plain | ❌ | darts (TFT) |
| 12 | **D** | darts-tft-regressors | ✅ 14 | darts (TFT) |

The 12-entry leaderboard answers three questions definitively:
- **Q1 — does any model beat naive?** Already answered "no" by Phases 1-3; expansion tests whether SARIMAX/Darts changes the verdict.
- **Q2 — do exogenous regressors help?** Direct comparison via plain-vs-regressors pairs for SARIMAX, Darts RNN, Darts NBEATS, Darts TFT.
- **Q3 — which AR family closes the Prophet gap?** Direct comparison ARIMA vs SARIMAX vs StatsForecast vs Darts-RNN vs Darts-NBEATS vs Darts-TFT.

---

## Phase A — Option 4: Formalize NeuralProphet drop (docs only, no compute)

**Goal:** Move from "we tried NeuralProphet and it failed" to "NeuralProphet is permanently excluded from this study with citation-backed reasoning". Consolidate the existing notes into a clean documentation state.

**Tasks A.1-A.5:**

1. Restore `scripts/04_neuralprophet.py` to its pre-revival state OR leave it as the "dead" reference script (we'll annotate it as such in a docstring rather than restore). Decision: **annotate, don't restore** — the script is now the canonical record of what we tried.
2. Update `notes/07_phase4_neuralprophet_BLOCKED.md` to point readers to `notes/09_neuralprophet_root_cause_report.md` for the deep investigation.
3. Update `README.md` Phase Status table to reflect "NeuralProphet PERMANENTLY DROPPED — see `09_neuralprophet_root_cause_report.md`".
4. Update `notes/03_design.md` §7 (Phase plan) to note that the design was modified post-implementation to drop NeuralProphet.
5. Update `notes/08_final_report.md` to fold in the new direction (4 new entries coming).

**Effort:** ~10 min, no compute, no risk.

**Deliverables:** edits to 5 existing files; no new files except this plan and the root-cause report (already written).

---

## Phase B — Option 1: SARIMAX (2 entries)

**Goal:** Test whether the standard non-NeuralProphet way to do AR + exogenous regressors closes any gap to naive.

**Tasks B.1-B.4:**

1. **B.1** — Add `06_sarimax_plain.py` script. Uses `statsmodels.tsa.statespace.SARIMAX` on log-returns, no exogenous, fixed `order=(p, 0, q)` with `auto_arima`-selected `(p, q)` from Phase-3 OR a small explicit grid. Walk-forward retrain_every=20. Writes `outputs/06_sarimax_plain.csv`.
2. **B.2** — Add `07_sarimax_regressors.py`. Same SARIMAX but with `exog=` set to the 14 Phase-2 regressors (filtered by `usable_regressors`). Writes `outputs/07_sarimax_regressors.csv`.
3. **B.3** — Run both, regenerate `outputs/leaderboard.csv` and `plots/leaderboard.png` via `scripts/05_compile_leaderboard.py` (just update the MODELS list).
4. **B.4** — Write `notes/11_phase_B_sarimax.md` documenting both runs with numbers + interpretation.

**Compute:** statsmodels SARIMAX is faster than pmdarima but does ~29 retrains × ~10s/fit ≈ 5 min per entry × 2 = ~10 min.

**Risk:** SARIMAX with `exog=` requires future regressor values at predict time — the harness already passes `target_row` with regressors, so this should be a clean wire-up.

---

## Phase C — Option 2: Nixtla StatsForecast (1 entry)

**Goal:** Sanity-check pmdarima's AIC-selected ARIMA result against a different, modern ARIMA library on the same data. If the two ARIMA libraries diverge meaningfully, pmdarima may be mis-fitting; if they converge, our ARIMA verdict is robust.

**Tasks C.1-C.3:**

1. **C.1** — Add `08_statsforecast_autoarima.py`. Uses `statsforecast.models.AutoARIMA` on log-returns; per Nixtla docs, the `freq=` parameter accepts irregular cadence when fitting on integer-indexed series. Walk-forward retrain_every=20. Writes `outputs/08_statsforecast_autoarima.csv`.
2. **C.2** — Add `statsforecast>=2.0` to `requirements.txt`. Install.
3. **C.3** — Run, regenerate leaderboard, write `notes/12_phase_C_statsforecast.md`.

**Compute:** Nixtla advertises 10-100× speedup over pmdarima → likely under 5 min total.

**Risk:** install compat on Python 3.14 (`statsforecast` requires `nixtla-numba` which may not have a 3.14 wheel). If it fails to install, document and skip C.

---

## Phase D — Option 3: Darts (6 entries = 3 architectures × 2 regressor modes)

**Goal:** Test the AR-Net replacement question — does any modern deep-AR architecture beat ARIMA on this data?

**Tasks D.1-D.10:**

1. **D.1** — Install: add `darts>=0.30` to `requirements.txt`, install. Verify on Python 3.14 + torch 2.12 + numpy 1.26.
2. **D.2** — Create shared Darts helper module `scripts/common/darts_helpers.py` with: `to_darts_ts(df)` (converts our long-format frame to `TimeSeries` with `fill_missing_dates=False`), `darts_forecaster_factory(model_class, model_kwargs, use_regressors)`. Reduces per-script boilerplate.
3. **D.3** — `09_darts_rnn_plain.py` (LSTM, no covariates).
4. **D.4** — `10_darts_rnn_regressors.py` (LSTM + `future_covariates`).
5. **D.5** — `11_darts_nbeats_plain.py`.
6. **D.6** — `12_darts_nbeats_regressors.py`.
7. **D.7** — `13_darts_tft_plain.py`.
8. **D.8** — `14_darts_tft_regressors.py`.
9. **D.9** — Run all 6 sequentially. After each: append output CSV, regenerate leaderboard + plots, append a row to `notes/13_phase_D_darts.md`.
10. **D.10** — Write the consolidated Phase D summary in `notes/13_phase_D_darts.md`.

**Compute:** Darts on CPU/GPU + 6 entries × ~5-30 min each = ~1-3 hours. TFT is the slowest.

**Risk:** Darts depends on pytorch-lightning; we already have a compatible torch from the NeuralProphet install. Custom-covariate plumbing is the most error-prone part — D.2 helper minimises this.

---

## Phase E — Final consolidation (docs)

**Goal:** Produce the definitive 12-entry leaderboard + final report verdict.

**Tasks E.1-E.4:**

1. **E.1** — Update `scripts/05_compile_leaderboard.py` MODELS list to include all 12 entries; add a "regressors used" column to `leaderboard.csv`; regenerate all plots with appropriate scaling for 12 bars.
2. **E.2** — Rewrite `notes/08_final_report.md` to incorporate all phases. Re-rank verdict; address all 3 research questions (Q1/Q2/Q3 above) with numbers.
3. **E.3** — Update `README.md` with the final 12-entry status table.
4. **E.4** — Run the full test suite + reproducibility sanity check.

---

## Cross-cutting docs updates (after EACH phase A, B, C, D)

After every phase, the following files MUST be updated to reflect new state:

- `README.md` — status table.
- `notes/08_final_report.md` — leaderboard table at the top.
- `outputs/leaderboard.csv` — auto-regenerated by `05_compile_leaderboard.py`.
- `plots/leaderboard.png`, `plots/error_distribution.png` — auto-regenerated.
- New `notes/11_phase_B_*.md`, `12_phase_C_*.md`, `13_phase_D_*.md` per phase.

---

## Risks and mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| `darts` install fails on Python 3.14 | medium | Document failure, run on smaller set (only RNN), or use an isolated 3.11 venv. |
| `statsforecast` install fails on Python 3.14 | medium | Same — Phase C is the most expendable. Skip if blocked. |
| Walk-forward retraining on Darts TFT is too slow | high | Drop retrain cadence to every 40 or 60 bars for TFT specifically. Document the asymmetry. |
| SARIMAX with `exog` blows up on NaN regressors at eval boundary | low | Already-fixed by the `split_by_cutoff` pattern used in Prophet driver — re-apply here. |
| Leaderboard becomes cluttered at 12 entries | low | Group plot by family (naive/Prophet/ARIMA-family/Darts-family); use color coding. |

---

## Execution sequence (this is what runs)

Phase A (docs only, ~10 min) → Phase B.1 (SARIMAX plain, ~5 min) → B.2 (SARIMAX + regressors, ~5 min) → leaderboard update → B.4 (Phase B notes) → C.1-C.3 (StatsForecast, ~10 min) → leaderboard update → D.1-D.8 (Darts × 6, ~1-3 hours) → leaderboard updates between each → D.10 (Phase D notes) → E.1-E.4 (final consolidation).

Total estimated wall-clock: **2-4 hours**.

I'll start with Phase A now (just docs, fast) and ask any clarifying questions inline if Phase B/C/D throws something unexpected at me.
