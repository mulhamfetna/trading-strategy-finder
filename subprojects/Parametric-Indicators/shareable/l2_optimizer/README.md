# L2 Optimizer — self-contained NSGA-III search (with optional cross-instrument contributors)

The **exact** parity-locked L2 optimizer extracted into one runnable package — *not* a re-implementation. It
searches L2 trading profiles (and, optionally, a cross-instrument **ES contributor**) with Optuna NSGA-III,
scored on walk-forward folds with a drawdown-feasibility constraint. The same code also runs the **L1** (main
NQ) optimizer.

> **No secrets, no market data shipped.** This bundle is code + per-TF config + champion seeds only. You supply
> the CSV data (below). Storage defaults to a local SQLite file — no database required.

---

## 1. What's inside

```
box_lookup.py config.py engine.py loader.py presets.py volatility.py   # core NQ box engine
indicators/                                                            # the 18-indicator committee
optimize/
  optimizer.py            # L1 / main NSGA-III driver (+ --contributors)
  core.py folds.py fast_engine.py signals.py data.py timeframes.py     # vectorized scoring stack
  storage.py two_stage.py contributor_search.py contributor_masks.py
  cooldown_caps.json sl_tp_bounds.json                                 # per-TF search bounds (required)
  results/*.json          # champion seeds (lean L1 source of truth + warm-start champions)
  l2/
    optimize.py           # >>> THE L2 OPTIMIZER (entry point) <<<
    engine.py payload.py metrics.py l1_runner.py dataset.py
    contributors/         # cross-instrument substrate (registry, loader, align, state, votes, gate, combine)
subprojects/all-stocks-signals/instruments.py                         # the no-mix instrument registry (ES/QQQ/…)
requirements.txt
```

## 2. What it does (architecture)

- **L1** = the frozen lean 4h champion (box + 1-minute indicators), the source of truth from
  `optimize/results/wsh_lean_4h_champion.json`.
- **L2** trades L1's **dropped** signals while L1 is flat. The L2 optimizer searches L2's SL/TP, vol-gate,
  drawdown breaker, confirmation `k`, and its own indicator committee.
- **Cross-instrument contributor (optional):** a second instrument (ES first; QQQ/SQQQ registered) can vote
  into the gate — its net state (touch/traversal) + an indicator committee, combined by a searchable
  **topology** (`separate_and` / `merged` / `or_boost`). Fully searchable and **unforced** (`es_enabled` is a
  categorical the optimizer can switch off). Absent ⇒ byte-identical to the contributor-free L2.

## 3. Data you must provide

Point `WSH_DATA_BASE` at a directory laid out like this (sizes are large — not shipped):

```
$WSH_DATA_BASE/
  Full_Canldes_Data/<RAW_DIR>/NQ_<tf>.csv   # decision-frame candles per TF (4h, …)
  Full_Canldes_Data/<RAW_DIR>/NQ_1m.csv     # 1-minute frame (exit resolution)
  data/full_data/NQ_full_data.csv           # NQ box levels (one row per market date)
  # --- only if you use --contributors ES ---
  subprojects/all-stocks-signals/instruments.py        # (shipped here; keep it at this path)
  ALL_STOCKS/CANDLES/CME/ES_Continuous_Data/ES_*.csv   # ES candles (1m + decision TF)
  ALL_STOCKS/BOXS/CME/ES/ES_full_data.csv              # ES box levels
  ES_SIGNALS_DELIVERY/2_holds_dropped/ES_*.csv         # ES delivered Stage-1 signal
```

`WSG_DATA_ROOT` (defaults to `$WSH_DATA_BASE/data`) locates the NQ box CSV.

## 4. Run it

```bash
pip install -r requirements.txt
export WSH_DATA_BASE=/path/to/your/data-root
export WSG_DATA_ROOT=$WSH_DATA_BASE/data

# --- L2 optimizer (the entry point) ---
python3 optimize/l2/optimize.py --tf 4h --prefix l2demo --trials 200 --min-trades 5
#   scores L2 on the frozen L1's residuals; champion JSON → optimize/results/l2demo_4h_champion.json

# --- L2 with the cross-instrument ES contributor (searchable, unforced) ---
python3 optimize/l2/optimize.py --tf 4h --prefix l2es --contributors ES --trials 2000
#   (SMC indicators are excluded from the ES committee for speed — see the optimizer note it prints)

# --- L1 / main NQ optimizer (same stack) with ES as an L1 contributor ---
python3 optimize/optimizer.py 4h --contributors ES --ind-1min --no-warm-start --trials 5000 --study-prefix wshesdemo
python3 optimize/optimizer.py 4h --plan          # dry-run: print search size + recommended trials
```

## 5. Storage

- **Default:** a local SQLite study under `optimize/studies/` — fully self-contained, resumable.
- **Shared/parallel:** set `WSH_STORAGE_URL=postgresql://user:pass@host/db` and launch many workers with the
  same `--prefix`; they collaborate on one study (`load_if_exists`). (No DB credentials are shipped here.)

## 6. Objectives & feasibility

NSGA-III, 3 objectives — **median fold P/L ↑**, **worst-fold maxDD ↓**, **median win-rate ↑** — with a
feasibility constraint: full-period maxDD ≤ 25% of full-period P/L. The champion = max median fold P/L among
feasible. The full Pareto front is preserved in the study; no single winner is auto-imposed.

## 7. A note on the ES contributor result

In our own large run, the optimizer — given ES as a *fair, unforced* option — **kept it off**: ES added no
robust signal at L1 (zero ES-on solutions on the Pareto front). The contributor machinery is correct and
general; the negative result is about ES *under the vote-committee model*. Treat `--contributors` as a research
lever, not a recommended default.
