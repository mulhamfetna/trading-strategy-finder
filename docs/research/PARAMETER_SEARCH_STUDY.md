# Parameter Search Study — Optimising Profit Factor

**Status:** Research / pre-implementation. Read this, pick an approach, then we build.
**Scope today:** 3 parameters — `sl_soft_points`, `sl_hard_points`, `tp_target_points`.
**Future scope:** up to 10–30 parameters from `BoxStrategyParams`.
**Objective:** maximise `metrics.profit_factor` (with caveats — see §8).

---

## 1. The problem framed correctly

Each evaluation = **one full backtest run** of `BoxStrategy` over the 4h CSV. That's a one-shot oracle: feed it `(sl_soft, sl_hard, tp)`, get back a `profit_factor`. The oracle has these properties that determine which algorithms are viable:

| Property | Value | Implication |
|---|---|---|
| Evaluation cost | seconds → ~1 min on a multi-year CSV | Sample-efficient methods preferred |
| Stochasticity | **Deterministic** — same params → same PF | Noise-handling methods give us nothing |
| Gradient available? | No | Gradient-based methods are out |
| Constraints | `sl_hard ≥ sl_soft`, both > 0, `tp_target > 0` | Need constraint handling |
| Output anomalies | PF can be `None` (no losses) or `0.0` (no wins) | Need a fallback objective for those cases |
| Search-space shape | Multi-modal, discontinuous (cliffs where trades flip SL↔TP), plateaus | Local methods get stuck |
| Continuous or discrete? | Continuous in principle, **discretised at the NQ tick = 0.25 pt** | Grid is feasible at coarse resolution |

The **single most important property**: PF is hostile to local methods. Small changes in `tp_target` can move a trade from a loss to a win and flip the PF by a lot. There are flat plateaus where many trades miss every level; there are cliffs where one extra trade clears the SL line. Gradient-free, multi-modal-aware methods are the only choice.

---

## 2. Algorithm survey

Grouped from simplest to most sophisticated. Each row is a candidate.

### 2.1 Brute force / sampling

| # | Algorithm | One-line description | Strengths | Weaknesses |
|---|---|---|---|---|
| A1 | **Grid Search** | Discretise each param, try every combination. | Complete coverage; trivially parallel; deterministic; gives full landscape (heatmaps) | Combinatorial explosion: 3^10 = 59k, 10^10 = 10 billion. Misses optima between grid points. |
| A2 | **Random Search** | Sample uniformly at random. | Scales well; embarrassingly parallel; usually beats grid for >5 params. | Wastes samples on bad regions; never adapts. |
| A3 | **Latin Hypercube / Sobol** | Stratified or low-discrepancy quasi-random sampling. | Better coverage than random with fewer samples; great seed for surrogate models. | Still not adaptive. |

### 2.2 Population / evolutionary

| # | Algorithm | One-line description | Strengths | Weaknesses |
|---|---|---|---|---|
| B1 | **Simulated Annealing** | Local search with probabilistic uphill moves controlled by temperature. | Simple, low memory, escapes local optima eventually. | Slow convergence; temperature schedule is its own tuning problem. |
| B2 | **Genetic Algorithm** | Population of param vectors, mutation + crossover. | Handles constraints + mixed types; multi-modal-friendly; parallel. | Many meta-hyperparameters; slow for cheap-ish evals. |
| B3 | **Particle Swarm (PSO)** | Particles with velocity that get pulled toward personal + global bests. | Smooth on continuous landscapes; intuitive. | Often plateaus near local optima; tuning of inertia/social weights. |
| B4 | **Differential Evolution (DE)** | Mutation via difference of two random members; scipy built-in. | Robust on rough landscapes; few hyperparameters. | Population overhead; slower than BO on smooth surfaces. |
| B5 | **CMA-ES** | Evolution strategy that learns the covariance of the search distribution. | **Best-in-class for continuous black-box up to ~50 dims**; handles ill-conditioning. | O(n²) memory; complex (use the `cma` package). |

### 2.3 Surrogate / Bayesian

| # | Algorithm | One-line description | Strengths | Weaknesses |
|---|---|---|---|---|
| C1 | **Bayesian Optimisation w/ Gaussian Process (BO-GP)** | Fit a GP to observed (params, PF) pairs; pick next point that maximises Expected Improvement. | **Gold standard for expensive evaluations**; uncertainty-aware. | GP cost is O(n³); chokes above ~20 dims; needs careful prior. |
| C2 | **Tree-structured Parzen Estimator (TPE)** | Bayesian alternative using density estimators over "good" vs "bad" samples. | Scales to 100+ dims; handles mixed continuous/categorical; the Optuna default. | Less theoretically elegant than GP; harder uncertainty quantification. |
| C3 | **Random Forest / Gradient-Boosted surrogate (SMAC)** | Surrogate is an RF/GBT instead of a GP. | Handles non-stationary, discrete, conditional params; scales to 50+ dims. | Less smooth uncertainty estimates; trickier to tune EI. |

### 2.4 Direct search

| # | Algorithm | One-line description | Strengths | Weaknesses |
|---|---|---|---|---|
| D1 | **Nelder–Mead simplex** | Gradient-free direct search via reflection / expansion / contraction. | Zero hyperparameters; great for **local refinement** of an already-good point. | Useless for global; can't handle constraints natively. |
| D2 | **Pattern Search / NOMAD** | Mesh-adaptive direct search with constraint handling. | Deterministic; constraint-aware. | More setup than alternatives; rarely worth it for HPO. |

### 2.5 Multi-objective (worth flagging for later)

| # | Algorithm | One-line description | Strengths | Weaknesses |
|---|---|---|---|---|
| E1 | **NSGA-II / NSGA-III** | Evolutionary multi-objective; produces Pareto front. | Gives the **PF / Sharpe / Max-DD trade-off curve**, not a single point. | Heavier; needs multi-objective objective definition. |

### 2.6 What we're NOT considering

| Algorithm | Why skipped |
|---|---|
| Gradient descent / Adam / L-BFGS | No gradient available; objective is non-differentiable. |
| Reinforcement learning / NAS | Needs orders of magnitude more samples than we have budget for. |
| Deep learning surrogate (e.g., neural surrogate model) | Same — insufficient data, ROI is poor for this scale. |

---

## 3. Mapping algorithms to our problem

The decisive constraints:
- **Today: 3 params** with a known reasonable range each.
- **Tomorrow: 10–30 params**, some of which will be discrete (ints / booleans / categorical like `big_candle_resolution`).
- **Each evaluation is seconds-to-minutes**, parallelisable.
- **Objective is multi-modal with cliffs.**

### 3.1 For 3 params (today)

| Method | Verdict |
|---|---|
| **Grid Search** (A1) | ✅ Works. 50 × 50 × 50 = 125 000 evals — tractable in a few hours, parallelisable, gives a 3-D heatmap you can visualise. |
| **Random Search** (A2) | ✅ Works. 5 000 random samples will usually find within 2 % of the optimum. Use as a baseline. |
| **Bayesian Opt** (C1/C2) | ✅ Overkill but cheap. Could converge in 200 evals. |
| **CMA-ES** (B5) | ⚠️ Excessive for 3 dims — population overhead beats the convergence benefit. |
| **Nelder–Mead** (D1) | ⚠️ Local-only. Useful as a **refinement step** after a global pass. |

### 3.2 For 10–30 params (future)

| Method | Verdict |
|---|---|
| Grid (A1) | ❌ Combinatorial explosion. |
| Random (A2) | ⚠️ Baseline only; loses badly to adaptive methods. |
| **Optuna + TPE** (C2) | ✅ **Strong default**. Industry-standard HPO; multivariate TPE handles param dependencies; supports pruning + parallel workers + study persistence. |
| **CMA-ES** (B5, via Optuna's `CmaEsSampler`) | ✅ For *purely continuous* params; faster convergence than TPE in that case. |
| BO-GP (C1) | ⚠️ Borderline. Works up to ~20 dims if you use sparse GPs; otherwise too slow. |
| SMAC / RF surrogate (C3) | ✅ For mixed continuous/discrete spaces with conditional params. |
| NSGA-II (E1) | ✅ If we eventually care about Pareto frontier (PF vs DD vs trade count). |

### 3.3 Always pair with a local refinement

After any global method converges, run **Nelder–Mead (D1)** or **L-BFGS-via-finite-differences** seeded from the best K points found. Cheap, often gains a few percent on PF.

---

## 4. Comparison matrix

For our problem specifically (3 params now, expanding; deterministic, expensive, multi-modal, NQ-tick-discrete).

| Method | Setup effort | Sample efficiency | Parallel? | Handles >10 dims? | Handles cliffs / multi-modal? | Discrete params? | Library |
|---|---|---|---|---|---|---|---|
| Grid (A1) | trivial | poor for >5d | yes | no | yes (complete) | yes | stdlib |
| Random (A2) | trivial | poor | yes | yes | partial | yes | stdlib |
| LHS / Sobol (A3) | low | medium | yes | yes | partial | yes | `scipy.stats.qmc` |
| Simulated Annealing (B1) | low | medium | partial | yes | yes | yes | `scipy.optimize.dual_annealing` |
| GA (B2) | medium | medium | yes | yes | yes | yes | `pygad`, `deap` |
| PSO (B3) | medium | medium | yes | yes | partial | continuous mostly | `pyswarms` |
| Differential Evolution (B4) | low | medium | yes | yes | yes | mostly continuous | `scipy.optimize.differential_evolution` |
| CMA-ES (B5) | medium | **high** for ≤50d | yes | yes | yes | continuous only | `cma` |
| BO-GP (C1) | medium | **very high** | partial | no (>20d slows) | yes | yes (with kernel) | `scikit-optimize`, `Ax` |
| **TPE (C2)** | **low** | **high** | **yes** | **yes** | **yes** | **yes** | **`optuna`** |
| RF surrogate (C3) | medium | high | yes | yes | yes | yes | `SMAC3` |
| Nelder–Mead (D1) | trivial | n/a (local) | no | partial | no — needs good seed | no | `scipy.optimize.minimize` |
| NSGA-II (E1) | medium | medium | yes | yes | yes | yes | `optuna`, `pymoo` |

---

## 5. Recommended approach

A two-phase strategy. **Pick one, build, iterate.**

### Phase A — today, 3 parameters (recommended starting point)

**Hybrid: Sobol seeding → TPE → Nelder–Mead refinement.**

1. **Coarse-grain Sobol sampling** (50–100 evals) to characterise the landscape and rule out garbage regions. Cheap, gives us a heatmap.
2. **Optuna with TPE sampler** for ~200–500 evals, biasing toward the regions Sobol found promising. Reports the best-K trials.
3. **Nelder–Mead local refinement** seeded from each of the top 3 trials. ~50 evals each.

Total budget: ~500 backtests. At even 10 seconds per backtest that's ~80 minutes wall time on one worker; under 10 minutes with 8 parallel workers (FastAPI is fine with multi-process workers).

**Why not just grid?** Grid gives you a complete picture but wastes most samples in bad regions. Sobol + TPE finds the same optimum with 5–10× fewer samples and produces a more usable summary (top-K trials with their full param vectors).

**Why Optuna specifically?**
- One library, multiple samplers — easy to swap TPE → CMA-ES → NSGA-II when scope grows.
- Built-in study persistence (SQLite or postgres) — survives kill/restart.
- Built-in pruning — early-stop unpromising trials at intermediate progress points (e.g., partial backtest with <50 trades).
- Trivial parallelism via `n_jobs` or distributed workers.
- Optional Optuna Dashboard for live visualisation.

### Phase B — scaling to 10+ parameters

Stay on **Optuna**. Switch the sampler:
- **`TPESampler(multivariate=True)`** — default for mixed continuous + discrete.
- **`CmaEsSampler`** — if the user only optimises continuous params (e.g. all the point-distance params).
- **`NSGAIISampler`** — when you want a Pareto front of PF / Sharpe / max-DD.

Move from "find the best point" to **conditional search spaces** — e.g., `big_candle_full_contracts` only matters when `big_candle_threshold_points < some value`. Optuna handles conditionals natively via `trial.suggest_*`.

### Phase C — production-grade

- **Walk-forward validation:** run the chosen optimum on a held-out time period. The "best" PF on the training period is *usually* an overfit; the goal is robust out-of-sample PF.
- **Multi-objective:** add Sharpe and max-DD as secondary objectives. NSGA-II gives a Pareto front; the user picks an operating point.
- **Robust objective:** instead of raw PF, optimise `PF − λ × std(PF across walk-forward folds)`. Penalises overfit configurations.

---

## 6. What "best" actually means — the elephant

Maximising PF on a single full-history backtest is **overfitting** by construction. The optimum will exploit specific historical noise.

Concrete mitigations, in order of importance:

1. **Walk-forward / rolling windows.** Optimise on bars 0 → N, evaluate on N → N + M, slide and repeat. The "best" combo is the one whose median out-of-sample PF is highest.
2. **Minimum-trades gate.** Reject any candidate with `total_trades < 30` (or similar). High PF on 5 trades is meaningless.
3. **Variance penalty.** Use `PF − λ × stddev(PF across folds)` as the objective. λ=0.5 is a reasonable starting prior.
4. **Avoid optimising too many params.** Each extra free param = more overfitting risk. Rule of thumb: at least 10 trades per param.
5. **Stability across regimes.** Bucket the data by regime (high/low vol; trend/range) and require the combo to perform in all of them.
6. **Held-out test set.** Final reported PF must be on data the optimiser never saw.

Without these, the "best" PF the optimiser reports will be a fantasy number. **Whatever search algorithm we pick, this layer is more important than the algorithm choice.**

---

## 7. Constraints and edge cases

The optimiser needs to know:
- `sl_hard_points ≥ sl_soft_points` — already enforced in the UI; the search space must reflect it. In Optuna: parameterise `sl_hard = sl_soft + δ` where `δ ≥ 0`.
- `tp_target_points > 0`, `sl_*_points > 0` — bounded below.
- **Profit factor is `None`** when there are no losses. Decide: count as +∞ (best possible) or skip (treat as invalid sample). Skipping is safer — `None` usually means insufficient data, not a winning miracle.
- **Profit factor is `0.0`** when there are no wins. Treat as `-∞` for optimisation purposes.
- Backtest may raise `ConfigurationError`. The optimiser must catch it and treat the trial as failed (return `-∞` objective).

---

## 8. Recommendation in one sentence

> **Build an Optuna-driven HPO pipeline with a Sobol → TPE → Nelder–Mead chain, walk-forward validation, and a variance-penalised PF objective. Ship phase A first; scale samplers as parameter count grows.**

This is the right shape for our scale (3 → 30 params), our oracle cost (seconds), and our deployment story (FastAPI backend that already has SSE workers).

---

## 9. Proposed integration

If this approach is approved, the implementation lands as:

```
src/
  optimization/
    __init__.py
    objective.py          # wraps BoxStrategy.backtest -> PF (with edge-case handling)
    walk_forward.py       # rolling-window cross-validation
    study.py              # Optuna study lifecycle (create, resume, report best K)
    samplers.py           # factory: 'sobol', 'tpe', 'cmaes', 'nsga2'

src/api/app.py
  POST /api/optimize/start    -> body: { param_space, sampler, budget, objective }, returns study_id
  GET  /api/optimize/{id}     -> live status, top-K trials, best PF so far
  POST /api/optimize/{id}/stop

frontend/
  components/OptimizePanel.vue  # param-range sliders + sampler dropdown + budget + start
  components/OptimizeResults.vue # top-K table + 3D scatter (PF vs sl_soft vs tp_target)
```

---

## 10. Open questions for you

1. **Optimisation objective:** raw `profit_factor`, or a variance-penalised version with walk-forward folds?
2. **Search budget:** how many backtests are we willing to spend per study? (Affects sampler choice and pruning aggressiveness.)
3. **Parallelism:** can we run multiple backtest workers in parallel on the same server? Optuna scales near-linearly across workers with a shared SQLite study.
4. **Should the optimiser surface live in the FastAPI app**, or as a separate CLI / batch job? (Live UI = nicer feedback loop; CLI = simpler.)
5. **Multi-objective from the start, or single-objective for v1?** Multi-objective adds a Pareto-front UI but takes more thought.

Answer those and I'll write the implementation plan. The algorithm choice above is robust; the open questions affect *how* we wire it in.
