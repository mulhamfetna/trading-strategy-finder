# Update Report — Phase D: server rollout + PostgreSQL cutover (system update, no sweep)

**Date:** 2026-06-12 · branch `dev` · `ACTION_PLAN_scaling_tiers.md` Phase D
**Scope:** deploy the hardened optimizer (Tiers 0–4 + Axis-A/B engine speedups) to the AMD server, stand up
PostgreSQL, **migrate ALL trial history into it**, and prove the contention is fixed. **No sweep launched** —
per the directive, the next run is a *fresh clean run on updated data*, triggered later.

---

## 1. What was done (in order, each verified)

| Step | Action | Result |
|------|--------|--------|
| **D1 push** | `remote_wsi.sh push` — rsync hardened code + data (studies/results excluded) | ✅ done |
| **D2 parity** | `remote_wsi.sh parity` — server-side byte-identical check | ✅ `$7,735 / $3,670 / n=66` |
| **D3 Postgres** | docker `postgres:16` container `wsh-pg`, localhost-only `127.0.0.1:55432`, persistent volume `wsh_pg`, random pw in `$WSI/pg.env` (chmod 600); `pip install psycopg2-binary` in the venv | ✅ ready in 2 s; optuna create/read/delete verified |
| **D4 migrate** | `migrate_to_pg.py` — `copy_study` all 6 `wsh4_*` SQLite → Postgres | ✅ **6/6 copied** |
| **D5 verify** | `study_stats` from Postgres + `contention_smoke 30×20` on Postgres | ✅ counts match; **0 lock deaths** |
| **D6 sweep** | — | ⏸️ **intentionally not run** (fresh-data run is later) |

### Migrated trial counts (now in Postgres)
| TF | total | complete | pruned | FAIL |
|----|------:|---------:|-------:|-----:|
| 4h | 6,100 | 5,483 | 614 | 3 |
| 2h | 5,000 | 4,476 | 524 | 0 |
| 1h | 5,553 | 5,017 | 533 | 2 |
| 15m | 3,507 | 3,294 | 211 | 2 |
| 5m | 5,004 | 4,565 | 439 | 0 |
| 2m | 4,256 | 4,037 | 218 | 1 |

Source was the **legacy shared `wsh.db` (405 MB)** — the per-TF split was never deployed to the server, so
`migrate_to_pg` resolved the studies from the shared file (its built-in fallback). `wsh.db` is **left intact**
on the server as a read-only backup.

---

## 2. The proof the incident can't recur
The wsh4 failure was 30 concurrent writers on one SQLite file → `database is locked` → dead workers.
**`contention_smoke --workers 30 --trials 20` on Postgres → `lock_deaths=0`.** Postgres MVCC removes the
single-writer lock entirely; combined with Tier-2 watchdog/respawn (a dead worker is replaced) and Tier-3
`stats` (a FAIL spike is visible in one poll), the capacity-loss mode that under-sampled 4h/1h is closed.

---

## 3. How the store is selected (one knob, secret stays on the server)
`remote_wsi.sh` resolves the Optuna store in this order: **(1)** a local `WSH_STORAGE_URL` (override) →
**(2)** the server's `$WSI/pg.env` (Postgres, sourced on the box) → **(3)** per-TF SQLite. Verified live:
`remote_wsi.sh stats` with no local env returned the **Postgres** counts. So `run`/`stats`/`smoke`/`counts`/
`pull` all use Postgres automatically; the password never leaves the server.

---

## 4. The future fresh run (your later call — NOT done now)
Because the next run is on **updated data**, it must use a **new study prefix** (do not append to the
old-data `wsh4_*`). On the server, after refreshing the data + `remote_wsi.sh push`:
```bash
# edit PREFIX="wsh5" in remote_wsi.sh (new regime on updated data), then:
./remote_wsi.sh smoke 30 20        # pre-flight: expect 0 lock deaths (now on Postgres)
./remote_wsi.sh run 5000           # target 5000 trials/TF, watchdog/respawn, idempotent, on Postgres
./remote_wsi.sh stats              # watch COMPLETE/RUNNING/FAIL
./remote_wsi.sh pull               # results + report when targets hit
```
The migrated `wsh4_*` history stays in Postgres for analysis/comparison.

---

## 5. Reverting / rollback
- **Drop Postgres, return to SQLite:** `rm $WSI/pg.env` (store selection falls back to per-TF sqlite);
  `docker rm -f wsh-pg` (data persists in volume `wsh_pg`; `docker volume rm wsh_pg` to wipe).
- **Driver change** (`pg.env` auto-source): `git revert` the remote_wsi.sh commit — runs revert to
  forwarding only the local `WSH_STORAGE_URL`.
- Old `wsh.db` (SQLite) remains the untouched historical record.

---

## 6. Status
- ✅ **System updated:** hardened code live on the server; PostgreSQL up with **all 6 studies migrated**;
  contention fixed (30-writer smoke = 0 lock deaths); store auto-selected via `pg.env`.
- ⏸️ **No sweep run** — fresh run on updated data is the next, user-triggered step (new `wsh5` prefix).
- Local repo: Phase L (Tiers 1–4) + `migrate_to_pg.py` committed & pushed; this doc + the `pg.env`
  auto-source driver edit committed here.
