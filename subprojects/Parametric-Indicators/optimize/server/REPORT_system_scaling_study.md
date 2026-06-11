# System Scaling Study — Detailed Report
### Dask vs Vectorization · MongoDB vs SQLite · Bottleneck-Prevention Roadmap

**Author:** engineering analysis
**Date:** 2026-06-11
**Trigger:** `wsh4` 1-minute-indicator NSGA-III sweep degraded — a single shared SQLite store under ~30
concurrent Optuna workers raised `database is locked`, killed workers, and left the **4h** and **1h**
studies under-sampled (2,146 / 2,653 trials vs a 5,000 target). See
`INCIDENT_wsh4_sqlite_contention.md` for the post-mortem this report builds on.
**Companion (condensed):** `STUDY_scaling_dask_mongo_bottlenecks.md`.
**Scope of this document:** evaluate two proposed technology swaps and define the essential
infrastructure improvements needed as the system expands (more instruments × timeframes × windows ×
trials). **Analysis only — no production code is changed by this report.**

---

## Table of contents
1. Executive summary
2. Measured baseline — what the system actually is
3. The bottleneck, precisely
4. Study 1 — Dask (parallel dataframe) vs numpy vectorization
5. Study 2 — MongoDB vs SQLite (and the real alternative: PostgreSQL)
6. Study 3 — Essential improvements & phased roadmap
7. Decision matrices
8. Migration playbooks (concrete code)
9. Risk register
10. Appendix — evidence & references

---

## 1. Executive summary

| Question | Verdict | Why (one line) |
|----------|---------|----------------|
| **Dask vs vectorization?** | **Keep vectorization** (+ optional Numba on the trade loop) | The stall was DB writes, not dataframe compute; data is 28 MB on a 123 GB box; trials are already parallel across processes. |
| **MongoDB vs SQLite?** | **Neither as posed → adopt PostgreSQL** for the optimizer store; Parquet+DuckDB for tabular results | Optuna does **not** support MongoDB; Postgres is Optuna-native and removes write-lock contention via MVCC. |
| **Essential improvements?** | **Tiered roadmap** (Tier 0 hardening → Tier 1 Postgres → Tier 2 resilience → Tier 3 observability → Tier 4 data layer) | The design is sound; it failed only at the *results store*. Fix the store, add resilience and visibility. |

**The single most important sentence in this report:** the incident was caused by *one writable file
behind thirty writers* — not by the math, the data volume, or the memory. Every recommendation is judged
against that fact, which is why two "bigger hammer" technologies (Dask, MongoDB) are **not** the answer
and a targeted store change (PostgreSQL) **is**.

**Minimum action before the next large sweep (half a day of work):** add `catch=` to `study.optimize`,
enable WAL + `busy_timeout`, and split to per-timeframe DB files. That trio alone would have prevented
the incident. PostgreSQL is the durable follow-up once worker counts stay high.

---

## 2. Measured baseline — what the system actually is

All figures measured on 2026-06-11 from the repo and the AMD server.

### 2.1 Data volumes (the "dataframe" workload)

| File | Size | Rows | Role |
|------|-----:|-----:|------|
| `NQ_1m.csv` | **28 MB** | **486,970** | shared 1-minute exit-resolution + 1-min indicator frame |
| `NQ_2m.csv` | 14 MB | — | decision frame (finest swept) |
| `NQ_5m.csv` | 5.6 MB | — | decision frame |
| `NQ_15m.csv` | 1.9 MB | — | decision frame |
| `NQ_1h.csv` | 479 KB | — | decision frame |
| `NQ_2h.csv` | 252 KB | — | decision frame |
| `NQ_4h.csv` | 127 KB | — | decision frame |
| `wsh.db` (SQLite) | **158 MB** | ~25k trials | Optuna results store (all 6 studies, all writers) |

**Server:** 123 GB RAM (44 GB free, 70 GB page-cache at peak), 937 GB disk (13% used), CPU-only.
**Implication:** the entire working set fits in RAM ~4,000× over. There is **no out-of-core problem and
no memory pressure.**

### 2.2 Compute kernel

`optimize/fast_engine.py` (135 LoC) — numpy-vectorized backtest, parity-locked to the reference
`engine.SimpleStrategy`:
- Outer loop over trades is **sequential** (`while idx < n`, carries `blocked_until`) because entry/exit
  is path-dependent — a trade's start depends on the prior trade's exit.
- Inner exit resolution is **vectorized**: `np.searchsorted` to find the first 1-minute bar at/after
  entry, `np.argmax` boolean scans to find the first SL/TP touch.
- Indicator computation (the per-trial cost driver) runs on the 1-minute frame
  (`indicators/runner.py`, 249 LoC).

### 2.3 Parallelism model

Process-level, shared-nothing: `remote_wsi.sh` launches ~30 independent `optimizer.py` workers:

```bash
declare -A WORKERS=( [2m]=6 [5m]=6 [15m]=5 [1h]=5 [2h]=4 [4h]=4 )   # sum ≈ 30
```

Each worker runs its own Python process, holds its own copy of the arrays, and coordinates **only**
through the shared Optuna SQLite store (trial suggestions + results). This is textbook
embarrassingly-parallel hyperparameter search.

### 2.4 The three places the storage path is hard-coded (a refactor target)

```
optimize/optimizer.py:67        _DB = _STUDIES / "wsh.db"          # writer
optimize/report_wsi.py:34,76    _DB = .../"wsh.db" ; load_study(... sqlite:///{_DB})   # reader
optimize/server/remote_wsi.sh   create_study(... 'sqlite:///optimize/studies/wsh.db' ...)  # launcher + counts
```

Any backend change must update all three in lockstep — which is itself an argument for centralizing the
storage URL behind one config value/env var.

---

## 3. The bottleneck, precisely

**Mechanism:** SQLite permits exactly one writer at a time and guards the database file with a global
lock. Optuna commits trial state frequently (suggest → running → complete). With ~30 workers committing
every few seconds against one file, lock-wait exceeded SQLite's default ~5 s `busy_timeout`, raising
`sqlite3.OperationalError: database is locked`. Optuna wraps this as `StorageInternalError`; because
`study.optimize()` was called **without `catch=`**, the exception propagated and **terminated the worker
process**.

**Why 4h/1h specifically:** the failures clustered in a contention storm at ~01:00. Studies whose
workers survived it reached target (5m: 5,004; 2h: 5,000); studies that lost workers early ran short
(4h: 2,146; 1h: 2,653). The deficit is **lost worker-hours**, not a logic error.

**Explicitly ruled out:** OOM (44 GB free, no dmesg OOM), disk (13% used), code/logic (tracebacks
terminate inside `sqlalchemy`/`sqlite3`, never in engine/indicator code).

**This is a documented Optuna limitation:** the project advises against SQLite for distributed studies
with many workers and recommends an RDB (PostgreSQL/MySQL) for that case.

---

## 4. Study 1 — Dask vs the current numpy vectorization

### 4.1 What each technology is for

- **numpy vectorization (current):** single process, arrays resident in RAM, tight C-level array ops.
  Optimal when data fits in memory and the hot path is array arithmetic.
- **Dask:** two distinct value propositions — (a) **out-of-core** computation on larger-than-RAM data via
  chunked partitions; (b) a **parallel/distributed scheduler** that spreads a task graph (incl.
  `dask.dataframe`) across many cores or many machines.

### 4.2 Pros of adopting Dask **in this system**

| Pro | Realized today? | Notes |
|-----|:---:|-------|
| Multi-node scale-out | ✗ (single box) | Real value only once we exceed one machine. |
| Out-of-core for >RAM data | ✗ (28 MB ≪ 123 GB) | Becomes relevant only with full tick history × many symbols. |
| pandas-compatible API for data-prep | ~ | The merge/dedup scripts *could* port, but they're trivially small. |

### 4.3 Cons / why Dask does not fit now

1. **It targets the wrong bottleneck.** Dask parallelizes compute; our stall was the **results store**.
   Dask workers would deadlock on the identical SQLite lock — zero relief.
2. **Negative ROI on small data.** Dask's per-task scheduling overhead (~hundreds of µs–ms) dominates
   when the underlying op is sub-second. Partitioning a 487k-row array would run **slower** than the
   current single-process numpy path.
3. **Parallelism is already solved — more cheaply.** 30 shared-nothing OS processes give near-linear
   scaling without serialization. Dask shines at coordinating *one big shared* computation; we have
   *many small independent* ones, already farmed out by Optuna.
4. **The kernel is path-dependent.** `fast_engine`'s sequential trade loop (order-dependent entries via
   `blocked_until`) is not a vectorizable groupby/reduction Dask could accelerate. The expensive part is
   inherently sequential *per trial*.
5. **Operational complexity.** Scheduler + workers + dashboard + inter-worker array pickling is
   significant surface area to debug for no current gain.

### 4.4 If we ever do need scale-out

For distributed **hyperparameter search**, the unit of distribution is "a trial" (a whole process), not
"a dataframe partition." Better fits than Dask, in order:
1. **Optuna + PostgreSQL across nodes** — we already use Optuna; only the storage URL changes. Lowest
   migration cost.
2. **Ray Tune** — purpose-built distributed HPO with Optuna sampler support; good if we want managed
   fault-tolerance and scheduling.
3. **Dask** — last, and mainly if a genuine out-of-core dataframe problem appears.

### 4.5 Cheaper local speedup than Dask

If single-trial latency ever needs cutting, **Numba `@njit`** on the `fast_engine` trade loop typically
yields 5–50× on tight numeric loops, keeps everything in-process, and adds one decorator — far less
complexity than Dask and aimed at the actual hot path.

### 4.6 Verdict
**Do not adopt Dask now.** Keep numpy vectorization + process-level parallelism. Reconsider a distributed
executor (Ray Tune first, then Optuna+Postgres multi-node, Dask last) only when we exceed one machine or
hold a dataset larger than RAM. For raw per-trial speed, prefer Numba over Dask.

---

## 5. Study 2 — MongoDB vs SQLite

### 5.1 The decisive constraint

The SQLite under discussion is **Optuna's storage backend**. Optuna's supported stores are:

- `InMemoryStorage` (no persistence),
- `RDBStorage` via SQLAlchemy → **SQLite / PostgreSQL / MySQL**,
- `JournalStorage` → file or **Redis** backend,
- `GrpcStorageProxy` (fronting one of the above).

**MongoDB is not a supported Optuna backend.** Choosing it for the optimizer would mean writing and
maintaining a custom storage that re-implements Optuna's transactional/locking contract — high risk, high
maintenance, and easy to get subtly wrong (the sampler↔storage interaction governs correctness of
pruning and multi-objective fronts). This effectively rules MongoDB out **for the optimizer store**.

The question therefore splits in two.

### 5.2a As the optimizer's trial store

| | SQLite (today) | **PostgreSQL** | MongoDB |
|---|---|---|---|
| Concurrent writers | ✗ single global lock | ✓✓ MVCC, true concurrency | ✓✓ doc-level (WiredTiger) |
| Optuna-native | ✓ | ✓ (drop-in URL) | ✗ **unsupported** |
| Fixes our contention | partially (WAL/timeout) | ✓ completely | n/a (can't use) |
| Ops cost | none | medium (one server) | medium-high |
| SQL for ad-hoc analysis | ✓ | ✓ | ✗ |

→ **PostgreSQL** is the correct upgrade: it removes the exact failure (concurrent writers under MVCC,
no global write lock) and is a first-class Optuna backend reachable by changing the storage URL.

### 5.2b As the system-wide data layer (candles, signals, results, run metadata)

Today: **CSV files** + the SQLite Optuna store. If we want a database here, match the store to the data
shape:

- **Tabular/columnar time-series** (candles, trades, signals, Pareto fronts) — the bulk of our data:
  - **Parquet + DuckDB** — zero-server, columnar, compresses well, reads faster than CSV, full SQL over
    files. **Best low-friction upgrade** for analytical/tabular data; keeps the in-RAM numpy path.
  - **PostgreSQL / TimescaleDB** — if a served DB is wanted: ACID, concurrent writers, SQL; Timescale
    adds time-series partitioning/compression for tick data.
- **Schema-fluid documents** (run manifests: params + env + dataset hash + arbitrary nested results;
  experiment catalogs): **MongoDB is a reasonable fit here** — flexible nested documents with no fixed
  columnar schema. This is the *only* niche where Mongo is the right tool in this system, and only if
  such a need actually materializes.

### 5.3 Why Mongo is the wrong default for our core data

Our core data is fixed-schema, numeric, time-ordered, and queried with range scans/aggregations —
exactly what columnar/relational engines optimize and what document stores handle comparatively poorly
(larger on disk, slower scans, no SQL for analysts). Adopting Mongo for it would add an operational
dependency while *losing* analytical ergonomics.

### 5.4 Verdict
**MongoDB is the wrong swap for the bottleneck.** Adopt **PostgreSQL** for the optimizer store
(Optuna-native, concurrent). For the broader data layer, prefer **Parquet+DuckDB** for tabular
results/candles and **Postgres/TimescaleDB** for a served time-series DB. Keep MongoDB on the table only
for genuinely document-shaped, schema-fluid metadata.

---

## 6. Study 3 — Essential improvements & phased roadmap

Prioritized by leverage and sequenced so each tier is independently shippable. **Tiers 0–1 are the
must-do before the next large sweep.**

### Tier 0 — Stop the exact failure (≈0.5 day, no new infra)
- **0.1 Non-fatal storage errors:** `study.optimize(..., catch=(optuna.exceptions.StorageInternalError,))`.
  A lock blip then fails one trial, never a worker. *Alone would have prevented the incident.*
- **0.2 Harden SQLite:** WAL journal + `busy_timeout=60s` via `RDBStorage(engine_kwargs=...)`.
- **0.3 Per-timeframe DB files** (`wsh_<tf>.db`): splits the single lock ~6× (≈5 writers/file). Update
  the reader (`report_wsi.py`) and launcher/counts (`remote_wsi.sh`) to match.

**Acceptance:** a 30-worker × 50-trial smoke produces **zero** `database is locked` worker deaths.

### Tier 1 — Right-size the backend (≈1–2 days)
- **1.1 PostgreSQL optimizer store** once worker counts stay ≥ ~10. Structural fix: MVCC eliminates
  write-lock contention; Optuna-native.
- **1.2 Centralize the storage URL** behind one env var/config read so `optimizer.py`,
  `report_wsi.py`, and `remote_wsi.sh` share a single source of truth (sqlite ↔ postgres = one switch).

**Acceptance:** full 6-TF × 5,000-trial sweep completes with all studies at target; no worker attrition.

### Tier 2 — Resilience & self-healing (≈1 day)
- **2.1 Worker watchdog/respawn** in `launch.sh`: respawn a worker that dies before its study hits the
  trial target (prevents silent capacity loss — the precise way 4h/1h fell short).
- **2.2 Target-based, idempotent runs:** express a run as "reach N **total** trials," not "add N," so
  top-ups are exact and re-runnable.

**Acceptance:** killing a worker mid-run leaves the final trial count unchanged (auto-respawn covers it).

### Tier 3 — Observability (≈1 day)
- **3.1 Live counters in `status`:** completed / running / **FAILED** per study + trials/min. A
  contention storm becomes visible within a minute, not hours later via log grep.
- **3.2 Structured run log + alert** on worker-count drop or rising FAIL rate.
- **3.3 Pre-flight contention smoke test:** short high-concurrency probe before any multi-hour sweep
  (complements the existing parity gate).

**Acceptance:** an injected failure storm is surfaced by `status` within 60 s.

### Tier 4 — Data layer for expansion (≈2–3 days, as instrument count grows)
- **4.1 CSV → Parquet** for candle/results data: faster load, smaller, columnar; keeps the numpy path.
- **4.2 Dataset registry:** path + content hash + provenance per dataset, recorded by every run for
  reproducibility across the instruments × windows matrix.
- **4.3 Capacity formula, documented:** `workers ≈ cores − 2`; SQLite tolerates few writers, Postgres
  effectively lifts the cap — encode this where `WORKERS` is defined.

### Tier 5 — Orchestration (only if multi-node) (≈1–2 weeks, deferred)
- **5.1 Distributed trials** via Optuna+Postgres across nodes or **Ray Tune**.
- **5.2 Job queue** (Redis/RQ) to schedule instrument × TF × window sweeps.

### Explicitly **not** needed yet
- **Dask** (Study 1) — wrong bottleneck, negative ROI on in-RAM data.
- **MongoDB** (Study 2) — unsupported by Optuna; columnar/relational beats it for our tabular data.
- A microservice/cluster rewrite — single box + Postgres + resilience tiers covers foreseeable growth.

---

## 7. Decision matrices

### 7.1 Compute engine (weights reflect *our* workload)

| Criterion (weight) | numpy (today) | numpy+Numba | Dask | Ray Tune |
|--------------------|:---:|:---:|:---:|:---:|
| Fits in-RAM 28 MB workload (×3) | 5 | 5 | 2 | 4 |
| Per-trial latency (×3) | 4 | 5 | 2 | 4 |
| Solves the DB bottleneck (×3) | 1 | 1 | 1 | 2* |
| Simplicity/ops (×2) | 5 | 4 | 2 | 3 |
| Multi-node future (×1) | 1 | 1 | 4 | 5 |
| **Weighted total** | **40** | **43** | **23** | **38** |

\*Ray helps indirectly by managing distribution; the store still needs Postgres. **Winner: keep numpy;
add Numba if/when latency matters.**

### 7.2 Results store

| Criterion (weight) | SQLite (today) | SQLite+WAL+perTF | **PostgreSQL** | MongoDB |
|--------------------|:---:|:---:|:---:|:---:|
| Concurrent writers (×3) | 1 | 3 | 5 | 5 |
| Optuna-native (×3) | 5 | 5 | 5 | 0 |
| Fixes the incident (×3) | 1 | 4 | 5 | — |
| Ops cost (×2, higher=cheaper) | 5 | 5 | 3 | 2 |
| Analytical SQL (×1) | 4 | 4 | 5 | 1 |
| **Weighted total** | **30** | **45** | **53** | **—** |

**Winner: PostgreSQL** (durable); **SQLite+WAL+per-TF** is the strong stop-gap shippable today.

---

## 8. Migration playbooks (concrete code)

> Reference only — not applied. Each is small and reversible.

### 8.1 Tier 0 — harden SQLite (drop-in within `run_study`)

```python
import sqlite3, optuna
from optuna.exceptions import StorageInternalError

_DB = _STUDIES / f"wsh_{tf_name}.db"            # 0.3 per-TF file (one lock per study)
with sqlite3.connect(_DB) as _c:                # 0.2 enable WAL once per file
    _c.execute("PRAGMA journal_mode=WAL;")
    _c.execute("PRAGMA synchronous=NORMAL;")

storage = optuna.storages.RDBStorage(
    url=f"sqlite:///{_DB}",
    engine_kwargs={"connect_args": {"timeout": 60}},   # 0.2 wait up to 60s for the lock
)
study = optuna.create_study(study_name=f"{study_prefix}_{tf_name}", storage=storage,
                            directions=["maximize","maximize","maximize"],
                            sampler=optuna.samplers.NSGAIIISampler(seed=seed, constraints_func=_constraints),
                            load_if_exists=True)
study.optimize(objective, n_trials=n_trials, show_progress_bar=False,
               catch=(StorageInternalError,))          # 0.1 a lock blip kills one trial, not the worker
```

Matching reader/launcher edits: `report_wsi.py` loops `wsh_<tf>.db`; `remote_wsi.sh` `create_study` +
`cmd_counts` + `cmd_pull` use the per-TF path.

### 8.2 Tier 1 — PostgreSQL (single switch)

```python
import os
STORAGE_URL = os.environ.get("WSH_STORAGE_URL", f"sqlite:///{_DB}")   # 1.2 one source of truth
storage = optuna.storages.RDBStorage(
    url=STORAGE_URL,                                                  # e.g. postgresql://wsh:***@localhost/wsh
    engine_kwargs={"pool_size": 32, "max_overflow": 8},              # size to worker count
)
```

```bash
# server, once: a containerized Postgres avoids touching the host
docker run -d --name wsh-pg -e POSTGRES_USER=wsh -e POSTGRES_PASSWORD=*** \
  -e POSTGRES_DB=wsh -p 5432:5432 -v wsh_pg:/var/lib/postgresql/data postgres:16
# launcher: export WSH_STORAGE_URL=postgresql://wsh:***@localhost:5432/wsh   (replaces the sqlite literal)
```

### 8.3 Tier 2 — worker respawn watchdog (launcher)

```bash
run_worker () {   # respawn until the study reaches its target trial count
  local tf="$1" per="$2"
  while :; do
    python3 -u optimize/optimizer.py "$tf" --trials "$per" --folds 5 --min-trades 5 $IND_ARGS \
      >> "$WSI/logs/$tf.log" 2>&1
    done_n=$(python3 -c "import optuna,os;print(len(optuna.load_study(study_name=f'${PREFIX}_$tf',storage=os.environ['WSH_STORAGE_URL']).trials))")
    [ "$done_n" -ge "$TARGET" ] && break
    echo "[watchdog] $tf worker exited at $done_n/<$TARGET — respawning" >> "$WSI/logs/$tf.log"
  done
}
```

### 8.4 Tier 3 — live FAIL counts in `cmd_status`

```python
from optuna.trial import TrialState
s = optuna.load_study(study_name=f"{PREFIX}_{tf}", storage=URL)
states = [t.state for t in s.get_trials(deepcopy=False)]
print(tf, "complete", states.count(TrialState.COMPLETE),
          "running", states.count(TrialState.RUNNING),
          "FAIL",    states.count(TrialState.FAIL))
```

---

## 9. Risk register

| Risk | Likelihood | Impact | Mitigation |
|------|:---:|:---:|------------|
| Per-TF SQLite files complicate report aggregation | med | low | reader loops the 6 files; covered in 8.1 |
| Postgres adds an ops dependency (uptime, backups) | med | med | containerized + volume; `pg_dump` cron; it's localhost-only |
| Migrating existing `wsh.db` history to Postgres | low | med | keep SQLite read-only for past studies; start new prefix on Postgres; or `optuna.copy_study` |
| Numba JIT warm-up cost / dtype constraints | low | low | optional, gated behind a flag; parity test guards correctness |
| Watchdog respawn masks a real recurring crash | low | med | log every respawn; alert if respawns exceed a threshold |
| WAL files on network/edge filesystems misbehave | low | med | studies live on local NVMe (confirmed 13% used) — fine |

---

## 10. Appendix — evidence & references

### 10.1 Incident evidence (summarized; full detail in `INCIDENT_wsh4_sqlite_contention.md`)
- Trial counts at idle: 4h 2,146 / 2h 5,000 / 1h 2,653 / 15m 3,507 / 5m 5,004 / 2m 4,256.
- Error signature: `sqlite3.OperationalError: database is locked` → `StorageInternalError` → worker exit,
  clustered ~01:00–01:01; 5m logged zero, 2h one.
- Ruled out: OOM (`free -g` 44 GB free, no dmesg OOM), disk (13%), logic (tracebacks end in
  sqlalchemy/sqlite3).

### 10.2 Top-up in progress (this session)
`./remote_wsi.sh run 2900 "4h 1h"` resumed both studies (`load_if_exists`); verified **19 optimizer
procs**, 4h past trial ~2,240 and 1h past ~2,754, no lock errors (8 workers, no competing studies) —
empirically confirming that reducing concurrent writers removes the contention, consistent with the
Tier-0/1 recommendations.

### 10.3 Code references
- `optimize/optimizer.py:67` (shared `_DB`), `:133–141` (`create_study` + unguarded `study.optimize`).
- `optimize/report_wsi.py:34,76` (reader).
- `optimize/server/remote_wsi.sh` (`WORKERS` map, `cmd_run` launch fan-out, `cmd_counts`, `cmd_pull`).
- `optimize/fast_engine.py` (135 LoC, numpy kernel), `indicators/runner.py` (249 LoC).

### 10.4 External references
- Optuna storages: `RDBStorage` (SQLite/PostgreSQL/MySQL), `JournalStorage` (file/Redis) — MongoDB not
  supported. Optuna docs recommend an RDB for distributed/many-worker studies.
- SQLite concurrency: single-writer model; WAL allows concurrent readers with one writer; `busy_timeout`
  controls lock-wait before error.
- Alternatives for distributed HPO: Ray Tune (Optuna sampler support); Parquet/DuckDB for columnar
  analytics; TimescaleDB for time-series.
```
