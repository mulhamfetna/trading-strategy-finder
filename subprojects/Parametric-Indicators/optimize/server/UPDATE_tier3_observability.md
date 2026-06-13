# Update Report — Scaling Tier 3: observability + pre-flight contention gate

**Date:** 2026-06-12 · branch `dev` · `ACTION_PLAN_scaling_tiers.md` Phase L · **local-only (no server change)**
**Type:** observability — additive, **trade math untouched**. Makes a contention storm visible in a poll and
catchable *before* a multi-hour sweep.

---

## 1. What changed (plain + professional)

**Professional.** Three observability gaps from the incident closed:
- **3.1 Live state counts** — `optimize/study_stats.py` reports **COMPLETE / RUNNING / FAIL / PRUNED / total**
  per study (honouring the Tier-1 storage URL). A contention storm now shows as **rising FAIL / dropping
  RUNNING** within one poll, not hours later via log grep. Wired as `remote_wsi.sh stats`.
- **3.2 Structured run log** — `study_stats.py --json` emits one JSON line per poll (prefix + per-study
  counts) that a cron/Telegram watcher can tail and alert on.
- **3.3 Pre-flight contention smoke** — `optimize/contention_smoke.py` spawns N worker processes that hammer
  ONE shared store with a few trials and asserts **zero `StorageInternalError` (lock) deaths**; exit 1 if
  any. Wired as `remote_wsi.sh smoke [workers] [trials]` — run it **before** committing to a sweep
  (complements the parity gate). It reproduces the wsh4 failure mode in seconds.

**Baby.** We added a **dashboard light** (`stats`) that shows green "completed", blue "running" and a red
"FAILED" number per timeframe — if red starts climbing you know the traffic jam is back *now*. And a
**10-second dress rehearsal** (`smoke`): before the real multi-hour race we send a crowd of runners at the
notebook/office and check nobody gets locked out. If anyone does, we don't start the real race.

---

## 2. New commands
```
./remote_wsi.sh stats                  # COMPLETE/RUNNING/FAIL/pruned/total per study (one poll)
./remote_wsi.sh smoke [workers] [trials]   # pre-flight lock probe (default 30×20); exit 1 ⇒ DO NOT launch
```
`smoke` uses `WSH_STORAGE_URL` when set (e.g. a Postgres pre-flight) else a fresh temp sqlite with
WAL+busy_timeout — i.e. it tests the *same* store concurrency the sweep will face.

---

## 3. Code touched / links
| File | Change |
|------|--------|
| `optimize/study_stats.py` (NEW) | `stats(prefix, tf)` → state counts; CLI table + `--json`; reuses `trial_count._quiet_url` |
| `optimize/contention_smoke.py` (NEW) | `run_smoke(url, workers, trials)` → `{lock_deaths, ok}`; CLI exit 0/1; WAL on sqlite; `spawn` Pool |
| `optimize/server/remote_wsi.sh` | + `cmd_stats`, `cmd_smoke`; dispatch + usage updated |
| `tests/test_observability.py` (NEW) | 3 tests: state counts, absent→zeros, contention smoke (4×3 → 0 lock deaths) |

---

## 4. Verification evidence (all green)
| Gate | Result |
|------|--------|
| `tests/test_observability.py` | ✅ 3 passed |
| Full `pytest` | ✅ **179 passed** (176 + 3) |
| `bash -n remote_wsi.sh` | ✅ OK |
| `contention_smoke.py --workers 12 --trials 8` (local temp sqlite) | ✅ `lock_deaths=0 → OK` |

> At-scale behaviour (30-worker storm on the server's store) is the **Phase-D** use of `smoke` — that is
> exactly its job, run on the box right before the sweep.

---

## 5. Reverting Tier 3
```bash
git revert --no-edit <TIER3_COMMIT>     # removes study_stats/contention_smoke + the 2 launcher commands
```
Purely additive (new files + two new subcommands); reverting cannot affect runs or results.

## 6. Status & next
- ✅ Tier 3 done locally (live FAIL counts + structured JSON + pre-flight contention gate), 179 tests.
- ▶️ **Last local tier:** Tier 4 (CSV→Parquet loader, dataset registry, capacity-formula doc) — then Phase L
  is complete and we move to the **Phase D** server rollout (push → parity → `smoke` → provision Postgres +
  `WSH_STORAGE_URL` → `smoke` again → `run` with the watchdog).
