# Update Report — Scaling Tier 2: worker watchdog/respawn + target-based idempotent runs

**Date:** 2026-06-12 · branch `dev` · `ACTION_PLAN_scaling_tiers.md` Phase L · **local-only (no server change)**
**Type:** orchestration/resilience — **trade math untouched.** The launcher logic is server-side bash;
its complex part is moved into a locally-tested Python helper so it can be verified without the box.

---

## 1. What changed (plain + professional)

**Professional.** Two resilience gaps from the wsh4 incident are closed:
- **Target-based, idempotent runs (2.2):** a run now means *"reach N **total** trials for this study"*, not
  *"add N more."* The launcher computes `remaining = TARGET − completed` and only runs the deficit, so
  re-invoking a run that already hit target does **nothing**, and a top-up lands exactly on target.
- **Watchdog/respawn (2.1):** each worker is a `run_worker` loop that re-checks the completed count and
  **re-runs the optimizer until the study reaches TARGET** — so a worker that dies mid-run (the exact way 4h
  and 1h fell short) is automatically replaced and the deficit is topped up. `|| true` means a crashed
  optimizer just loops instead of leaving the study short.

The count logic lives in a new **locally-tested** `optimize/trial_count.py` (the launcher shells out to it),
keeping the untestable-on-server bash trivial.

**Baby.** Before: we told each worker "do 5,000 laps" and walked away — if someone tripped, the race
finished short and nobody noticed. Now: we say "the track must reach 5,000 laps total"; a referee
(`run_worker`) keeps checking the lap board and sends runners back out until the board hits 5,000. If a
runner trips, another is sent to cover the missing laps. Ask for 5,000 when it's already 5,000 → everyone
just goes home (nothing re-run).

---

## 2. How it works (the launcher, post-change)

```
TARGET = <trials/TF>                      # the number to REACH (was: trials to ADD)
run_worker(tf, w):                        # one per worker slot
  loop:
    done = trial_count.completed(prefix, tf)        # honours WSH_STORAGE_URL / per-TF sqlite
    rem  = TARGET - done;  if rem <= 0: stop
    per  = ceil(rem / w)                             # this worker's slice of the deficit
    run optimizer.py tf --trials per   (|| true)     # a crash just loops back
spawn w × run_worker per TF;  wait                   # launcher (setsid) stays alive until all reach TARGET
```

- **Idempotent:** `rem ≤ 0 ⇒ stop` → re-runs are exact and safe.
- **Self-healing:** any worker death → next loop sees `done < TARGET` → respawns to cover the gap.
- **No oversubscribe:** the existing `pkill optimize/optimizer.py` + the per-TF `WORKERS` map are unchanged;
  `wait` keeps the detached session leader alive so children aren't orphaned/SIGHUP'd.

---

## 3. Code touched / links
| File | Change |
|------|--------|
| `optimize/trial_count.py` (NEW) | `completed(prefix, tf)` → count of COMPLETED trials (0 if absent), honouring the Tier-1 storage URL with a quiet per-TF/shared resolver; CLI `python3 optimize/trial_count.py <tf> --prefix wsh4` |
| `optimize/server/remote_wsi.sh` | `cmd_run`: `TOTAL`→`TARGET`; added `run_worker` watchdog loop; spawn `run_worker` per slot; `wait`; run-log says "target … (idempotent, watchdog/respawn)" |
| `tests/test_trial_count.py` (NEW) | 3 tests: counts via env URL, missing study → 0, CLI path |

`optimizer.py` is **unchanged** — `--trials` still means "run this many now"; the watchdog supplies the
right number each iteration. The Tier-0.3 per-TF resolver + Tier-1 URL helper are reused, not duplicated.

---

## 4. Verification evidence (all green)
| Gate | Result |
|------|--------|
| `tests/test_trial_count.py` | ✅ 3 passed |
| Full `pytest` | ✅ **176 passed** (173 + 3) |
| `bash -n remote_wsi.sh` (outer) | ✅ OK |
| **Generated `launch.sh`** (heredoc body extracted, unescaped, `bash -n`) | ✅ OK — run_worker/arith/spawn/`wait` well-formed |
| `trial_count` CLI smoke (missing study → 0) | ✅ `0` |

> Real end-to-end behaviour (respawn under load, target convergence with ~30 workers) is validated by the
> **Phase-D contention smoke test on the server** — it cannot be exercised locally without the worker fleet.

---

## 5. Reverting Tier 2
```bash
git revert --no-edit <TIER2_COMMIT>     # restores the fixed-"add N" launcher; removes trial_count + watchdog
```
The launcher change is isolated to `cmd_run`; `trial_count.py` is additive (nothing else imports it yet).

## 6. Status & next
- ✅ Tier 2 done locally (watchdog/respawn + target-based idempotent runs), 176 tests.
- ▶️ **Next (Phase L):** Tier 3 (observability — live COMPLETE/RUNNING/**FAIL** counts, structured log +
  alert, the pre-flight contention smoke test) → Tier 4 (Parquet/registry/capacity).
