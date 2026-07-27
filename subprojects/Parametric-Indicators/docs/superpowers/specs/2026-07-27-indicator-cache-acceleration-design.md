# Design — Accelerating Indicator Cold-Miss Compute (Numba + GPU batch)

**Date:** 2026-07-27 · **Issue:** #54 · **Branch:** `research/indicator-cache-acceleration`
**Type:** research (pre-registered criterion) · **Hard rule:** speed only — results must not change.

---

## 1. Context (what is actually true today)

A single backtest spends **~98–99% of wall-clock computing indicators** on the 486,970-row 1-minute
frame; the trade/exit engine (`fast_engine`, vectorized + memoized, faster/trial than vectorBT) is ~1–2%.
The optimizer is two-stage: **compute indicator signals → backtest on them**, run as ~30 shared-nothing
Optuna worker processes against a Postgres trial store.

Two facts, established from the codebase this session, define the problem:

### Finding A — "precompute everything" is a combinatorics wall, not a bandwidth wall
The 165 registered indicators (`indicators/library.py:SCHEMA`) carry discrete **stepped** parameter grids.
Their full Cartesian product is **~4.0 billion parameterizations** (top contributors: Schaff Trend Cycle
2.32B, stoch-RSI 1.18B, vol_ratio 106M, Kalman 100M, wavetrend 96M …). Each `directions()` output is
~1 MB (cdir+vdir int8 × 486,970 bars), so materializing the full grid for **one** instrument ≈ **3.9 PB**.
No storage tier (RAM, Redis, tmpfs, SSD, VRAM) changes this. **Precomputing "all possibilities" is out.**

### Finding B — the on-demand cache the question imagines already exists
`ind.directions()` — the expensive kernel — is a **pure function of `(indicator, params, price series)`**,
independent of K, retrace/wait, SL/TP, the drawdown breaker, and the other enabled indicators. The repo
already exploits this:

- `optimize/core.py` — in-process `_VOTE_MEMO` keyed by `(slice_sig, use1, indicator_key, mode, params)`.
- `optimize/vote_cache.py` — disk `.npy` cache under `/tmp/wsh_vote_cache/`, **shared across worker
  processes + watchdog respawns**, atomic writes, versioned key. Result-neutral by construction.

Memory records the payoff already banked: *memoization took candidate-L1 from 24 → 1286 trials/min.*

**Conclusion.** The open question is not "should we cache" (done) but **"can we make the COLD MISS — the
first time each `(indicator, params)` is computed — dramatically cheaper, and is `.npy`-on-SSD the right
substrate?"** The actually-visited set across a full sweep is only tens of thousands of arrays, heavily
re-requested across 30 workers and 6 timeframes — so cold-miss cost and substrate latency are the levers.

---

## 2. Goals / non-goals

**Goals**
1. Quantify, on the real server, where sweep time goes: cold-miss compute vs warm-cache hits vs I/O.
2. **Primary lever (user priority): cut cold-miss compute** via (a) Numba / streaming-recurrence on CPU,
   (b) **GPU batch-compute** — many parameterizations of one indicator in one batched kernel — benchmarked
   on a requested NVIDIA box.
3. Secondary analyses (report + smaller benchmarks): cache **substrate** (`.npy` vs tmpfs/Redis/Arrow/
   shared-memory/DuckDB) and cache **level** (re-key at `directions()` to kill the 3× `mode` duplication
   and share across the 6 decision TFs).
4. A ranked, evidence-backed recommendation + the PoC code, all committed locally.

**Non-goals**
- Changing any result (bit-identical parity is a hard gate).
- Precomputing the full grid (Finding A).
- Replacing the Optuna/Postgres orchestration (covered by the 2026-06-11 scaling study; out of scope).
- Distributed multi-node execution (deferred).

---

## 3. Research questions & pre-registered hypotheses

| # | Question | Hypothesis to test | Primary metric |
|---|----------|--------------------|----------------|
| Q1 | Does GPU batch-compute of the top-N costliest indicators beat CPU on cold misses? | GPU wins only when a single kernel amortizes host↔device transfer over **many** param-combos of one indicator (high arithmetic intensity); loses on sequential/stateful ones (SMC, EMA-family recurrences). | cold-miss arrays/sec, incl. transfer + provisioning |
| Q2 | Does Numba/streaming-recurrence cut cold-miss CPU cost bit-identically? | Yes for the classes flagged in `RESEARCH_indicator_recurrence_relations.md` (monotonic-deque stoch, mfi sliding-sum, EMA-family lfilter/njit); no for `cci` (no recurrence). | cold-miss wall-clock, parity pass/fail |
| Q3 | Is `.npy`-per-file the substrate bottleneck under 30 workers? | tmpfs/`/dev/shm` and shared-memory beat SSD on hit latency; Redis/Arrow help cross-process sharing but add serialization; DuckDB/Parquet best for analytics, not hot-path. | warm-hit latency, hit-rate |
| Q4 | Does re-keying the cache at `directions()` (not vote/mode) raise reuse? | Yes — collapses 3× mode duplication and shares 1-min arrays across all 6 decision TFs, result-neutral. | distinct-arrays computed per sweep |

**Dumb controls (mandatory).** Every lever is compared against (i) the current **warm `.npy` cache** and
(ii) simply **adding CPU workers**. A lever must beat both to be recommended.

---

## 4. Architecture of the PoC

Three isolated, independently-shippable pieces. None touches production defaults; all gated on parity.

### 4.1 Instrumentation & baseline harness (`optimize/perf/cache_probe.py`)
- Wrap `vote_cache.get/put` + `_cached_votes` with counters: hits, misses, cold-compute seconds,
  bytes read/written, per-indicator breakdown. Emit a JSON/CSV profile per run.
- Run one **real** study slice on the AMD server (live progress log per the never-wait-blindly rule);
  produce the ground-truth cold/warm/I-O split that every later number is measured against.

### 4.2 Cold-miss accelerator (PRIMARY)
- **CPU track:** apply the already-researched exact wins (deque stoch, mfi sliding-sum, EMA-family via
  `scipy.signal.lfilter`/Numba `@njit`) behind a feature flag, each with a bit-identical parity test vs the
  current pure-Python reference (the repo's established pattern).
- **GPU track:** select the top-N most-expensive *vectorizable* indicators (from 4.1's per-indicator
  breakdown — expected: rolling-window oscillators, NOT the stateful SMC loops). Implement a **batched**
  CuPy / Numba-CUDA kernel that computes many `(param-combo)` columns for one indicator in a single
  device call. Benchmark cold-miss throughput vs CPU **including** host↔device transfer and one-time
  provisioning; compute the break-even #combos.

### 4.3 Substrate & level micro-benchmarks (SECONDARY)
- Substrate: a standalone bench that stores/loads a fixed set of real arrays via `.npy` (current),
  `/dev/shm`, `multiprocessing.shared_memory`, Redis, Arrow/Plasma, DuckDB — measured under a simulated
  30-reader load. Report latency + concurrency behavior only (no production swap in this issue).
- Level: prototype a `directions()`-keyed cache adapter and measure distinct-array count on a real sweep
  vs today's vote/mode key (pure counting; result-neutral).

### 4.4 GPU provisioning
Request an NVIDIA box (per approval). Record exact GPU/driver/CUDA + CuPy versions in the report for
reproducibility. If provisioning stalls, the CPU track + a desk estimate of the GPU ceiling still ship;
the GPU benchmark becomes a fast follow-up rather than a blocker.

---

## 5. Method & guardrails

- **Server-only compute**, never the local box; every long run gets a live progress log + short polls.
- **Parity is a hard gate**: `optimize/test_parity.py`, `test_indicator_parity.py`, full `pytest`, and a
  champion reproduction must hold after any accelerator is toggled on. A reference pure-Python/CPU path is
  kept to diff against every optimized path.
- **No silent defaults**: print the params/indicators actually used in each benchmark; a "speedup" that
  changed a vote is a failure, not a win.
- **Local = source of truth**: all PoC outputs + report scp'd back and committed on this branch.
- **Online prior-art pass** feeds §3 (vectorbt / nautilus / Qlib / TA-Lib / Optuna caching practice;
  cuDF/CuPy GPU technical-analysis; Arrow Plasma; feature stores) — cited in the report.

## 6. Deliverable (report)
`optimize/REPORT_indicator_cache_acceleration.md` — verbose, no-jargon, concrete-$ where relevant,
Mermaid-only visuals, explicit "what went well / what went wrong", and a decision matrix ranking every
lever against the two dumb controls, ending in a GO/NO-GO per §7.

## 7. Pre-registered success criterion
A lever is **GO** only if, on a fixed parity fold, it (a) produces **bit-identical** votes AND (b) shows a
**measured ≥ 3× cold-miss wall-clock reduction** on the server (GPU: after transfer + provisioning
overhead), AND (c) **beats both dumb controls**. A quantified **NO-GO** is a valid, publishable outcome.

## 8. Risks
| Risk | Mitigation |
|------|------------|
| GPU float ops diverge from CPU → breaks parity | keep CPU reference; assert bit/≈-identity on a fixed fold before any adoption; GPU may be accepted only for indicators where it reproduces exactly |
| GPU provisioning latency blocks the study | CPU track + desk-estimated GPU ceiling ship independently; GPU benchmark is a follow-up, not a gate |
| Stateful/sequential indicators (SMC, EMA recurrences) don't vectorize on GPU | scope GPU to the rolling-window oscillators surfaced by 4.1; leave sequential ones on CPU/Numba |
| Substrate swap introduces a stale/poisoned array | versioned key already exists; benchmarks are read-only, no production swap in this issue |
| Scope creep into orchestration/DB | explicitly out (§2); the 2026-06-11 scaling study owns that axis |

## 9. YAGNI
No production substrate migration, no distributed executor, no full-grid materialization, no dashboard
work in this issue. This issue delivers **measurements + a recommendation + PoC code**; adoption of any
winning lever is a separate, criterion-gated follow-up issue.
