# Scaling Study — Dask vs Vectorization · MongoDB vs SQLite · Bottleneck-Prevention

**Date:** 2026-06-11
**Context:** Triggered by the `wsh4` sweep incident (see `INCIDENT_wsh4_sqlite_contention.md`) where a
single shared SQLite store under ~30 concurrent Optuna workers threw `database is locked`, killed
workers, and left 4h/1h under-sampled. This study evaluates two technology swaps the team raised, then
defines the essential improvements for scaling the system.

**One-line framing that governs the whole study:** *the bottleneck we hit was **write contention on the
results store**, not dataframe compute, not data size, and not memory.* Any improvement must be judged
against that fact first.

---

## 0. Measured baseline (what the system actually is)

| Dimension | Reality today | Source |
|-----------|---------------|--------|
| Largest dataframe | `NQ_1m.csv` = **28 MB, ~487k rows**; every other TF ≤ 14 MB | `ls -lh`, `wc -l` |
| Server RAM | **123 GB** (44 GB free, 70 GB cache at peak) | `free -g` |
| Compute kernel | `fast_engine.py` (135 LoC) — **numpy-vectorized**: sequential outer trade loop, exit resolution via `np.searchsorted` + `np.argmax` boolean scans | `optimize/fast_engine.py` |
| Parallelism model | **process-level**: ~30 independent `optimizer.py` workers (no threads sharing arrays) | `remote_wsi.sh` `WORKERS` |
| Results store | one **SQLite** file `wsh.db` = **158 MB**, all 6 studies + all 30 writers | `optimizer.py:67` |
| Per-trial cost | dominated by indicator compute on the 1-min frame, then a vectorized backtest; **~tens of ms–seconds**, not minutes | log cadence |
| Failure we hit | `sqlite3.OperationalError: database is locked` → worker death | run logs |

**Key inference:** data fits in RAM ~4000× over; the work is *millions of tiny, independent backtests*,
already farmed out by process. The scarce resource under stress was **the single writable SQLite file**.

---

## 1. Study — Dask (parallel dataframe) vs the current numpy vectorization

### What each is good at
- **numpy vectorization (current):** one process, arrays in RAM, tight C loops. Best when data fits in
  memory and the hot path is array math — exactly our case.
- **Dask:** (a) *out-of-core* compute on larger-than-RAM data by chunking; (b) a *parallel/distributed*
  task scheduler that can spread a dataframe/graph across many cores or many machines.

### Pros of adopting Dask here
- **Multi-node scale-out (future).** If we outgrow one box (many instruments × many TFs × tick data),
  Dask's `distributed` scheduler can spread work across a cluster with one API.
- **Out-of-core safety net.** If a future dataset (e.g. full tick history for dozens of symbols) exceeds
  RAM, Dask streams partitions instead of OOM-ing.
- **Unified dataframe API.** `dask.dataframe` mirrors pandas, so the data-prep scripts (`build_plus20d_data.py`,
  the merges/dedups) could in principle scale unchanged.

### Cons / why it does **not** fit the current system
- **Wrong bottleneck.** Dask parallelizes *dataframe compute*. Our stall was *DB writes*. Dask adds zero
  relief and would still deadlock on the same SQLite lock.
- **Negative ROI on tiny data.** 28 MB fits in L3-ish working sets; Dask's per-task scheduling overhead
  (~hundreds of µs–ms per task) **dominates** when the op itself is sub-second. Partitioning a 487k-row
  array into Dask chunks would run *slower* than the current numpy path.
- **Parallelism already solved, more cheaply.** We get linear scaling from 30 OS processes sharing
  nothing. Dask's value is coordinating *shared* big computations — we don't have one; we have many
  independent small ones. Optuna already distributes those.
- **Path-dependent kernel resists dataframe parallelism.** `fast_engine` walks trades sequentially
  (`while idx < n`, `blocked_until` carry) because entry/exit is order-dependent. That inner loop is not
  a vectorizable groupby Dask could accelerate; it's inherently sequential per trial.
- **Operational complexity.** Scheduler + workers + dashboard + serialization (pickling arrays between
  workers) is a lot of moving parts to debug for no current gain.

### If we ever *do* need scale-out, Dask is not the first choice
For distributed *hyperparameter search* specifically, **Ray Tune** or **Optuna + a shared RDB
(Postgres)** are a better fit than Dask, because the unit of distribution is "a trial" (a whole process),
not "a dataframe partition." Optuna already supports the RDB pattern — that's the natural growth path.

### Verdict (Study 1)
**Do not adopt Dask now.** Keep numpy vectorization + process-level parallelism; it is the correct tool
for in-RAM, embarrassingly-parallel, path-dependent backtests. Revisit a *distributed executor* (Ray
Tune first, Dask second) only when we (a) exceed one machine, or (b) hold a single dataset larger than
RAM. Where micro-optimization is wanted, **Numba `@njit` on the `fast_engine` trade loop** would beat
Dask for our shape, at a fraction of the complexity.

---

## 2. Study — MongoDB vs the current SQLite

### Critical correction up front
The SQLite in question is **Optuna's storage backend**, and **Optuna does not natively support MongoDB.**
Optuna's supported stores are: `InMemoryStorage`, `RDBStorage` (SQLAlchemy → **SQLite / PostgreSQL /
MySQL**), and `JournalStorage` (file or **Redis** backend). So "MongoDB instead of SQLite" is **not a
drop-in** for the optimizer — choosing it would mean either writing a custom storage (high risk, must
re-implement Optuna's transactional semantics) or abandoning Optuna's storage layer. The *supported* fix
for write-contention is **PostgreSQL** (or `JournalStorage`+Redis).

So the question splits into two honest sub-questions:

### 2a. As the optimizer's trial store
- **MongoDB pros:** document-level concurrency (WiredTiger) handles many writers far better than
  SQLite's single file lock; horizontal scaling; flexible nested documents (a trial is naturally a
  document).
- **MongoDB cons:** **unsupported by Optuna** (the dealbreaker); we'd lose Optuna's tested
  pruning/sampler↔storage contract; an extra server to run/secure/back-up; no SQL for ad-hoc analysis.
- **Better answer:** **PostgreSQL** solves the exact contention (true MVCC, concurrent writers, no global
  write lock) *and* is a first-class Optuna backend — drop-in via the storage URL. This is the
  contention fix, not Mongo.

### 2b. As the *system-wide* data layer (signals, results, run metadata, candles)
Today these are **CSV files + a SQLite Optuna db**. If the team wants a database here:
- **Where Mongo fits:** heterogeneous, schema-fluid **documents** — e.g. a "run manifest" (params +
  environment + dataset hash + arbitrary nested results), signal-bundle metadata, experiment catalogs.
  Mongo shines when records don't share a fixed columnar schema.
- **Where Mongo is the wrong tool:** our core data (candles, trades, signals, Pareto fronts) is
  **tabular/columnar time-series**. For that, columnar/relational stores beat a document DB on storage,
  scan speed, and analytics:
  - **Parquet + DuckDB** — zero-server, columnar, reads faster than CSV, SQL over files. Best low-friction
    upgrade for the analytical/tabular data.
  - **PostgreSQL / TimescaleDB** — if we want a real server, ACID, concurrent writers, and SQL; Timescale
    adds time-series partitioning for tick data.

### Pros / cons summary table

| Option | Concurrent writers | Optuna-native | Fit for tabular TS | Ops cost | Best role here |
|--------|:---:|:---:|:---:|:---:|----------------|
| SQLite (today) | ✗ single lock | ✓ | ok | none | small/local studies only |
| **PostgreSQL** | ✓✓ MVCC | ✓ | ✓ | medium | **optimizer store + system DB** |
| MongoDB | ✓✓ doc-level | ✗ | ✗ (columnar better) | medium-high | only schema-fluid docs/manifests |
| Parquet+DuckDB | n/a (files) | ✗ | ✓✓ | none | analytical results/candles |
| JournalStorage+Redis | ✓ | ✓ | n/a | medium | alt optimizer store |

### Verdict (Study 2)
**MongoDB is the wrong swap for the bottleneck.** The contention fix is **PostgreSQL** (Optuna-native,
true concurrent writers). For the broader data layer, prefer **Parquet+DuckDB** for tabular results/candles
and **Postgres/TimescaleDB** for a served time-series DB. Reserve MongoDB strictly for genuinely
document-shaped, schema-fluid metadata (run manifests/experiment catalogs) — and only if such a need
actually materializes.

---

## 3. Essential improvements to prevent these bottlenecks as the system expands

Prioritized; each maps to the failure mode it removes. **Tiers 0–1 are the must-do before the next big
sweep.**

### Tier 0 — Stop the exact failure (cheap, do first)
1. **Make storage failures non-fatal.** `study.optimize(..., catch=(StorageInternalError,))` so a lock
   blip fails one trial, never a worker. *(One line; alone would have saved 4h/1h.)*
2. **Harden the store:** WAL + `busy_timeout=60s` via `RDBStorage(engine_kwargs=...)`, or **per-TF DB
   files** to split the single lock ~6×. (Details in the incident report §4.A–C.)

### Tier 1 — Right-size the backend for concurrency
3. **Move the optimizer store to PostgreSQL** once worker counts stay ≥ ~10. It is the structural fix:
   MVCC removes write-lock contention entirely and is Optuna-native. Single env-var/URL change in
   `optimizer.py` + `report_wsi.py` + `remote_wsi.sh`.
4. **Decouple "store" from "compute" in config** so the storage URL is one switch (sqlite ↔ postgres)
   and the launcher/report/counts all read it from one place (today the `sqlite:///…wsh.db` literal is
   duplicated across three files — a refactor target).

### Tier 2 — Resilience & self-healing
5. **Worker watchdog/respawn** in `launch.sh`: re-spawn a worker that dies before the study hits its
   trial target, so transient faults self-heal instead of silently reducing capacity (the precise way
   4h/1h came up short).
6. **Idempotent, resumable runs** (already partly true via `load_if_exists`): always express a run as
   "reach N total trials," not "add N," so top-ups are exact and re-runnable.

### Tier 3 — Observability (so we see contention *live*, not in a post-mortem)
7. **Live counters in `status`:** completed / running / **FAILED** per study, plus trials/min. A failure
   storm should be visible within a minute, not discovered hours later by grepping logs.
8. **Structured run log + alert** on worker-count drop or rising FAIL rate.
9. **Pre-flight load test:** a short high-concurrency smoke (e.g. 30 workers × 50 trials) before
   committing a multi-hour sweep, to surface storage contention cheaply. (Complements the existing parity
   gate.)

### Tier 4 — Data layer for expansion (more instruments / TFs / history)
10. **CSV → Parquet** for candle/results data: faster load, smaller, columnar; keeps the in-RAM numpy
    path but cuts I/O as instrument count grows.
11. **A small dataset registry** (path + hash + provenance) so every run records exactly which immutable
    dataset it used — reproducibility as the matrix of instruments × windows grows.
12. **Capacity formula, documented:** `workers ≈ cores − 2`, and `max writers per SQLite file ≈ small`;
    with Postgres the writer cap effectively lifts. Encode it where `WORKERS` is defined.

### Tier 5 — Orchestration (only if we go multi-node)
13. If one box is outgrown: **Ray Tune** or **Optuna + Postgres across nodes** for distributed trials
    (preferred over Dask for trial-shaped parallelism). A job queue (Redis/RQ) to schedule
    instrument×TF×window sweeps.

### What we explicitly do **not** need yet
- Dask (Study 1) — wrong bottleneck, negative ROI on in-RAM data.
- MongoDB (Study 2) — unsupported by Optuna; columnar/relational beats it for our tabular data.
- A microservice/cluster rewrite — single box + Postgres + the resilience tiers covers the foreseeable
  expansion.

---

## 4. Bottom line

| Question | Answer |
|----------|--------|
| Dask vs vectorization? | **Keep vectorization** (+ optional Numba). Dask only if multi-node or >RAM data — and even then Ray Tune fits better. |
| MongoDB vs SQLite? | **Neither as posed — go PostgreSQL** for the optimizer store (Optuna-native, concurrent). Parquet+DuckDB for tabular results. Mongo only for schema-fluid docs. |
| Essential improvements? | Tier 0–1 now (catch + WAL/per-TF, then Postgres + single storage switch); Tier 2–3 next (watchdog, live FAIL metrics); Tier 4 as instruments grow (Parquet + dataset registry). |

The cause was never the math or the data volume — it was **one writable file behind thirty writers**.
Fix the store and add resilience, and the current vectorized/multiprocess design scales cleanly with the
expansion.
