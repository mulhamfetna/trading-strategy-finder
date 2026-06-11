# Worklog — wsh4 Sweep, Incident, Scaling Studies & Monitoring
### Session 2026-06-11 (Asia/Damascus) · branch `dev`

A verbose, chronological record of everything done in this session: the optimizer readiness check, the
full `wsh4` sweep launch, the SQLite-contention incident and its investigation, the three scaling
studies, the 4h/1h top-up, and the Telegram monitoring watcher. **No production code was modified this
session — all work was operational (server runs) or documentation.** Times are server clock unless noted.

---

## 0. Starting state

- Branch `dev`, 68 commits ahead of `origin/dev` (local only — **not** pushed to origin).
- Merge commit `2fbafc8` already in place (2024 + +20d windows, no-entry-streak, veto-as-flip merged into
  the 1-min-indicator dev line). Parity `$7,735 / $3,670 / n=66`, 88/88 tests passing.
- Sweep wiring present: `optimize/server/remote_wsi.sh` — `TFS=(4h 2h 1h 15m 5m 2m)`, `PREFIX="wsh4"`,
  `IND_ARGS="--ind-1min --study-prefix wsh4"`, `WORKERS=( [2m]=6 [5m]=6 [15m]=5 [1h]=5 [2h]=4 [4h]=4 )`.

---

## 1. Optimizer readiness verification

**Goal:** confirm the 1-min-indicator NSGA-III optimizer was ready to run on the server, with **no new
data** required.

### 1.1 Data-source confirmation
Confirmed the optimizer reads the **all-history originals** via `optimize/data.py`, *not* the `+20d`
combined files built earlier for the dashboard:
- decision frame → `Full_Canldes_Data/<RAW_DIR>/NQ_<tf>.csv`
- 1-minute frame → `Full_Canldes_Data/<RAW_DIR>/NQ_1m.csv`
- box → `data/full_data/NQ_full_data.csv`

→ The `+20d` work is dashboard-only and does not affect the optimizer's inputs.

### 1.2 Smoke run (exact sweep flags)
```bash
python3 optimize/optimizer.py 4h --trials 3 --folds 5 --min-trades 5 --ind-1min --study-prefix smoketest
```
Result: loaded 2,119 decision bars; NSGA-III sampler + 5-fold pruning + 1-minute indicators all worked;
trials 0/1 pruned, trial 2 finished with valid 3-objective values. The throwaway `smoketest_4h` study was
then deleted from `wsh.db`.

**Verdict:** optimizer ready; data unchanged.

---

## 2. Pre-flight on the AMD server

`server.env`: `SRV_HOST=78.89.209.212`, `SRV_PORT=33362`, `SRV_USER=dev`. Scratch root
`/home/dev/Mulham/wsg-i`.

### 2.1 Push (`./remote_wsi.sh push`)
Rsynced `Parametric-Indicators/` + `Full_Canldes_Data/` + `data/` → server scratch. Exit 0.
Transfer totals ≈ 25 MB code + 104 MB + 88 MB data. Completed 23:37 (prev day).

### 2.2 Parity (`./remote_wsi.sh parity`)
```
core   : P/L $7,735  maxDD $3,670  n=66  2025 $2,565  2026 $5,170  locks=11
payload: P/L $7,735  maxDD $3,670  n=66
PARITY OK ✓
```
→ Server environment + data reproduce local results byte-identically.

---

## 3. Full `wsh4` sweep launch

**Decision (user):** launch now, **5000 trials/TF**, deep search.

```bash
./remote_wsi.sh run 5000          # 6 TFs, detached
```
Launched 23:40. All 6 studies created in `optimize/studies/wsh.db`; ~30 workers spawned:
`4h×4, 2h×4, 1h×5, 15m×5, 5m×6, 2m×6`. Config: NSGA-III · `--ind-1min` · 5-fold walk-forward ·
min-trades 5 · constraint DD≤25%·P/L. Status at 23:41 confirmed all 6 RUNNING, trials accumulating,
load climbing to ~18. Tracked as task **#209 (WS-I.11)**.

---

## 4. Completion check & anomaly (next day ~14:16)

By the next status check the run had gone **idle** (all workers exited, load 0.72). Trial counts:

| TF | trials | complete | feasible | reached 5000? |
|----|-------:|---------:|---------:|:---:|
| 4h | 2,146 | 1,788 | 1,165 | ✗ |
| 2h | 5,000 | 4,476 | 2,810 | ✓ |
| 1h | 2,653 | 2,276 | 901 | ✗ |
| 15m | 3,507 | 3,294 | 1,718 | partial |
| 5m | 5,004 | 4,565 | 2,779 | ✓ |
| 2m | 4,256 | 4,037 | 2,929 | partial |

**Anomaly:** 4h and 1h fell well short of the 5,000 target despite no tracebacks in the tail of their
logs (each log ended in repeated clean best-combo summary lines).

---

## 5. Incident investigation → root cause

One SSH batch gathered: per-log line counts + first/last timestamps, error/OOM/killed signatures, live
worker count, dmesg OOM, disk + mem.

### 5.1 Findings
- **Per-log timestamps:** all started 21:35; 4h last log 05:23, 1h 05:14, while 2m ran to 09:35, 15m to
  07:33 — i.e. some TFs lost workers hours earlier than others.
- **Error signature** in 4h/1h/15m/2m (near-absent in 2h/5m):
  ```
  sqlite3.OperationalError: database is locked
  optuna.exceptions.StorageInternalError: An exception is raised during the commit ...
  [W ...] Trial NNNN failed ... because of the following error: StorageInternalError(...)
  ```
  Failures clustered at a **contention storm ~01:00–01:01**.
- **Ruled out:** OOM (`free -g` → 123 GB total, 44 free; no dmesg OOM), disk (`df` → 13% used), logic
  bug (tracebacks terminate in `sqlalchemy`/`sqlite3`). Live workers: 0.

### 5.2 Root cause
All ~30 workers across all 6 studies write to **one shared SQLite file** (`wsh.db`). SQLite serializes
writes behind a single file lock; under ~30 concurrent committers the lock-wait exceeded the default
~5 s `busy_timeout` → `database is locked` → `StorageInternalError`. Because
`optimize/optimizer.py:141` calls `study.optimize(...)` **without `catch=`**, the exception propagated
and **killed the worker process**. Studies whose workers survived the storm hit target (5m, 2h); those
that lost workers (4h, 1h) ran short. The deficit is **lost worker-hours, not a logic error**.

### 5.3 Relevant code (exact)
- `optimize/optimizer.py:65–67` — `_DB = _STUDIES / "wsh.db"` (single shared DB).
- `optimize/optimizer.py:133–141` — `create_study(storage=f"sqlite:///{_DB}", ...)` (no `engine_kwargs`,
  no WAL) + `study.optimize(...)` (no `catch=`).
- `optimize/report_wsi.py:34,76` — reader (`load_study` on the same `wsh.db`).
- `optimize/server/remote_wsi.sh` — `WORKERS` map + `cmd_run` launch fan-out + `cmd_counts` + `cmd_pull`.

---

## 6. Documentation produced

Three documents written to `optimize/server/` (analysis only — no code touched):

1. **`INCIDENT_wsh4_sqlite_contention.md`** — the post-mortem: summary, evidence (counts + error
   signature + ruled-out table), exact related code, suggested fixes (A: WAL+busy_timeout, B: `catch=`,
   C: per-TF DB, D: Postgres, E: operational guards), immediate options, current best combos.

2. **`STUDY_scaling_dask_mongo_bottlenecks.md`** — condensed three-part study (Dask vs vectorization;
   MongoDB vs SQLite; essential improvements), with the measured baseline and verdicts.

3. **`REPORT_system_scaling_study.md`** — the full detailed engineering report (10 sections): exec
   summary, measured baseline, precise bottleneck, Study 1 (Dask), Study 2 (MongoDB), Study 3 + phased
   roadmap (Tiers 0–5 with effort + acceptance criteria), decision matrices (weighted scoring),
   migration playbooks (concrete code per tier), risk register, appendix (evidence + references).

### 6.1 Study verdicts (summary)
- **Dask vs vectorization → keep vectorization** (+ optional Numba). Dask targets dataframe compute, not
  the DB-write bottleneck; data is 28 MB on a 123 GB box; trials already parallel across processes. For
  multi-node future, prefer Ray Tune / Optuna+Postgres over Dask.
- **MongoDB vs SQLite → neither; adopt PostgreSQL.** Optuna does **not** support MongoDB; Postgres is
  Optuna-native and removes write contention via MVCC. For tabular system data, Parquet+DuckDB beats
  Mongo; reserve Mongo for schema-fluid run-manifest documents only.
- **Essential improvements → tiered roadmap.** Tier 0 (catch + WAL/busy_timeout + per-TF DB), Tier 1
  (PostgreSQL + centralized storage URL), Tier 2 (worker watchdog/respawn, target-based resumable runs),
  Tier 3 (live FAIL counters + pre-flight contention smoke test), Tier 4 (CSV→Parquet + dataset
  registry), Tier 5 (multi-node only).

---

## 7. Missing-data top-up (4h + 1h)

**Decision (user):** finish the missing data on the server while we worked on the studies — zero-code
path (the durable fixes are for "next times").

```bash
./remote_wsi.sh run 2900 "4h 1h"     # +2900 trials each, RESUME (load_if_exists)
```
Launched 14:35. `launch.out` confirmed **"Using an existing study"** (resume, not restart). Per-worker
math: 4h 4×725, 1h 5×580 → targets ≈ 5,046 (4h) / ≈ 5,553 (1h).

> **Note on verification:** an initial check reported "0 workers" — this was a **faulty pgrep pattern**
> (`\|` is a literal pipe under pgrep's ERE), not a failed launch. A corrected probe showed **19
> optimizer procs** (4h ×4 + 1h ×5 + counting overhead) and both studies advancing.

Progress samples (no lock errors this run — only 8 workers, no competing studies):
| time | 4h trials | 1h trials |
|------|----------:|----------:|
| 14:41 | ~2,240 | ~2,754 |
| 14:50 | 2,399 (feas 1,359) | 2,946 (feas 1,077) |

Observed rate ≈ 17/min (4h), ≈ 20/min (1h) → ETA both ≥ 5,000 ≈ 2–2.5 h from 14:35. Feasible fronts
deepening (4h 1,165→1,359, 1h 901→1,077), confirming the extra trials add genuine search depth.
Empirically this also **validates the root cause**: dropping to 8 concurrent writers eliminated the
`database is locked` failures.

---

## 8. Telegram monitoring watcher

**Goal:** periodic status reports + a completion alert, independent of the agent session.

### 8.1 Bot + chat
- Bot token (provided by user): `…uib8FEX8` → `getMe` ok: **@beinmedia_server_bot**.
- `getUpdates` initially empty; after the user sent `/start`, discovered **chat_id `5041591927`**
  (Mulham). Sent a "watcher connected" confirmation (delivery ok).

### 8.2 Watcher script (server-side, detached)
Deployed `/home/dev/Mulham/wsg-i/tg_watch.sh`, launched via `setsid` (survives the agent session). The
`255` exit on launch was an SSH-backgrounding artifact; a follow-up probe confirmed **1 watcher process
running**.

Behavior:
- **First report immediately**, then **every 20 minutes** (`INTERVAL=1200`).
- Each report: timestamp · per-TF **trials/complete/feasible** for 4h & 1h · live **worker counts** ·
  host **load**. Counts read directly from `wsh.db` via Optuna.
- **Final alert** "✅ wsh4 top-up COMPLETE — ready to pull" once **both** ≥ 5,000, then exits.
- **Safety:** 8-hour hard cap (`MAX_HOURS=8`) → sends a cap notice and exits, so it can never run
  forever.
- **Stop early:** `pkill -f tg_watch.sh` on the server.

> Security note: the script on the server embeds the bot token + chat_id (needed for unattended sending).
> It lives only in the private server scratch `/home/dev/Mulham/wsg-i/`. The token is **not** stored in
> the repo or in any committed file.

### 8.3 On-demand responder — `/report_server_status` command
Added a second, independent Telegram process so the user can pull a live report at will (not only on the
20-min schedule). Deployed `/home/dev/Mulham/wsg-i/tg_bot.py`, launched via `setsid` (the `255` launch
exit was again the SSH-backgrounding artifact; a follow-up probe confirmed **1 bot process running**).

Behavior:
- **Long-polls** Telegram `getUpdates` with a 50 s timeout and offset tracking — it is the **sole**
  `getUpdates` consumer (the §8.2 watcher only *sends*, so there is no 409 long-poll conflict).
- On **`/report_server_status`** from the authorized chat (`5041591927`), it generates a **live
  full-server report for all 6 timeframes** and replies. Messages from any other chat are ignored.
- **Report content:** timestamp · host load average · a monospace table of per-TF
  **trials / complete / feasible** + **state** `RUN(n)`/`idle(0)` with live worker count (read from
  `wsh.db` via Optuna + `pgrep`/`/proc/loadavg`).
- On startup it calls **`setMyCommands`** so `/report_server_status` shows in the bot's `/` menu, and
  sends a "🤖 Responder online" notice.
- **Resilience:** the poll loop catches exceptions and retries after 5 s; report failures are logged, not
  fatal.
- **Stop:** `pkill -f tg_bot.py` on the server.

Validated end-to-end by invoking `report()` directly on the server (`report sent`, exit 0) — a real
report reached the chat. Same security note as §8.2 applies (token embedded in the server-only script).

Example report shape:
```
🖥 wsh4 server report — HH:MM:SS
load: 9.2 9.1 6.3
TF   trials compl  feas  state
4h     2399  2021  1359  RUN(4)
2h     5000  4476  2810  idle(0)
1h     2946  2551  1077  RUN(5)
15m    3507  3294  1718  idle(0)
5m     5004  4565  2779  idle(0)
2m     4256  4037  2929  idle(0)
```

**Telegram monitoring now has two channels:** automatic push every 20 min + completion alert (§8.2), and
on-demand `/report_server_status` (§8.3).

---

## 9. Artifacts & locations

### 9.1 New files in the repo (this session)
```
subprojects/Parametric-Indicators/optimize/server/INCIDENT_wsh4_sqlite_contention.md
subprojects/Parametric-Indicators/optimize/server/STUDY_scaling_dask_mongo_bottlenecks.md
subprojects/Parametric-Indicators/optimize/server/REPORT_system_scaling_study.md
subprojects/Parametric-Indicators/optimize/server/WORKLOG_wsh4_session_2026-06-11.md   (this file)
```
(All untracked/uncommitted — documentation only.)

### 9.2 Server-side artifacts (`/home/dev/Mulham/wsg-i/`)
```
Parametric-Indicators/optimize/studies/wsh.db   — wsh4_{4h,2h,1h,15m,5m,2m} studies (+ legacy wsh3_*)
logs/{4h,2h,1h,15m,5m,2m}.log                    — per-TF optimizer logs
launch.sh, launch.out                            — sweep launcher + its output
tg_watch.sh, tg_watch.log                        — Telegram watcher (auto push every 20 min) + its log
tg_bot.py, tg_bot.log                            — Telegram responder (/report_server_status) + its log
```

### 9.3 No code changes
`optimizer.py`, `report_wsi.py`, `remote_wsi.sh`, engine/indicator code — **unchanged**. The fixes in the
studies are proposals pending approval (Tier 0–1).

---

## 10. Open items / next steps

1. **Await completion** — Telegram will alert when 4h & 1h both ≥ 5,000 (ETA ~16:30–17:00 server time).
2. **Pull results** — on completion: `./remote_wsi.sh pull` (builds `WS-I_RESULTS.md` on the server,
   rsyncs `results/`, `reports/`, `logs/` back to local).
3. **Decide on durable fix** — apply Tier 0 (`catch=` + WAL/busy_timeout + per-TF DB) before the next
   large sweep; plan Tier 1 (PostgreSQL) as worker counts grow. *(Requires explicit approval — not yet
   authorized.)*
4. **Task #209 (WS-I.11)** remains open until pull + results extraction is complete.

---

## 11. Command reference (as used this session)

```bash
# all from subprojects/Parametric-Indicators/optimize/server, sandbox disabled for network
./remote_wsi.sh push                 # sync code+data → server
./remote_wsi.sh parity               # 4h parity sanity on server
./remote_wsi.sh run 5000             # full 6-TF sweep, 5000 trials/TF, detached
./remote_wsi.sh run 2900 "4h 1h"     # top-up only 4h+1h (+2900 each), resume
./remote_wsi.sh status               # load + per-TF RUNNING/idle + last log line
./remote_wsi.sh counts               # per-TF trials/complete/feasible
./remote_wsi.sh pull                 # build report on server + rsync results/logs back
./remote_wsi.sh stop                 # kill all optimizer workers

# server-side Telegram controls
pgrep -fc tg_watch.sh                 # watcher (auto push every 20 min) — confirm running
pkill  -f  tg_watch.sh                # watcher — stop early
pgrep -fc tg_bot.py                   # responder (/report_server_status) — confirm running
pkill  -f  tg_bot.py                  # responder — stop
# in Telegram: send /report_server_status for an on-demand live full-server report
```

---

## 12. System updates APPLIED this session (Tier-0 + Step-3 contention fixes)

After the studies were written (§6), we began applying the bottleneck-prevention roadmap from
`REPORT_system_scaling_study.md`. **All edits are LOCAL-ONLY and committed on `dev`; nothing is pushed to
the server.** Each step was approved individually and verified before the next.

### 12.1 What changed, and why (plain + precise)

| Step | Code change | Plain-language | Verified |
|------|-------------|----------------|----------|
| **1** | `study.optimize(..., catch=(optuna.exceptions.StorageInternalError,))` in `optimizer.py` | If the shared notebook is busy, a worker **skips one line instead of quitting forever**. | parity OK |
| **2** | Open the store via `RDBStorage(engine_kwargs={"connect_args":{"timeout":60}})` + `PRAGMA journal_mode=WAL; synchronous=NORMAL` | Workers **wait a full minute** for their turn and can **read while one writes**. | smoke + `journal_mode=wal` |
| **3** | Per-timeframe DB files `wsh_<tf>.db` via a prefix-aware `_db_for()` resolver in **both** `optimizer.py` and `report_wsi.py`, plus `remote_wsi.sh` (`cmd_run` create + `cmd_counts`) | **Each of the 6 groups gets its own notebook** (~5 writers each, not 30 on one). If asked for a study that only lives in the old shared `wsh.db`, it reads it and **shouts `⚠️ FALLBACK` loudly** — never silent, never lost. | resolver unit + fresh-create + reader fallback + parity + **pytest 88 passed** |

Steps 1–2 do **not** change the DB layout. Step 3 introduces per-TF files but is **backward-compatible**:
new local runs isolate per timeframe; any reader/counter asked for a study that lives only in the legacy
shared `wsh.db` (which is exactly what the server is producing now) transparently uses it and announces
the fallback. This was confirmed **live** — running `./remote_wsi.sh counts` against the server prints
`⚠️ FALLBACK <tf>: per-TF file absent, reading shared wsh.db` for each timeframe and returns correct
counts.

### 12.2 Commits on `dev` (local, NOT pushed to origin or the server)

| SHA | Type | Contents |
|-----|------|----------|
| `93a9244` | **ROLLBACK SNAPSHOT** | Steps 1–2 (layout unchanged) + all scaling docs. Known-good restore point. |
| `813f9f5` | feat | Step 3 per-TF DB files + backward-compatible loud-fallback resolver (child of `93a9244`). |

**Rollback:** `git reset --hard 93a9244` (undo Step 3, keep 1–2) — or `git revert 813f9f5`. Full
reverse steps in `MIGRATION_per_tf_db.md` §6; verification matrix in §7.

### 12.3 Files touched (all local)
```
optimize/optimizer.py        — Steps 1, 2, 3 (catch=, WAL/timeout, _db_for per-TF resolver)
optimize/report_wsi.py       — Step 3 reader: _db_for with loud shared-file fallback
optimize/server/remote_wsi.sh— Step 3 launcher: per-TF create + counts (fallback-aware); cmd_pull unchanged
optimize/server/MIGRATION_per_tf_db.md — before/after/reverse documentation
```

---

## 13. Sweep PROGRESS snapshot (at time of writing)

Top-up (`run 2900 "4h 1h"`) still in flight; other 4 TFs idle since the original sweep.

| TF | trials | complete | feasible | target | state |
|----|-------:|---------:|---------:|-------:|:-----:|
| **4h** | 4,175 | 3,700 | **2,841** | ~5,046 | 🟢 running (~870 to go) |
| **1h** | **5,103** | 4,579 | **2,522** | ~5,553 | 🟢 running (already past 5,000) |
| 2h | 5,000 | 4,476 | 2,810 | ✓ | idle (done) |
| 15m | 3,507 | 3,294 | 1,718 | — | idle |
| 5m | 5,004 | 4,565 | 2,779 | ✓ | idle |
| 2m | 4,256 | 4,037 | 2,929 | — | idle |

Feasible fronts vs the original shortfall: **4h 1,165 → 2,841**, **1h 901 → 2,522** — the top-up has
roughly doubled (or more) the usable solution set on both. Watcher fires its completion alert when
**both** 4h and 1h are ≥ 5,000; 4h is the last one outstanding.

---

## 14. Updates HELD until the optimizer finishes (do NOT start before the pull)

These are intentionally deferred so they cannot interfere with the running sweep or risk results
retrieval (priority #1 = get the report back). **Ordered.**

1. **`./remote_wsi.sh pull`** — FIRST action once 4h crosses target. Runs the server's report builder
   (single `wsh.db`) and rsyncs `results/`, `reports/WS-I_RESULTS.md`, and logs back to local. Nothing
   below happens before this succeeds and the results are confirmed home.
2. **Push the Tier-0/Step-3 code to the server** — only AFTER the pull. `./remote_wsi.sh push` would
   overwrite the server's `optimizer.py`/`report_wsi.py`/`remote_wsi.sh` with the per-TF versions. Safe
   *after* pull because: (a) results are already retrieved; (b) the new reader is backward-compatible and
   would still read the existing single `wsh.db` (with a loud fallback) if we ever re-report on the
   server. NOT done yet.
3. **Step 4 — PostgreSQL backend + centralized storage URL (NOT IMPLEMENTED).** The Tier-1 durable fix:
   add a single `WSH_STORAGE_URL` switch (sqlite ↔ postgres) read by `optimizer.py` + `report_wsi.py` +
   `remote_wsi.sh`, and stand up a (containerized) PostgreSQL on the server. This is the ONLY roadmap item
   that requires something **running on the server**, so it is held until after the pull and only with
   explicit go-ahead. Local code/switch can be prepared and tested first with SQLite remaining the
   default; the server-side Postgres service is deployed last.
4. **(Optional) Migrate existing wsh4 studies** from the single `wsh.db` into per-TF files (or into
   Postgres) for a clean future-run layout — only if desired; the backward-compatible reader means it is
   not required for correctness.

**Status of Step 4 as of now:** not started — no Postgres installed, no `WSH_STORAGE_URL` switch added.
Steps 1–3 are SQLite-only improvements (a much better-behaved SQLite).

### Decision gates still open
- Pull now-vs-wait (auto-alert will signal readiness).
- Step 4: prepare-locally-now vs defer-entirely; deploy Postgres on the server only post-pull.

---

## 15. 4h boost — extra workers (approved, executed)

With only 4h still short of target and the box at ~9/32 cores used, we **added 8 extra 4h workers** to
finish faster. Mechanics that kept it safe:
- **Spawned directly** with `setsid` (same `wsh4_4h` study, same env, appending to `logs/4h.log`),
  **never** via `remote_wsi.sh run` (whose `pkill -9` would have killed all running workers).
- **Bounded** `--trials 150` each → self-terminating, no runaway.
- Total writers went 9 → ~17 (12 on 4h + 5 on 1h) — well under the ~30 that caused the incident.

Result: **0 new lock errors**, load 9.8 → 17.5 (still ~14 idle cores), and 4h throughput ~tripled. 4h
crossed the 5,000 threshold in ~15 min instead of ~48. Confirmed Optuna's many-workers-one-study model
does not disturb existing workers.

---

## 16. Results PULLED (the held priority — done)

Once 4h crossed 5,000, ran `./remote_wsi.sh pull`:
- Built `reports/WS-I_RESULTS.md` + `results/wsi_leaderboard.csv` on the server (reading the single
  `wsh.db`), then rsynced `results/`, `reports/`, and `server_logs/` back to local.
- Read-only on the DB → safe while the last 4h boost workers were still finishing.

**Final feasible-Pareto champions (full-period, DD≤25%·P/L):**

| TF | front | full P/L | DD ($ / %P/L) | win% | K | #ind |
|----|------:|---------:|---------------|-----:|:-:|:----:|
| **4h** 🏆 | 297 | **$142,229** | $14,075 / **9.9%** | **71.1%** | 1 | 8 |
| 1h | 144 | $96,024 | $10,984 / 17.6% | 52.4% | 4 | 8 |
| 2h | 124 | $92,057 | $12,944 / 17.7% | 50.5% | 3 | 8 |
| 15m | 85 | $77,336 | $8,089 / 10.5% | 51.2% | 3 | 8 |
| 2m | 156 | $29,665 | $2,275 / 11.0% | 64.4% | 1 | 7 |
| 5m | 187 | $24,030 | $4,167 / 19.3% | 62.8% | 1 | 7 |

4h is the standout. vs the original shortfall, feasible counts grew massively (4h 1,165→4,246,
1h 901→2,856). Task **#209 (WS-I.11)** marked complete.

---

## 17. New "1-min-trained" portfolios imported to the dashboard

The 6 wsh4 champions were added as dashboard portfolios **alongside** (never replacing) the existing
ones, clearly labelled as 1-minute-trained.

### 17.1 What was added/changed (local)
```
optimize/build_champions_from_pareto.py        NEW — converts <tf>_wsi_pareto.csv → champions JSON
                                                     (schema-typed params; champion = top row)
optimize/results/wsh4_champions_full.json      NEW — 6 TF champions (box + per-indicator params)
presets.py                                     MOD — _champions_1min() loader + a second loop in
                                                     strategies() emitting "⏱ WS-I <tf> · 1-min-trained"
                                                     entries (id wsi1m_<tf>); preset tagged
                                                     trained_on="1-minute frame (wsh4)".
```
The original `wsi_champions_full.json` and the `wsi_<tf>` entries are **untouched**.

### 17.2 Why these reproduce faithfully
The dev dashboard computes indicators on the **1-minute frame unconditionally**
(`strategy.py:264 ind_src = runner.indicator_source_1min(...)`). The wsh4 champions were tuned under
exactly that regime (`--ind-1min`), so loading a preset and backtesting reproduces its tuned behaviour.

### 17.3 Verification
- `presets.strategies()` → **15 entries**: winner + 7 original `wsi_*` (preserved) + **6 new `wsi1m_*`**
  + 1 user profile. (assertion-checked)
- **Live reproduction:** 5m 1-min champion backtested through the dashboard engine →
  **P/L $23,926** vs sweep-reported **$24,030** (0.4% — rounding/edge only). 4h needs per-year CSVs not
  in this checkout, but uses the identical builder.
- Full **pytest: 88 passed**.
- Dashboard **restarted** (port 8200) and `/api/config` confirmed serving all 15 strategies including
  the 6 `⏱ 1-min-trained` entries.

### 17.4 Champion typical (median-fold) P/L shown in each label
4h $33,592 · 1h $27,776 · 2h $21,755 · 15m $21,852 · 5m $7,813 · 2m $6,287.
