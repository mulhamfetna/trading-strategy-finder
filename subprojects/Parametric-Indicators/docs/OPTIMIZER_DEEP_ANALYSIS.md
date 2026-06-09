---
name: optimizer-deep-analysis
description: Deep analysis of the WS-I optimiser — (A) exactly how it works today, (B) is NSGA-III the
  right search algorithm or is there a better option, (C) multithreading vs vectorisation for the
  compute, and (D) the higher-ROI levers. Code-grounded; measured numbers where stated; algorithm/
  parallelism trade-offs from established practice. Analysis only — no code changed.
type: reference
status: analysis
workstream: WS-I
---

# Optimiser — deep analysis: algorithm choice & parallelism

Four parts: **A** how it works now, **B** the search algorithm (is NSGA-III best?), **C** parallelism
vs vectorisation, **D** the highest-ROI levers and a verdict. Facts about *our* code are grounded in
the source; algorithm/parallelism trade-offs are from established optimisation/HPC practice and are
labelled as judgement where they are not measured.

---

## PART A — How the current optimiser works

### A.1 The shape of the problem
For **one decision timeframe** we search a single parameter vector that defines a complete strategy,
and score it by how well it trades NQ over 2025–26. The search runs independently per timeframe
(7 studies), and within a timeframe many worker processes cooperate on one shared study.

### A.2 The search space (one trial = one vector) — `optimizer.py:_suggest_indicators` + `objective`
A mixed, high-dimensional space (~50 dimensions):
- **Box / risk (continuous + int + categorical):** `sl_soft` (per-TF bounds), `sl_hard = sl_soft + δ`
  (δ ≥ 0, enforces hard ≥ soft), `tp`, `gate_pct ∈ [0,100]`, `dd_limit ∈ [0,5000]`,
  `cooldown ∈ [0, cap(TF)]` (int), `flip ∈ {F,T}`, `k ∈ {1..5}` (int).
- **Indicator layer:** for **each of the 15 indicators**: a categorical `en_<key> ∈ {F,T}` (on/off)
  **plus all of its internal params** (e.g. EMA fast/slow, RSI n/lower/upper). Crucially the space is
  **rectangular** — the params are *always* suggested even when the indicator is off — so the EA's
  crossover/mutation stay well-defined and a turned-off indicator that turns on later already has
  sensible genes. That is ~30 indicator-internal dims on top of the box dims.

This is **mixed-integer + categorical + continuous + (logically) conditional** — a regime that rules
out some classic algorithms (see Part B).

### A.3 The objectives + the constraint — `objective`
Three objectives, **all maximised** (`directions=["maximize"]×3`):
- `obj0 = median fold P/L` — profit, but the **median across walk-forward folds** (consistency, not
  one lucky stretch);
- `obj1 = −worst-fold max-drawdown` — conservative risk (maximising the negative = minimising the
  worst fold's DD);
- `obj2 = median fold win-rate`.

Plus a **feasibility constraint** (constrained domination, via Optuna `constraints_func`):
`full-period maxDD ≤ 25 % of full-period P/L` (and P/L > 0). Infeasible trials are dominated by
feasible ones, so the front is pushed into the "safe" region.

The output is the **feasible Pareto front** — not a single winner — a menu of profit↔drawdown↔win
trade-offs.

### A.4 How one trial is scored — `folds.score_walkforward` + `core.backtest_metrics`
- The history is split into **5 equal-calendar-time folds**; fold 0 is a causal gate warm-up (not
  scored); folds 1–4 are each an **independent** backtest (no equity/breaker leakage between folds).
- Plus **one full-period backtest** for the feasibility constraint.
- ⇒ **~5 backtests per trial.** A trial is pruned (`TrialPruned`) if any scored fold has < `min_trades`
  trades (too thin to trust).

### A.5 The sampler — `NSGAIIISampler(seed, constraints_func)`
**NSGA-III** = a reference-point-based many-objective evolutionary algorithm. Population-based: it
keeps a population of trials, ranks them by non-dominated sorting, and maintains spread across the
objective space using a set of **reference points** (this is the part that replaces NSGA-II's
crowding distance and is why NSGA-III is preferred for **≥3 objectives**). New trials are produced by
crossover + mutation of good parents. Constraints are folded into the domination rule.

### A.6 Persistence & resumption
Each TF is an Optuna study `wsh3_<tf>` in **one shared SQLite DB** (`optimize/studies/wsh.db`),
created with `load_if_exists=True`. Trials are durable; a sweep can stop and resume; multiple
processes append to the same study.

### A.7 The parallel-execution model — `optimize/server/remote_wsi.sh`
This is the key operational fact: **trial-level parallelism via multiple OS processes**, not threads.
- The engine is **GIL-bound (~1 core per process)**, so the server launches **many worker processes
  per study** (weighted `[1m]=12 … [4h]=1`, summing ≈ 30 on the 32-core box). Each worker runs
  `optimizer.py <tf>` → `study.optimize(...)` single-threaded, and they **share trials through the
  SQLite study** (Optuna's RDB storage serialises concurrent trial bookkeeping).
- So: **embarrassingly parallel at the trial level** (each worker grabs the next trial), with the
  shared DB as the coordination point.

### A.8 The fast engine (vectorisation) — `optimize/fast_engine.py`
The reference engine walks 1-minute bars in a Python loop (slow). The fast engine reproduces the
**exact same decisions** but resolves each trade's exit with **numpy boolean scans / `argmax`**
(first-touch of soft-SL / hard-SL / TP). It still has an **outer Python `while` loop over decision
bars** (per trade: `searchsorted` to find the entry minute, `argmax` for the first exit touch), so it
is "vectorised *within* a trade's exit search," not a single whole-history vector op. This is what
makes the decision-TF trial cost ~1.4 s.

### A.9 Measured cost (this machine, 4h, full data)
- decision-TF indicators: **1.4 s/trial** (0.6 s folds + 0.8 s full).
- 1-minute indicators: **30.4 s/trial** (10.7 s folds + 19.7 s full) — dominated by the stateful SMC
  `order_block` Python loop over ~487 k 1-minute bars.

---

## PART B — Is NSGA-III the best search algorithm, or is there a better option?

### B.1 What this regime actually needs
1. **Many-objective (3)** with a true Pareto front, not a scalarisation.
2. **Mixed/categorical/conditional** variables (on/off switches + their params).
3. **Constraint** handling (DD ≤ 25 %·P/L).
4. **Massively parallel** (30+ workers) — the algorithm must stay efficient when many trials are
   in-flight with stale information.
5. Cost regime matters: **cheap trials** (decision-TF, ~1.4 s ⇒ tens of thousands are fine) vs
   **expensive trials** (1-minute, ~30 s ⇒ sample-efficiency becomes king).

### B.2 The candidates, judged against that
| Algorithm | Multi-obj | Mixed/categorical | Parallel-friendly | Sample-efficient | Fit here |
|---|---|---|---|---|---|
| **NSGA-III** (current) | ✅ native, ref-points (best ≥3 obj) | ✅ via EA operators | ✅✅ population → embarrassingly parallel | ✗ needs many evals | **Strong default** |
| NSGA-II | ✅ but crowding degrades >2 obj | ✅ | ✅✅ | ✗ | Worse than III for 3 obj — III is the right upgrade |
| **MOTPE** (Optuna multi-obj TPE) | ✅ | ✅✅ handles conditional natively | ⚠️ model updates serialise; OK with stale | ✅ better than EA early | **Best alt for expensive (1-min) trials** |
| **BoTorch qNEHVI / qEHVI** (GP Bayesian, multi-obj hypervolume) | ✅✅ gold-standard | ⚠️ categorical/conditional harder | ⚠️ q-batch parallel, but GP is O(n³) | ✅✅✅ fewest evals | **Best for a SMALL expensive budget (≤~hundreds)**; chokes at 21k trials / ~50 dims |
| CMA-ES | ✗ single-obj (needs scalarisation) | ✗ continuous-only | ✅ | ✅ (continuous, low-dim) | Poor fit — mixed/categorical/3-obj |
| Differential Evolution / PSO | ⚠️ via MO variants | ⚠️ continuous-leaning | ✅✅ | ~ EA | Comparable to NSGA, no advantage |
| Random / Sobol (quasi-MC) | n/a (baseline) | ✅ | ✅✅✅ trivial | ✗ | Great **seed/baseline**, surprisingly OK in high dim |
| **ASHA / Hyperband (pruner, not a sampler)** | — | — | ✅✅ | **massive on expensive trials** | **Highest-ROI add-on (see B.4)** |

### B.3 Verdict on the sampler
**NSGA-III is a defensible, near-best default** for this exact regime (3 objectives, mixed/categorical
~50-dim, constraint, 30-worker population parallelism, many cheap evals). It is correctly chosen over
NSGA-II (crowding distance degrades beyond 2 objectives). For the **decision-TF (cheap) sweep there is
little to gain by switching samplers** — NSGA-III + more trials is fine.

The picture flips for the **1-minute (expensive, 30 s) sweep**, where each evaluation is precious:
- **MOTPE** would likely reach a good front in **fewer trials** than NSGA-III (Bayesian density models
  beat blind EA crossover early), and it handles the on/off-then-params *conditional* structure more
  naturally. Worth A/B-testing as the sampler for the expensive regime.
- **BoTorch qNEHVI** is the most sample-efficient multi-objective method in existence, but its GP
  scales **cubically** in #observations and **degrades in ~50 dimensions** — so it only fits a *small*
  budget (a few hundred expensive trials, ideally on a reduced search space), not a 21k sweep.

### B.4 The bigger lever than the sampler: **pruning / early-stopping**
The optimiser spends ~5 backtests per trial *before* it knows the trial is bad. With 30 s trials that
is wasteful. **Score the cheapest fold first and prune obviously-bad trials before paying for the
remaining folds + the full-period backtest.** Optuna supports this directly (median pruner / ASHA /
Hyperband pruner with intermediate `trial.report()`s). On expensive trials this can cut total compute
**2–5×** — far more than any sampler swap. **This is the single highest-ROI search change.**

---

## PART C — Multithreading vs vectorisation for processing the data

### C.1 The constraint that decides everything: the GIL
CPython's Global Interpreter Lock means **pure-Python loops do not run in parallel across threads** in
one process. numpy *releases* the GIL during its C kernels, so threads help *numpy-heavy* code a
little — but our remaining hot path (`order_block` and the other stateful SMC machines) is a **Python
loop**, which threads cannot speed up. This single fact shapes the whole answer.

### C.2 The three ways to go faster, and where each applies
| Approach | What it parallelises | Speedup here | Difficulty | Stability |
|---|---|---|---|---|
| **Process-level (multiprocessing)** — *current server model* | whole trials, across cores | ✅✅ near-linear to #cores (already used: 30 workers) | low (already built) | **high** (isolated processes; SQLite coordinates) |
| **Vectorisation (numpy)** — *current within-trial* | the inner math (C kernels) | ✅✅ for MA/oscillator indicators; already done | medium | **high** (pure numpy) |
| **Thread-level within a trial** | inner loops | ❌ ~none for Python loops (GIL); small for numpy ops that release GIL | medium | medium (races, GIL surprises) |
| **Numba `@njit`** (JIT to native, optional `nogil`/`parallel`) | the stateful Python loops (order_block) | ✅✅✅ for the SMC loops (10–100×) | medium–high (rewrite loop in numba-subset) | medium (extra dep; first-call JIT cost; debugging) |
| **GPU (CuPy/torch)** | massively parallel array ops | overkill; data-transfer + branchy state machine ill-suited | high | low for this workload |

### C.3 Is multithreading beneficial, or is vectorisation enough?
**For this workload, intra-trial multithreading is *not* worth it.**
- Trial-level parallelism is already handled the right way — **multiprocessing** (30 worker processes)
  — which is GIL-immune, simple, and already in production (`remote_wsi.sh`). Adding threads *inside* a
  trial competes with that for the same cores and gives little, because the hot loop is Python (GIL).
- **Vectorisation is "enough" for the indicators that vectorise** (done: stochastic, MFI; EMA/MACD/etc.
  already cheap). The part vectorisation *can't* easily reach is the **stateful SMC loop** — and for
  that, the right tool is **Numba JIT**, not threads.

**So the ranked compute options are:** keep multiprocessing for trials (already optimal) → keep
vectorising what vectorises → **Numba-JIT `order_block`/structure/fvg** if you must keep SMC in a
1-minute search → only then consider threads (and expect little).

### C.4 Pros / cons of adding more parallelism
- **More worker processes (scale-out):** + near-linear speedup, trivial, stable; − SQLite write
  contention rises with worker count (see D.3), and memory × workers (each loads the 1-minute frame).
- **Numba on the SMC loops:** + could turn `order_block` from ~15 s to <1 s (the whole 1-minute trial
  from ~30 s toward ~5 s, i.e. the ~2 h sweep instead of ~6 h); − adds a dependency, JIT warm-up on
  first call, and the loop must be rewritten in Numba's typed subset and re-parity-tested.
- **Threads:** + none meaningful here; − GIL, race-condition risk, harder to reason about. Skip.

---

## PART D — Other (higher-ROI) levers, and the verdict

1. **Early pruning (B.4)** — score 1 fold, prune, then pay for the rest. **2–5× on expensive trials.**
   Highest ROI of everything here, sampler-agnostic.
2. **Numba-JIT the stateful SMC indicators (C.3)** — removes the dominant 1-minute cost. High ROI *if*
   SMC must stay in the 1-minute search; otherwise just exclude them for the first pass.
3. **Shrink the search space** — the rectangular "all 15 on/off + all params" space is ~50-dim; every
   extra dim costs evaluations. Group/condition indicators, or search a curated subset first. Improves
   *every* sampler's efficiency.
4. **Storage contention at high worker counts (A.7)** — SQLite is a single-writer; ~30 workers
   hammering one `wsh.db` can serialise on writes. Mitigations: Optuna `JournalStorage` (file-append,
   less locking) or per-worker studies merged at the end. Matters more as you add workers.
5. **Warm-start** — seed the study with the known decision-TF champions (`enqueue_trial`) so the EA
   starts near good regions instead of cold. Cheap, helps convergence.
6. **Cache the param-independent work** — box Stage-1 signals are already precomputed once (`sig_int`);
   the per-trial cost is the *param-dependent* indicator gate, which genuinely must recompute. Little
   left to cache without memoising indicator sub-results across similar trials (complex).

### Bottom-line recommendations (prioritised by ROI)
1. **Keep NSGA-III** — it is the right default for this 3-objective, mixed, population-parallel regime;
   swapping samplers is not where the win is.
2. **Add early pruning** (median/ASHA pruner on the first fold) — biggest single win for the expensive
   1-minute sweep; sampler-agnostic; low risk.
3. **For the 1-minute sweep, either exclude the stateful SMC indicators (fast, ~2 h) or Numba-JIT them**
   (keeps them, ~2 h, more work).
4. **Keep parallelism as multiprocessing**; do **not** add intra-trial threads (GIL ⇒ no benefit).
   Watch SQLite write-contention as workers scale; switch storage if it bites.
5. **Optionally A/B MOTPE vs NSGA-III** *only* in the expensive 1-minute regime, where sample
   efficiency matters; and reserve **BoTorch qNEHVI** for a small, reduced-space, high-value budget —
   not a 21k sweep.

_All measured numbers are from this machine (4h, full 2025–26 data). Algorithm/parallelism trade-offs
are established practice applied to this code; the MOTPE/pruning/Numba claims are hypotheses to
A/B-test, not yet measured here._
