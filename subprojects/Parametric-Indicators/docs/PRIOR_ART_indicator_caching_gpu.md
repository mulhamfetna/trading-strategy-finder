# Prior Art — Indicator Caching & GPU Technical Analysis

**Date:** 2026-07-27 · **Issue:** #54 · Feeds `REPORT_indicator_cache_acceleration.md`.
Online pass answering: *has someone already solved "compute parameterized indicators once, reuse across a
sweep", and does GPU help?* This is the **deep** pass — full pages + GitHub source fetched, real numbers
quoted, and the deprecated-Plasma claim verified against source. Each entry: what they do → the one idea
transferable to **our** system (where `ind.directions()` is a pure fn of `(indicator, params, series)`).

> **Verification note (honest sourcing).** Numbers below are quoted from the *fetched pages*. Where the
> first (search-only) pass over-attributed a feature to the wrong page, it is corrected inline. Hard
> decision-grade numbers for us still come from our own server + GPU benchmarks (Tasks 2/5), not blogs.

---

## 1. vectorbt / vectorbt PRO — batch params as array columns, chunked cache, Numba
- **What (verified timings, `vectorbt.pro/features/performance`):** rolling mean **Pandas 45.6 ms →
  Numba 5.33 ms → Numba+parallel 1.82 ms** (~25×); rolling Sortino **QuantStats 2.79 s → VBT 8.12 ms
  (~343×)**; random-portfolio threadpool ~2×. Parameter sweeps run through `@vbt.chunked(chunk_len=100)`
  — "at most 100 parameter combinations at once" — with `clear_cache=True` + `collect_garbage=True`
  between chunks, and a central cache registry reporting hits/misses/MB per property (e.g. `filled_close`
  6 hits / 1 miss).
- **Correction to the first pass:** `run_unique` (dedup of repeated param combos) and `cache_func` are real
  vectorbt features but come from the **DeepWiki** overview, *not* the performance page — re-sourced below.
- **Transferable idea:** batching a *whole param grid of one indicator into columns and computing in one
  vectorized/Numba pass* is the CPU analogue of our GPU-batch lever, and the **chunked** pattern
  (bounded combos per pass + explicit cache clearing) is exactly how to keep our batch memory-bounded
  against the 4B-combo wall. This is the **CPU-batched dumb control** the GPU must beat (Task 5).
- Sources: [PRO Performance](https://vectorbt.pro/features/performance/), [DeepWiki](https://deepwiki.com/polakowo/vectorbt) (run_unique/cache_func), [factory](https://vectorbt.dev/api/indicators/factory/).

## 2. talipp / wickra — incremental wins *streaming*, ties C for *batch* (our cold miss is batch)
- **talipp (verified, GitHub):** SMA(20) over 50k values — **batch ~200 ms ≈ TA-Lib ~200 ms**, but
  **incremental 200 ms vs TA-Lib 6,800 ms (~34×)**; O(1)/update vs O(n) recompute; ~50+ indicators;
  **does not state numerical parity with TA-Lib**. Explicit: for one-shot batch, "talib is a clear winner"
  (C, vectorized).
- **wickra (verified, GitHub):** 514 indicators, Rust core, O(1)/tick, drop-in TA-Lib, **zero deps** (not
  even numpy), `array.array('d')` zero-copy to numpy; streaming 11–56× vs the other incremental peer;
  **bit-for-bit batch==streaming across all 514 indicators**, golden fixtures replayed across 10 bindings.
- **Transferable idea:** our optimizer cold miss is a **full-history batch** (compute 486,970 bars once per
  new param), *not* a streaming append — so the incremental route buys nothing on the cold miss;
  vectorized C/GPU is the ceiling. This narrows Task 3 to the *exact* recurrences (EMA-family `lfilter`,
  deque max/min) rather than a general streaming rewrite. wickra's bit-for-bit batch/stream is an
  engineering signal, but its parity is with **TA-Lib conventions, not our vote math** → adopting it would
  still require our bit-identical gate (high risk; note only).
- Sources: [talipp](https://github.com/nardew/talipp), [wickra](https://github.com/wickra-lib/wickra).

## 3. Qlib — two-level (LRU memory + hash-keyed disk) cache, sub-expression reuse
- **What (verified, readthedocs):** a global `MemCache` (Calendar/Instruments/**Features**), size-bounded
  by `mem_cache_size_limit`/`limit_type`; `DiskExpressionCache` persists expression results (e.g.
  `Mean($close,5)`) to disk under **hash-based names `hash(instrument, field_expression, freq)`**;
  `DatasetCache` (`disk_cache=1` **default**) with `.meta`/`.index` tracking config + visit frequency;
  server uses `redis_lock` to guard read/write conflicts.
- **Transferable idea:** independent industrial confirmation that our `_VOTE_MEMO` (memory) + `vote_cache`
  (sha256-keyed disk `.npy`) two-level design **is** the standard answer — Qlib's `hash(instrument, field,
  freq)` maps 1:1 onto our `disk_key(version, slice_sig, use1, key, mode, params)`. The *new* idea is
  caching **sub-expressions** (Qlib caches every syntax-tree node): several of our indicators share a base
  EMA/ATR (MACD, Keltner, ADX) — caching that shared primitive *below* `directions()` could cut cold-miss
  cost further (Task 6 cache-level note + a possible follow-up). Qlib's `redis_lock` also foreshadows our
  Postgres-store contention lesson.
- Sources: [Qlib data layer](https://qlib.readthedocs.io/en/stable/component/data.html), [Qlib paper](https://arxiv.org/pdf/2009.11189).

## 4. RAPIDS cuDF / CuPy + Numba-CUDA — GPU batch is real, and its shape is exactly ours
- **What (verified, NVIDIA H200 blog):** Monte-Carlo order-book sim — **14× (1 trading day) → 38× (5 days)
  → 114× (1 month)** vs CPU. The speedup *grew with the time horizon* because the **time dimension stayed
  sequential** while the **`Nsims = 1,000` parallel paths** saturated 14,000+ CUDA cores; `@cuda.jit`
  kernels, random variates pre-batched to device via `cuda.to_device()` to avoid per-call overhead.
  Separately, cuDF ≈ 40× pandas on DataFrame-heavy pipelines.
- **Transferable idea (strong):** this is a near-perfect analogue of our cold miss. Our **serial dimension
  is the price time-series** (per-bar recurrence, can't parallelize within one array); our **parallel
  dimension is the param-combos** (thousands of independent parameterizations of one indicator). Batch
  many combos per kernel and the GPU should show the same "parallel-axis" win — *provided* the per-combo
  arithmetic amortizes the host↔device transfer (the break-even #combos Task 5 measures). cuDF's DataFrame
  wins don't apply (our per-bar rolling math → **CuPy / custom CUDA kernels**), and the 2026-06-11 scaling
  study's "GPU can't help the tiny 28 MB data" verdict is *not* contradicted — this is a *throughput*
  win across combos, a different axis than data volume.
- Sources: [Numba 114× trading (H200)](https://developer.nvidia.com/blog/gpu-accelerate-algorithmic-trading-simulations-by-over-100x-with-numba/), [RAPIDS cuDF](https://developer.nvidia.com/blog/accelerated-data-analytics-speed-up-data-exploration-with-rapids-cudf/), [cuDF+CuPy interop](https://medium.com/rapids-ai/10-minutes-to-cudf-and-cupy-e131cac0439b).

## 5. Cache substrate — shared-memory options (Plasma is dead; verified)
- **What (verified against source):** Arrow **Plasma** (zero-copy immutable shared-memory objects, from
  Ray) is **deprecated since Arrow 10.0.0 and REMOVED in Arrow 12.0.0** (2023-05-02, GH-33243); the
  project's own migration guidance is pyarrow **IPC** or stdlib **pickle**. So Plasma is *not* a valid new
  dependency in 2026. The durable options: `/dev/shm` tmpfs (RAM-backed files — same `.npy` code path,
  zero serialization change), Python `multiprocessing.shared_memory` (zero-copy numpy views across
  processes), Redis (socket hop + (de)serialization, but battle-tested cross-host), and mmap'd files.
- **Transferable idea:** our current disk `.npy` under `/tmp` on a 123 GB box is very likely already
  page-cache-hot (RAM-speed reads) — so the *first* substrate question is empirical: is the `.npy`
  open/parse the cost, or is it already RAM-speed? Task 6 measures `.npy` vs `/dev/shm` vs
  `shared_memory` vs Redis under 30 readers; **skip Plasma** (removed) and include Redis only if already
  installed (log the skip — no silent caps).
- Sources: [Plasma removed in 12.0.0 (GH-33243)](https://github.com/apache/arrow/issues/33243), [Plasma deprecated (GH-34738)](https://github.com/apache/arrow/issues/34738), [Arrow 12.0.0 release](https://arrow.apache.org/blog/2023/05/02/12.0.0-release/).

---

## Synthesis → how prior art shapes each lever

| Our lever (issue #54) | Prior-art verdict (with numbers) | Consequence for the PoC |
|-----------------------|----------------------------------|-------------------------|
| **Cold-miss compute (priority)** | vectorbt Numba rolling-mean 45.6→1.82 ms (~25×); GPU H200 114× *because* the parallel axis (1000 paths) saturates cores while time stays serial; incremental ties C for batch | Task 5 GPU-batches top-N oscillators along the **param-combo axis**; add a **CPU-batched (Numba/chunked)** dumb control the GPU must beat; Task 3 stays on the exact EMA/deque recurrences |
| **Cache substrate** | Qlib validates 2-level memo+hash-disk cache; **Plasma removed (Arrow 12.0.0)**; tmpfs/`shared_memory`/Redis are the live options | Task 6 measures `.npy` vs tmpfs vs `shared_memory` vs Redis; **drop Plasma**; question is empirical (is `.npy` already RAM-hot on the 123 GB box?) |
| **Cache level** | Qlib caches *every sub-expression* node, not just top-level features | Task 6 counts reuse for a `directions()` key; flag shared-primitive (EMA/ATR) sub-caching as a follow-up |
| **Do nothing / prebuilt** | wickra (Rust, 514 indicators, bit-for-bit batch/stream) exists but matches **TA-Lib**, not our votes | Note as an option; parity with our vote math is unproven → high adoption risk |

**Bottom line from prior art:** our two-level cache is the industry-standard design (Qlib, to the hash-key
detail); the GPU angle is legitimate specifically as **batched-param throughput** and the published H200
114× is the *same parallel-axis mechanism* we'd exploit; the cold miss must be attacked with
vectorized/GPU batch rather than incremental streaming (talipp/TA-Lib prove incremental ties C only for
batch); and the substrate benchmark should **skip the removed Plasma** and test tmpfs/`shared_memory`/Redis
against a `.npy` cache that may already be RAM-hot.
