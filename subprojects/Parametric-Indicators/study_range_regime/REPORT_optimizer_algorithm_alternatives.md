---
name: report_optimizer_algorithm_alternatives
description: Better optimization algorithms that avoid the "bigger space → worse result" trap — NSGA-III vs TPE/CMA-ES/GP-BO/MAP-Elites/two-stage, with a staged recommendation
---

# Optimizer algorithms — escaping the "bigger space → worse result" trap

**Why this exists:** wsh5 (split SL/TP) searched a *superset* of wsh4's space yet returned a *worse* champion,
because NSGA-III is a **finite-budget, population-based genetic** search — it returns the best point it *sampled*,
not the set maximum (full proof: `REPORT_optimizer_superset_paradox_and_system_breakdown.md`). Two mitigations
are now **implemented** (warm-start + dimension-proportional budget). This report surveys *algorithm* changes
that structurally reduce the failure and recommends a staged plan.

## 1. The failure mode (one picture)

```mermaid
flowchart LR
    A["Search space S₅ ⊃ S₄<br/>(contains a $33,592 point — proven)"] --> B{"Finite stochastic search<br/>NSGA-III · 5028 trials · 62 dims"}
    B -->|"genetic drift to<br/>asymmetric region"| C["99.8% of trials<br/>far from symmetric optimum"]
    B -->|"only 0.2% near-symmetric"| D["best near-symmetric = $7,833"]
    C --> E["best sampled = $28,228"]
    D --> E
    E --> F["⚠ worse than wsh4 $33,592<br/>(global optimum never visited)"]
    style F fill:#5a1a1a,stroke:#ff5252,color:#fff
    style A fill:#1a3a5a,stroke:#2962ff,color:#fff
```

Root cause = **density**: dimensions ↑ (volume ↑ exponentially) while trials stayed flat (even dropped). Any
finite optimizer degrades as density falls; genetic samplers also **collapse toward one basin**, starving others.

## 2. What's already implemented (mitigations, not new algorithms)

```mermaid
flowchart TD
    subgraph NOW["Implemented in optimizer.py (this change)"]
        W["Warm-start: enqueue known champions as<br/>FIRST trials (study.enqueue_trial)"] --> WG["front provably ≥ prior champion<br/>(verified: seed reproduces $142,203 full P/L)"]
        T["Dimension-proportional budget:<br/>trials = dims × 100 (--auto-trials)"] --> TG["density stays ~constant when<br/>dims grow (5,600 shared / 6,200 split)"]
        A["Acceptance gate in remote_wsi.sh:<br/>report dims+trials, require yes"] --> AG["no silent under-budgeted launch"]
    end
    style NOW fill:#13241a,stroke:#00c853,color:#fff
```

These guarantee **non-regression** and **right-sized budget**, but NSGA-III is still the engine. The rest of this
report is about *replacing or augmenting the engine* so it explores high-dim mixed spaces better.

## 3. Candidate algorithms for THIS problem

Our problem is hard in a specific way — **mixed** variables (continuous SL/TP + categorical indicator on/off +
their params), **multi-objective** (median P/L, −DD, win), **expensive** per eval (1-min indicators × 5 folds),
**deceptive** (many indicator combos look similar; the optimum is a narrow basin), **~52–62 dimensions**.

| Algorithm | Type | Multi-obj | Mixed vars | Sample-eff. | Scales to ~60d | Avoids basin-collapse | Fit for us |
|---|---|:--:|:--:|:--:|:--:|:--:|---|
| **NSGA-III** (current) | Genetic / EA | ✅ native | ✅ | low | ✅ | ✗ (collapses) | baseline; keep w/ mitigations |
| **TPE / MOTPE** | Bayesian (kernel density) | ✅ (MOTPE) | ✅ | medium | ⚠ degrades | partial | good ≤~30d; pairs well w/ stage-2 |
| **CMA-ES** | Evolution strategy | ✗ (scalarize) | ✗ continuous-only | medium-high | ✅ (continuous) | partial (restarts) | **ideal for the continuous sub-problem** |
| **GP-BO (BoTorch, qEHVI)** | Gaussian-process Bayesian | ✅ (qEHVI) | ⚠ (one-hot) | **high** | ✗ (≤~20–50d, costly) | ✅ (acquisition) | **best once dims are reduced** |
| **MAP-Elites / QD** | Quality-Diversity | ✅ (as behavior axes) | ✅ | medium | ✅ | ✅✅ (archive by niche) | **directly anti-collapse; gives a portfolio** |
| **Two-stage decomposition** | hybrid | ✅ | ✅ | **high** | ✅ | ✅ | **recommended** (see §4) |
| Hyperband / ASHA | budget scheduler | n/a | n/a | n/a | n/a | n/a | already approximated by fold pruning |

Notes that matter here:
- **GP-BO and TPE are far more sample-efficient than genetic search in moderate dims** — but both degrade past
  ~30–50 dims and dislike many categoricals. They shine *after* the dimension count is cut.
- **CMA-ES** is the gold standard for **continuous** optimization but does not handle the categorical
  indicator on/off flags — so it fits the *SL/TP + box* sub-problem, not the whole thing.
- **MAP-Elites (Quality-Diversity)** keeps an **archive of the best solution per "niche"** (e.g. binned by
  drawdown and by #indicators). It cannot collapse into one basin because it is *rewarded for diversity* — this
  is the most direct structural answer to "won't go in this trap again," and it yields a *portfolio* of champions
  (low-DD, high-return, few-indicator, …) instead of one point.

## 4. Recommended path — **two-stage decomposition** (cuts dimensions, then optimizes hard)

The single highest-leverage change: stop optimizing 62 mixed dimensions at once. Split the problem so each stage
is in a regime where a strong sampler works.

```mermaid
flowchart LR
    subgraph S1["STAGE A — pick the indicator set (discrete, ~18+ dims)"]
        direction TB
        A1["NSGA-III or bandit/QD over<br/>en_* flags only<br/>(SL/TP fixed at champion)"] --> A2["shortlist: top K indicator subsets<br/>by median fold P/L"]
    end
    subgraph S2["STAGE B — tune continuous knobs (low-dim, ~5–11 dims)"]
        direction TB
        B1["for each shortlisted subset:<br/>CMA-ES or GP-BO over<br/>sl_soft/hard/tp (+split) + gate + dd"] --> B2["sample-efficient → near-global<br/>on a tiny continuous space"]
    end
    SEED["warm-start: wsh4 + wsh5 champions"] --> S1
    S1 --> S2 --> WIN["champion = best (subset × tuned knobs)<br/>guaranteed ≥ warm-start seeds"]
    style S1 fill:#1a3a5a,stroke:#2962ff,color:#fff
    style S2 fill:#13241a,stroke:#00c853,color:#fff
    style WIN fill:#3a2f10,stroke:#ff9800,color:#fff
```

Why it works: Stage B optimizes only ~5–11 **continuous** dimensions — exactly where CMA-ES/GP-BO get close to
the global optimum with few evaluations. Stage A's discrete search is also easier with SL/TP held fixed. The
dimensionality that broke wsh5 never appears in a single search.

## 5. Staged recommendation (lowest risk → highest reward)

```mermaid
flowchart TD
    P0["P0 ✅ DONE — warm-start + ∝-budget + acceptance gate<br/>(guarantees non-regression NOW)"] --> P1
    P1["P1 — wsh6: NSGA-III + warm-start + --auto-trials,<br/>also search ifvg/breaker/cisd + split"] --> P2
    P2["P2 — pilot: MOTPE and CMA-ES on the<br/>continuous sub-problem (Optuna samplers, drop-in)"] --> P3
    P3["P3 — two-stage decomposition (§4) as the<br/>default search for new regimes"] --> P4
    P4["P4 — MAP-Elites archive for a robustness<br/>portfolio (anti-collapse, multi-champion)"]
    style P0 fill:#13241a,stroke:#00c853,color:#fff
```

- **P0 (done):** can't regress; budget scales with dimensions; nothing launches without a reported, accepted plan.
- **P1 (next run):** wsh6 inherits warm-start + `--auto-trials` automatically (one flag); cheapest real test.
- **P2:** Optuna ships `TPESampler`, `CmaEsSampler`, and `BoTorchSampler` — drop-in `sampler=` swaps, so a pilot
  is low-effort. Scalarize the 3 objectives (or use MOTPE/qEHVI) for the continuous sub-problem.
- **P3/P4:** structural wins; more engineering, but they make "bigger space → worse" essentially impossible.

## 6. Bottom line
- The trap was **search-budget/density**, not the space. **Warm-start + dimension-proportional trials (now
  implemented) already guarantee equal-or-better**, and are enough for the immediate next run.
- For a *structural* fix, **decompose** (discrete indicator-selection → continuous CMA-ES/GP-BO tuning) and/or
  adopt **MAP-Elites** for an anti-collapse portfolio. Both are staged experiments, not a rewrite — NSGA-III
  remains a valid baseline and the warm-start makes every variant safe to trial.
