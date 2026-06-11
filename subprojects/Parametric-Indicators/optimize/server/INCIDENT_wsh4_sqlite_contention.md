# Incident Report — wsh4 sweep: SQLite lock contention starved 4h/1h

**Date:** 2026-06-11
**Run:** WS-I.11 — `wsh4` 1-minute-indicator NSGA-III sweep on the AMD server
**Severity:** Medium — no data loss, no bad results; **two timeframes (4h, 1h) under-sampled** because worker processes died early. The Pareto fronts that *did* land are valid.
**Status:** Root-caused. Fix proposed (not yet applied — awaiting go-ahead).

---

## 1. Summary

The sweep launched ~30 worker processes across 6 timeframe studies (`4h 2h 1h 15m 5m 2m`), each
worker calling `study.optimize()` against **one shared SQLite database** (`optimize/studies/wsh.db`).
SQLite serializes all writes behind a single database-level file lock. Under ~30 concurrent committers
the lock-wait exceeded SQLite's default 5-second `busy_timeout`, raising
`sqlite3.OperationalError: database is locked`. Optuna wraps that as `StorageInternalError`, and because
`study.optimize()` was called **without `catch=`**, the exception propagated and **killed the worker
process**.

Timeframes whose workers happened to survive the contention storm reached the 5000-trial target
(**5m: 5004, 2h: 5000**). Timeframes that lost workers early fell short (**4h: 2146, 1h: 2653**;
15m: 3507 and 2m: 4256 lost workers later and landed in between).

**This is not a logic bug, OOM, or disk issue.** It is a known Optuna limitation: SQLite is not built
for many-writer distributed studies.

---

## 2. Evidence

### 2.1 Trial counts vs. 5000 target

| TF  | trials | complete | feasible (DD≤25%·P/L) | reached 5000? | last log ts |
|-----|-------:|---------:|----------------------:|:-------------:|:-----------:|
| 4h  | 2,146  | 1,788    | 1,165                 | ✗             | 05:23:41    |
| 2h  | 5,000  | 4,476    | 2,810                 | ✓             | 04:39:01    |
| 1h  | 2,653  | 2,276    | 901                   | ✗             | 05:14:51    |
| 15m | 3,507  | 3,294    | 1,718                 | partial       | 07:33:21    |
| 5m  | 5,004  | 4,565    | 2,779                 | ✓             | 05:08:08    |
| 2m  | 4,256  | 4,037    | 2,929                 | partial       | 09:35:37    |

`trials > complete` = failed trials (the lock failures). All workers started together at `21:35`.

### 2.2 Error signature (present in 4h, 1h, 15m, 2m; near-absent in 2h, 5m)

```
[W 2026-06-11 01:00:27] Caught an error from sqlalchemy: (sqlite3.OperationalError) database is locked
sqlite3.OperationalError: database is locked
  ...
optuna.exceptions.StorageInternalError: An exception is raised during the commit.
[W 2026-06-11 01:01:00] Trial 1195 failed ... because of the following error: StorageInternalError(...)
```

- Failures **cluster at ~01:00–01:01** — a contention storm where many studies committed simultaneously.
- **5m logged zero such errors** → all 6 workers survived → hit 5004.
- **2h logged a single warning** → survived → hit 5000.
- 4h crashed workers around trial ~1195; 1h around ~1078–1081.

### 2.3 Ruled out

| Hypothesis | Check | Result |
|------------|-------|--------|
| Out of memory | `free -g` → 123 GB total, 44 free, 70 cache; `dmesg` OOM | **No OOM** |
| Disk full | `df -h /home/dev` → 115 G / 937 G | **13% used** |
| Code/logic bug | Tracebacks all terminate in `sqlalchemy`/`sqlite3`, never engine/indicator code | **Not a logic bug** |
| Workers still hung | `pgrep -fc optimize/optimizer.py` | **0 — all exited** |

---

## 3. Related code (exact locations)

### 3.1 `optimize/optimizer.py` — the storage definition and the unguarded optimize call

```python
# line 65–67
_STUDIES = _HERE / "studies"
_STUDIES.mkdir(exist_ok=True)
_DB = _STUDIES / "wsh.db"                      # ← ONE shared DB for ALL timeframes
```

```python
# line 133–141
study = optuna.create_study(
    study_name=f"{study_prefix}_{tf_name}",
    storage=f"sqlite:///{_DB}",               # ← no busy_timeout, no WAL, no connect_args
    directions=["maximize", "maximize", "maximize"],
    sampler=optuna.samplers.NSGAIIISampler(seed=seed, constraints_func=_constraints),
    load_if_exists=True,
)
t0 = time.time()
study.optimize(objective, n_trials=n_trials, show_progress_bar=False)   # ← no catch= → a lock error kills the worker
```

**The two defects, precisely:**
1. `storage=f"sqlite:///{_DB}"` opens the SQLite file with library defaults — `busy_timeout` ≈ 5 s,
   rollback-journal mode (a writer blocks all readers). No `engine_kwargs` / `connect_args`.
2. `study.optimize(...)` has no `catch=` argument, so a transient `StorageInternalError` is fatal to
   the worker instead of failing just that one trial.

### 3.2 `optimize/server/remote_wsi.sh` — launch fan-out (the concurrency source)

```bash
# worker counts — sum ≈ 30 processes, ALL writing the same wsh.db
declare -A WORKERS=( [2m]=6 [5m]=6 [15m]=5 [1h]=5 [2h]=4 [4h]=4 )
```

```bash
# inside cmd_run() launch.sh heredoc
for pair in $spec; do
  tf=${pair%%:*}; w=${pair##*:}; per=$(( (TOTAL + w - 1) / w ))
  python3 -c "import optuna; optuna.create_study(study_name='${PREFIX}_$tf',
      storage='sqlite:///optimize/studies/wsh.db', ..., load_if_exists=True)"
  for i in $(seq 1 $w); do
    setsid bash -c "python3 -u optimize/optimizer.py $tf --trials $per --folds 5 \
        --min-trades 5 $IND_ARGS >> '$WSI/logs/$tf.log' 2>&1" < /dev/null &
  done
done
```

So **30 independent processes** open the same `wsh.db` and commit a trial every few seconds → the
write-lock contention that produced §2.2.

### 3.3 `optimize/report_wsi.py` — the downstream reader (must stay consistent with any DB change)

```python
# line 34
_DB = _HERE / "studies" / "wsh.db"
# line 76
study = optuna.load_study(study_name=f"{_PREFIX}_{tf}", storage=f"sqlite:///{_DB}")
```

Any move to per-TF DB files must update **both** `optimizer.py` and `report_wsi.py` (and the
`create_study` line + `cmd_counts` in `remote_wsi.sh`) so they read the same path.

---

## 4. Suggested improvements

Ordered by leverage. **Fix A+B together is the recommended durable fix.**

### A. Harden the SQLite connection (small, high impact)

Open the storage with a long `busy_timeout` and WAL journal mode so writers **wait** for the lock
instead of erroring, and readers don't block writers:

```python
storage = optuna.storages.RDBStorage(
    url=f"sqlite:///{_DB}",
    engine_kwargs={"connect_args": {"timeout": 60}},   # wait up to 60 s for the lock
)
# enable WAL once per file (readers + one writer concurrent; far less "database is locked")
import sqlite3
with sqlite3.connect(_DB) as _c:
    _c.execute("PRAGMA journal_mode=WAL;")
    _c.execute("PRAGMA synchronous=NORMAL;")
```

### B. Make a lock blip non-fatal (one-line change)

```python
study.optimize(objective, n_trials=n_trials, show_progress_bar=False,
               catch=(optuna.exceptions.StorageInternalError,))
```

A failed commit then fails **only that trial** (logged, retried by the next iteration) instead of
killing the worker. This alone would have kept 4h/1h workers alive to 5000.

### C. Per-timeframe database file (eliminates cross-study contention ~6×)

Give each TF its own file so the 30 workers split across 6 locks (≈5 per file) instead of 1:

```python
_DB = _STUDIES / f"wsh_{tf_name}.db"          # in run_study(), per TF
```

Update `report_wsi.py` (§3.3) and `remote_wsi.sh` (`create_study` + `cmd_counts` + `cmd_pull`) to the
same per-TF path. Combine with A+B. This is the cleanest structural fix; trade-off is the report/counts
helpers must iterate 6 files.

> **Note:** Optuna's own guidance is that SQLite "should not be used in distributed/parallel
> optimization with many workers." A+B makes the shared file workable; C removes most of the contention;
> a real RDB (D) removes all of it.

### D. (Optional, larger) Use a server-grade RDB

Run a local PostgreSQL/MySQL and point `storage` at it. Removes lock contention entirely and scales past
30 workers. Heavier setup; overkill unless worker counts grow well beyond 30.

### E. Operational guards (independent of A–D)

- **Watchdog/respawn:** in `launch.sh`, wrap each worker in a `while` that respawns it if it exits before
  the study reaches `n_trials`, so a dead worker self-heals.
- **Live failed-trial count in `cmd_status`:** surface `FAIL` states so a contention storm is visible in
  real time, not only in post-mortem log greps.
- **Stagger study starts:** launch the 6 studies a few seconds apart to avoid synchronized commit bursts.

---

## 5. Immediate options for *this* run

1. **Zero-code top-up:** re-run **only** 4h + 1h (`./remote_wsi.sh run 5000 "4h 1h"`). With no other
   studies competing, 8 workers on the shared DB face ~4× less contention and will very likely reach
   5000. `load_if_exists=True` resumes rather than restarts. Fastest path to the missing depth; does not
   fix the underlying fragility.
2. **Harden then relaunch (A+B, optionally C):** apply the fix above, re-push, relaunch 4h + 1h (or the
   full sweep). Durable — prevents recurrence on every future sweep.

The fronts already collected are valid regardless; the only deficit is **search depth** on 4h and 1h.

---

## 6. Current best feasible combo per TF (valid as-is)

| TF  | full P/L  | full DD       | win% | combo |
|-----|----------:|---------------|-----:|-------|
| 2h  | $98,676   | $16,881 (17%) | 45%  | slS60/slH109/tp127 · gate85 · K2 +9ind |
| 4h  | $95,815   | $19,013 (20%) | 74%  | slS115/slH241/tp69 · gate87 · K1 +5ind |
| 1h  | $53,733   | $5,825 (11%)  | 39%  | slS22/slH105/tp86 · gate60 · K5 +8ind |
| 15m | $57,822   | $7,154 (12%)  | 51%  | slS22/slH64/tp43 · gate92 · K3 +8ind |
| 2m  | $27,133   | $2,153 (8%)   | 62%  | slS12/slH19/tp18 · gate85 · K1 +7ind |
| 5m  | $25,865   | $4,568 (18%)  | 63%  | slS22/slH50/tp25 · gate76 · K1 +8ind |

*(4h/1h numbers come from a thinner search and may improve with the top-up.)*
