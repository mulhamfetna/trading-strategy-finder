# Prior Art — Indicator Caching & GPU Technical Analysis

**Date:** 2026-07-27 · **Issue:** #54 · Feeds `REPORT_indicator_cache_acceleration.md`.
Online pass answering: *has someone already solved "compute parameterized indicators once, reuse across a
sweep", and does GPU help?* Each entry: what they do → the one idea transferable to **our** system (where
`ind.directions()` is a pure function of `(indicator, params, price series)`).

---

## 1. vectorbt / vectorbt PRO — batch params as array columns + dedup + shared sub-compute
- **What:** `IndicatorFactory` broadcasts *many parameter combinations into extra columns of one 2-D array*
  and runs the indicator over all of them in a single vectorized (optionally jitted/multithreaded) pass.
  `run_unique=True` **deduplicates repeated param combinations**; `cache_func` + `cached_property/method`
  share intermediate results (e.g. a base EMA reused by BBANDS) across combos.
- **Transferable idea:** this is the CPU analogue of our GPU-batch lever — compute a *whole param grid of
  one indicator at once* rather than one array per cold miss. Their `run_unique` is exactly our cache's
  dedup, but applied *within a single vectorized call*. Validates batching the top-N vectorizable
  oscillators (Task 5) and suggests a **CPU batched path** as the "dumb control" the GPU must beat.
- Sources: [DeepWiki](https://deepwiki.com/polakowo/vectorbt), [factory](https://vectorbt.dev/api/indicators/factory/), [PRO Indicators](https://vectorbt.pro/features/indicators/), [PRO Performance](https://vectorbt.pro/features/performance/).

## 2. talipp / wickra — incremental (O(1)/tick) wins for *streaming*, loses to C batch for *one-shot*
- **What:** `talipp` computes indicators incrementally — O(1) per new tick vs O(n) recompute — ideal for
  live/iterative input; it beats TA-Lib when you *append* data. **But for a one-shot full-history batch,
  TA-Lib (C, vectorized) is "a clear winner."** `wickra` is a Rust-core, 514-indicator, O(1)-per-tick,
  drop-in TA-Lib replacement with Python bindings.
- **Transferable idea:** our optimizer cold miss is a **batch** (compute the full 486,970-bar history once
  per new param), *not* a streaming append — so the incremental route is the wrong tool for the cold miss;
  vectorized/C/GPU is right. This corroborates our own `RESEARCH_indicator_recurrence_relations.md` and
  narrows Task 3 to the *exact* recurrences (EMA-family `lfilter`, deque max/min) rather than a general
  streaming rewrite. `wickra` is worth noting as a prebuilt option **iff** it reproduces our vote math
  bit-identically (unlikely without porting — parity risk).
- Sources: [talipp](https://github.com/nardew/talipp), [talipp PyPI](https://pypi.org/project/talipp/), [wickra](https://github.com/wickra-lib/wickra).

## 3. Qlib — two-level (LRU memory + disk) expression cache with sub-expression reuse
- **What:** Qlib parses each feature expression into a syntax tree and caches **every node's** result in an
  in-memory LRU plus a `DiskExpressionCache`; a repeated (sub-)expression loads from cache instead of
  recomputing. Disk cache on by default.
- **Transferable idea:** exactly mirrors our `_VOTE_MEMO` (memory) + `vote_cache` (disk) two-level design —
  independent industrial validation that our architecture is the standard answer. The *new* idea is
  **sub-expression** caching: several of our indicators share a base EMA/ATR (MACD, Keltner, ADX). Caching
  at the shared-primitive level (below `directions()`) could cut cold-miss cost further — a candidate for
  the Task 6 cache-level analysis and a possible follow-up.
- Sources: [Qlib data layer](https://qlib.readthedocs.io/en/stable/component/data.html), [Qlib paper](https://arxiv.org/pdf/2009.11189).

## 4. RAPIDS cuDF / CuPy + Numba-CUDA — GPU batch is real, but only for the right shape
- **What:** cuDF (~40× pandas on DataFrame-heavy pipelines), CuPy (NumPy-API GPU arrays), and Numba-CUDA
  (NVIDIA reports >100× on *batched* Monte-Carlo trading simulations) all push array math to the GPU.
  Repeated theme: **"batching thousands of scenarios on the GPU reduces minutes to seconds."**
- **Transferable idea:** the GPU win is *throughput across many parallel scenarios*, not latency on one —
  which is precisely our Task 5 framing (many param-combos of one indicator per kernel), **not** the tiny
  28 MB data volume the 2026-06-11 scaling study correctly said GPU can't help. Caveat from the same
  sources: cuDF's big wins are DataFrame ops (joins/groupby); our per-bar rolling arithmetic maps to
  **CuPy / custom CUDA kernels**, and the host↔device transfer + kernel-launch overhead sets a break-even
  #combos below which CPU wins — exactly what Task 5 measures.
- Sources: [RAPIDS cuDF](https://developer.nvidia.com/blog/accelerated-data-analytics-speed-up-data-exploration-with-rapids-cudf/), [Numba 100× trading](https://developer.nvidia.com/blog/gpu-accelerate-algorithmic-trading-simulations-by-over-100x-with-numba/), [RAPIDS for trading](https://blog.quantinsti.com/nvidia-gpu-rapids-libraries-trading/), [cuDF+CuPy interop](https://medium.com/rapids-ai/10-minutes-to-cudf-and-cupy-e131cac0439b).

## 5. Cache substrate — shared-memory options for cross-process array reuse
- **What:** Arrow **Plasma** offered zero-copy immutable objects in shared memory across processes
  (originated in Ray). **Caveat (verify, don't assume): Plasma was deprecated and removed from Apache Arrow
  in later releases (~Arrow 12)** — it is *not* a safe new dependency in 2026. The durable options are
  `/dev/shm` tmpfs (RAM-backed files, no serialization change from `.npy`), Python
  `multiprocessing.shared_memory` (zero-copy numpy views across processes), Redis (network/socket hop +
  (de)serialization, but battle-tested cross-host), and memory-mapped files.
- **Transferable idea:** our current disk `.npy` under `/tmp` may already be on tmpfs or page-cache-hot
  (123 GB RAM box) — so the *first* substrate question is empirical: is the `.npy` open/parse the cost, or
  is it already RAM-speed? Task 6 measures `.npy` vs `/dev/shm` vs `shared_memory` vs Redis under 30
  readers; **skip Plasma** (deprecated) and only include Redis if already installed (no silent caps).
- Sources: [Plasma announcement](https://arrow.apache.org/blog/2017/08/08/plasma-in-memory-object-store/), [Arrow zero-copy cluster shared memory (2024)](https://arxiv.org/html/2404.03030v1).

---

## Synthesis → how prior art shapes each lever

| Our lever (issue #54) | Prior-art verdict | Consequence for the PoC |
|-----------------------|-------------------|-------------------------|
| **Cold-miss compute (priority)** | vectorbt batches param-grids into columns; GPU gives 100× only on batched scenarios; incremental is wrong for one-shot batch | Task 5 GPU-batches the top-N oscillators; add a **CPU-batched** path as a dumb control the GPU must beat; keep Task 3 to the *exact* EMA/deque recurrences |
| **Cache substrate** | Qlib validates 2-level memo+disk; Plasma deprecated; tmpfs/`shared_memory` are the live options | Task 6 measures `.npy` vs tmpfs vs `shared_memory` vs Redis; drop Plasma; question is empirical (is `.npy` already RAM-hot?) |
| **Cache level** | Qlib caches *sub-expressions*, not just top-level features | Task 6 counts reuse for a `directions()` key; flag shared-primitive (EMA/ATR) caching as a follow-up |
| **Do nothing / prebuilt** | `wickra` (Rust, drop-in TA-Lib) exists | Note as an option, but parity risk is high — our vote math must reproduce bit-identically |

**Bottom line from prior art:** our two-level cache is the industry-standard design (Qlib), the GPU angle
is legitimate *only* as batched-param throughput (RAPIDS/Numba), the cold miss should be attacked with
vectorized/GPU batch rather than incremental streaming (talipp/TA-Lib), and the substrate benchmark should
skip the deprecated Plasma and test tmpfs/`shared_memory`/Redis against a possibly-already-RAM-hot `.npy`.
