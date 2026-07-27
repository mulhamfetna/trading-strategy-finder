# Indicator Cold-Miss Acceleration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline) to implement this
> plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. **Do NOT use analysis subagents**
> (user rule: work inline, re-verify any mechanical parallel search yourself).

**Goal:** Measure where the optimizer sweep's indicator time goes on the real server, then prove or
disprove — with bit-identical parity — whether Numba/recurrence (CPU) and GPU batch-compute cut
cold-miss indicator wall-clock by ≥3×, ranked against two dumb controls.

**Architecture:** A read-only instrumentation harness first establishes the ground-truth cold/warm/I-O
split on one real study. Cold-miss accelerators (CPU Numba/recurrence, then a batched CuPy/Numba-CUDA
GPU kernel for the top-N vectorizable indicators) are each built behind a feature flag and gated on a
bit-identical parity test against the existing pure-Python path. Secondary micro-benchmarks cover cache
substrate and cache-level reuse. A final report ranks every lever.

**Tech Stack:** Python, numpy, Numba (`@njit`), scipy.signal.lfilter, CuPy / Numba-CUDA (GPU box),
Optuna+Postgres (existing), pytest (parity gates). Server: AMD (CPU) now; NVIDIA (requested) for GPU.

## Global Constraints

- **Speed only — results MUST NOT change.** Every accelerator is gated on bit-identical votes: verbatim
  parity `$7,735 / $3,670 / n=66` (`optimize/test_parity.py`) + `optimize/test_indicator_parity.py` +
  full `pytest` + a champion reproduction (wsh4 4h `$142,203 ± rounding`).
- **No heavy compute on the local box.** All benchmarks run on the server; every long run emits a live
  progress log + short polls (never a silent blocking wait).
- **Local = source of truth.** Every PoC output + report is scp'd back and committed on this branch.
- **No silent defaults.** Print the exact indicators/params used in every benchmark run.
- **Pre-registered GO criterion:** a lever is adopted only if bit-identical AND ≥3× cold-miss reduction
  AND it beats both dumb controls (warm `.npy` cache; +CPU workers). A quantified NO-GO is a valid result.
- Working dir: `subprojects/Parametric-Indicators/` on branch `research/indicator-cache-acceleration`.

---

## File Structure

- `optimize/perf/__init__.py` — new package for perf harnesses.
- `optimize/perf/cache_probe.py` — instrumentation: wraps vote_cache to count hits/misses/cold-seconds/bytes.
- `optimize/perf/test_cache_probe.py` — unit tests for the counters (result-neutral wrapper).
- `optimize/perf/run_baseline.py` — server entry: run one real study slice, emit the cold/warm/I-O profile.
- `optimize/perf/cold_accel.py` — CPU cold-miss accelerators (deque stoch, mfi sliding-sum, EMA lfilter/njit) behind a flag.
- `optimize/perf/test_cold_accel_parity.py` — bit-identical parity: accelerated vs pure-Python reference.
- `optimize/perf/gpu_batch.py` — batched GPU kernel for the top-N vectorizable indicators (CuPy/Numba-CUDA).
- `optimize/perf/test_gpu_batch_parity.py` — GPU-vs-CPU bit/≈-identity on a fixed fold (skipped if no GPU).
- `optimize/perf/bench_substrate.py` — substrate micro-bench (.npy vs shm/Redis/Arrow/DuckDB) under N readers.
- `optimize/perf/bench_cache_level.py` — count distinct arrays: vote/mode key vs directions() key.
- `optimize/REPORT_indicator_cache_acceleration.md` — final report (Mermaid, verbose, decision matrix, GO/NO-GO).
- `docs/PRIOR_ART_indicator_caching_gpu.md` — online prior-art notes feeding the report.

---

## Task 0: Online prior-art pass (research, no code)

**Files:**
- Create: `docs/PRIOR_ART_indicator_caching_gpu.md`

**Interfaces:**
- Produces: cited findings the report's §"prior art" and each lever's "is this already solved" note reuse.

- [ ] **Step 1: Search & read** — vectorbt / vectorbtpro indicator caching & broadcasting; NautilusTrader
  indicator model; Microsoft Qlib expression/feature cache; TA-Lib vs pandas-ta vs `talipp` (incremental);
  Optuna storage/caching practice; GPU technical-analysis (`cuDF`, CuPy rolling, `cuIndicators`/RAPIDS),
  Arrow Plasma / shared-memory object stores; feature-store cold-vs-warm patterns. (WebSearch/WebFetch.)
- [ ] **Step 2: Write notes** — for each: what they do, whether it maps to our pure-`directions()`
  function, and the one transferable idea. One paragraph each, with URLs.
- [ ] **Step 3: Commit**

```bash
git add docs/PRIOR_ART_indicator_caching_gpu.md
git commit -m "docs(perf): online prior-art notes on indicator caching + GPU TA (#54)"
```

---

## Task 1: Instrumentation harness (counters)

**Files:**
- Create: `optimize/perf/__init__.py`, `optimize/perf/cache_probe.py`, `optimize/perf/test_cache_probe.py`

**Interfaces:**
- Consumes: `optimize/vote_cache.py` (`get`, `put`, `disk_key`), `optimize/core._cached_votes`.
- Produces: `cache_probe.Probe` with `.install()` / `.uninstall()` / `.snapshot() -> dict` returning
  `{hits, misses, cold_seconds, bytes_read, bytes_written, per_indicator: {key: {misses, cold_seconds}}}`.

- [ ] **Step 1: Write the failing test**

```python
# optimize/perf/test_cache_probe.py
import numpy as np
from optimize import vote_cache
from optimize.perf.cache_probe import Probe

def test_probe_counts_hits_and_misses_without_changing_arrays(tmp_path):
    vote_cache.set_cache_dir(tmp_path)
    vote_cache._clear_disk_cache()
    p = Probe(); p.install()
    dkey = vote_cache.disk_key(("sig",), True, "rsi", "confirm", (("n", 14),))
    arr = np.arange(10, dtype=np.int8)
    assert vote_cache.get(dkey) is None          # miss
    vote_cache.put(dkey, arr)
    got = vote_cache.get(dkey)                    # hit
    p.uninstall()
    snap = p.snapshot()
    assert snap["misses"] == 1 and snap["hits"] == 1
    assert np.array_equal(got, arr)              # result-neutral
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest optimize/perf/test_cache_probe.py -v` — Expected: FAIL (`cache_probe` not found).

- [ ] **Step 3: Implement `cache_probe.Probe`** — monkeypatch `vote_cache.get`/`put` to count and time,
  delegating to the originals; `install()` saves originals, `uninstall()` restores them; a cold-compute
  timer wraps the miss branch by also patching `core.runner._ind_vote` (increment `misses` + accumulate
  wall-clock, keyed by indicator key parsed from the call). Return counts via `snapshot()`.

- [ ] **Step 4: Run test to verify it passes** — Run: `pytest optimize/perf/test_cache_probe.py -v` — Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add optimize/perf/__init__.py optimize/perf/cache_probe.py optimize/perf/test_cache_probe.py
git commit -m "feat(perf): result-neutral cache probe counting hits/misses/cold-seconds (#54)"
```

---

## Task 2: Baseline profile on the real server

**Files:**
- Create: `optimize/perf/run_baseline.py`

**Interfaces:**
- Consumes: `cache_probe.Probe`, the existing study launcher (`optimize/optimizer.py` / `core.run_l1_cached`).
- Produces: `optimize/perf/results/baseline_<instrument>_<tf>.json` — the ground-truth cold/warm/I-O split
  and the **ranked per-indicator cold-cost table** that Task 5 (GPU top-N) consumes.

- [ ] **Step 1: Write `run_baseline.py`** — install the Probe, run a fixed, seeded N-trial slice of one
  real study (default: NQ 4h, cold cache) with `ind_1min=True`; print the params used (no-silent-defaults);
  on finish dump `snapshot()` + wall-clock to JSON. Emit a progress line every M trials (never-wait-blindly).
- [ ] **Step 2: Dry-run locally tiny** — `python -m optimize.perf.run_baseline --trials 3 --smoke` to prove
  it runs and writes JSON (3 trials is negligible, not "heavy compute").
- [ ] **Step 3: Run on server** — scp/pull the branch to the AMD box, run the real slice (e.g. `--trials 200`)
  under `nohup` with a tailed log; poll the progress log. **Do not block silently.**
- [ ] **Step 4: Pull results back** — scp `baseline_*.json` + log to local; commit. Record the headline
  split (cold % / warm-hit % / I-O %) and the top-N costliest indicators in the commit message.
- [ ] **Step 5: Commit**

```bash
git add optimize/perf/run_baseline.py optimize/perf/results/baseline_*.json
git commit -m "perf: server baseline — real cold/warm/IO split + per-indicator cold-cost ranking (#54)"
```

---

## Task 3: CPU cold-miss accelerators (parity-gated)

**Files:**
- Create: `optimize/perf/cold_accel.py`, `optimize/perf/test_cold_accel_parity.py`

**Interfaces:**
- Consumes: `indicators/classic.py` reference functions (loops), `indicators/library.py` indicator specs.
- Produces: `cold_accel.accelerated_directions(key, ctx, params) -> (cdir, vdir)` matching
  `Indicator.directions` **bit-identically**, and a flag `COLD_ACCEL` (default OFF ⇒ parity preserved).

- [ ] **Step 1: Write the failing parity test** (start with the exact wins from
  `RESEARCH_indicator_recurrence_relations.md`: monotonic-deque stochastic max/min, mfi sliding-sum, EMA
  family via `lfilter`/`@njit`):

```python
# optimize/perf/test_cold_accel_parity.py
import numpy as np
from indicators import library
from indicators.runner import market_context
from optimize.perf import cold_accel

def _ctx(seed=0, n=5000):
    rng = np.random.default_rng(seed); c = 21000 + np.cumsum(rng.normal(0, 5, n))
    import pandas as pd
    df = pd.DataFrame({"Date": pd.date_range("2020", periods=n, freq="min"),
                       "Open": c, "High": c+2, "Low": c-2, "Close": c, "Volume": rng.integers(1,100,n)})
    return market_context(df)

def test_stochastic_accel_bit_identical():
    ctx = _ctx(); params = {"k": 14, "d": 3, "smooth": 3, "overbought": 80, "oversold": 20}
    ref_c, ref_v = library.build("stochastic", params).directions(ctx)
    acc_c, acc_v = cold_accel.accelerated_directions("stochastic", ctx, params)
    assert np.array_equal(acc_c, ref_c) and np.array_equal(acc_v, ref_v)
```

- [ ] **Step 2: Run to verify it fails** — Run: `pytest optimize/perf/test_cold_accel_parity.py -v` — Expected: FAIL.
- [ ] **Step 3: Implement the deque/sliding-sum/lfilter accelerators** in `cold_accel.py`, one indicator at
  a time; each falls back to the reference for any indicator not yet ported (so the flag is always safe).
- [ ] **Step 4: Run to verify PASS** for each ported indicator; then run the full parity gate:
  `pytest optimize/test_parity.py optimize/test_indicator_parity.py optimize/perf/test_cold_accel_parity.py -v`.
- [ ] **Step 5: Micro-bench** the ported set (cold-compute time accel vs reference) via a small timing loop
  in the test file's `__main__`; record the per-indicator speedup.
- [ ] **Step 6: Commit**

```bash
git add optimize/perf/cold_accel.py optimize/perf/test_cold_accel_parity.py
git commit -m "feat(perf): CPU cold-miss accelerators (deque/sliding-sum/lfilter), parity-gated (#54)"
```

---

## Task 4: Provision the NVIDIA box

**Files:** none (ops).

**Interfaces:**
- Produces: an SSH-reachable GPU host + recorded `nvidia-smi` / CUDA / CuPy versions for the report.

- [ ] **Step 1: Request/provision** — the interactive login or provider command is the USER's to run;
  surface it and ask them to run it via `! <command>` so output lands in-session. **Blocked-on-user.**
- [ ] **Step 2: Record environment** — once reachable, capture `nvidia-smi`, `nvcc --version`,
  `python -c "import cupy; print(cupy.__version__)"` into `optimize/perf/results/gpu_env.txt`.
- [ ] **Step 3: Commit** the env capture (no secrets):

```bash
git add optimize/perf/results/gpu_env.txt
git commit -m "chore(perf): record GPU box environment (driver/CUDA/CuPy) (#54)"
```

---

## Task 5: GPU batch-compute PoC (top-N, parity-gated)

**Files:**
- Create: `optimize/perf/gpu_batch.py`, `optimize/perf/test_gpu_batch_parity.py`

**Interfaces:**
- Consumes: Task 2's per-indicator ranking (choose top-N **vectorizable** ones — rolling-window
  oscillators; exclude stateful SMC), the reference `directions()`.
- Produces: `gpu_batch.batch_directions(key, ctx, param_grid) -> np.ndarray[len(grid), 2, N]` computing
  many param-combos of one indicator in a single device call; result copied back to host int8.

- [ ] **Step 1: Write the failing GPU parity test** (auto-skip when no CUDA):

```python
# optimize/perf/test_gpu_batch_parity.py
import numpy as np, pytest
cupy = pytest.importorskip("cupy")
from indicators import library
from optimize.perf import gpu_batch
# reuse _ctx from the CPU parity test module
from optimize.perf.test_cold_accel_parity import _ctx

def test_gpu_batch_matches_cpu_for_each_combo():
    ctx = _ctx(); grid = [{"n": n, "k": 2.0} for n in (10, 20, 30)]  # example: bollinger
    out = gpu_batch.batch_directions("bollinger", ctx, grid)         # [3, 2, N]
    for i, p in enumerate(grid):
        ref_c, ref_v = library.build("bollinger", p).directions(ctx)
        assert np.array_equal(out[i, 0], ref_c) and np.array_equal(out[i, 1], ref_v)
```

- [ ] **Step 2: Run on the GPU box to verify it fails** — Expected: FAIL (`gpu_batch` not implemented).
- [ ] **Step 3: Implement `batch_directions`** — CuPy rolling kernels for the top-N; one host↔device
  transfer of the price arrays, param-combos as a batched axis; copy results back as int8. Any combo whose
  GPU result is not bit-identical to CPU is **rejected** and flagged (per Global Constraints).
- [ ] **Step 4: Run to verify PASS** on the GPU box.
- [ ] **Step 5: Benchmark** cold-miss throughput: CPU (Task 3) vs GPU (this task) across grid sizes
  {1, 16, 256, 4096} combos, **including** host↔device transfer; write `gpu_batch_bench.json`. Compute the
  break-even #combos where GPU overtakes CPU.
- [ ] **Step 6: Pull results + commit**

```bash
git add optimize/perf/gpu_batch.py optimize/perf/test_gpu_batch_parity.py optimize/perf/results/gpu_batch_bench.json
git commit -m "feat(perf): batched GPU indicator kernel + CPU-vs-GPU cold-miss benchmark (#54)"
```

---

## Task 6: Secondary — substrate & cache-level micro-benchmarks

**Files:**
- Create: `optimize/perf/bench_substrate.py`, `optimize/perf/bench_cache_level.py`

**Interfaces:**
- Consumes: a fixed set of real `directions()` arrays (dumped once from Task 2).
- Produces: `substrate_bench.json` (hit-latency per backend under N concurrent readers) +
  `cache_level_reuse.json` (distinct-array count: vote/mode key vs directions() key on a real sweep trace).

- [ ] **Step 1: `bench_substrate.py`** — store/load the fixed array set via `.npy` (current), `/dev/shm`
  tmpfs, `multiprocessing.shared_memory`, Redis (if available), Arrow/Plasma (if available), DuckDB; drive
  N=30 concurrent readers; record p50/p99 hit latency. Skip backends not installed (log the skip — no
  silent caps).
- [ ] **Step 2: `bench_cache_level.py`** — replay a real sweep's `(indicator, mode, params, tf)` request
  trace; count distinct arrays under (a) today's `(…, mode, params)` key vs (b) a `(…, params)` key shared
  across modes and the 6 TFs. Report the reuse multiplier.
- [ ] **Step 3: Run on server, pull results, commit**

```bash
git add optimize/perf/bench_substrate.py optimize/perf/bench_cache_level.py optimize/perf/results/substrate_bench.json optimize/perf/results/cache_level_reuse.json
git commit -m "perf: substrate + cache-level micro-benchmarks (#54)"
```

---

## Task 7: Report — decision matrix + GO/NO-GO

**Files:**
- Create: `optimize/REPORT_indicator_cache_acceleration.md`

**Interfaces:**
- Consumes: all `optimize/perf/results/*.json`, Task 0 prior-art notes.

- [ ] **Step 1: Write the report** — verbose, no-jargon, concrete numbers; **Mermaid-only** visuals
  (pipeline diagram, cold/warm/I-O split, CPU-vs-GPU break-even curve, decision matrix). Sections: the two
  reframing findings; prior art; baseline split; each lever's measured result vs the two dumb controls;
  "what went well / what went wrong"; GO/NO-GO per the pre-registered criterion; recommended follow-up
  issue(s) for adopting any winning lever.
- [ ] **Step 2: Verify every number** in the report against the JSON artifacts (no unverified claims).
- [ ] **Step 3: Commit + open PR** referencing #54

```bash
git add optimize/REPORT_indicator_cache_acceleration.md
git commit -m "docs(perf): indicator cache-acceleration report — findings + GO/NO-GO (#54)"
git push -u origin research/indicator-cache-acceleration
gh pr create --title "Research: indicator cold-miss acceleration (Numba + GPU) — findings" --body "Closes #54. ..." --base dev
```

---

## Self-Review

- **Spec coverage:** Q1 GPU → Tasks 4,5; Q2 Numba/recurrence → Task 3; Q3 substrate → Task 6; Q4 cache
  level → Task 6; instrumentation/baseline → Tasks 1,2; prior-art → Task 0; report/criterion → Task 7. All
  spec sections mapped.
- **Dumb controls:** enforced in Task 7's matrix (warm `.npy` + `+workers`), per criterion.
- **Parity gate:** Tasks 3 & 5 each end on the bit-identical gate; default flags OFF ⇒ production unchanged.
- **Dependency note:** Task 5's top-N selection consumes Task 2's ranking; Task 4 (GPU box) blocks Task 5
  but not 1–3/6 — CPU track + report ship even if GPU provisioning stalls (spec §4.4).
- **No local heavy compute:** every real run is server-side with a live log; only 3-trial smokes run locally.
