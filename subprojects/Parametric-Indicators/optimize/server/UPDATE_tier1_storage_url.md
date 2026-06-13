# Update Report — Scaling Tier 1 (local half): centralized storage URL, Postgres-ready

**Date:** 2026-06-12 · branch `dev` · `ACTION_PLAN_scaling_tiers.md` Phase L · **local-only (no server change)**
**Type:** infrastructure — **trade math untouched, results byte-identical**. No new dependency.
**Decision context:** `EXPLAINER_tier1_postgres_and_history.md`. **Default behaviour unchanged** (env-unset).

---

## 1. What changed (plain + professional)

**Professional.** The Optuna trial-store URL was hard-coded as a `sqlite:///…` literal in three places.
A new `optimize/storage.py` is now the **single source of truth**: `storage_url(sqlite_path)` returns
`WSH_STORAGE_URL` when set (e.g. a `postgresql://…` URL) else the per-TF SQLite path; `engine_kwargs(url)`
returns backend-appropriate SQLAlchemy kwargs (SQLite → 60 s busy_timeout; served RDB → connection pool).
`optimizer.py` (writer), `report_wsi.py` (reader), and `remote_wsi.sh` (launcher/pre-create/counts) all call
it. SQLite↔Postgres is now **one environment variable**, not a three-file edit.

**Baby.** The notebook's address used to be on three sticky notes; now it's on **one whiteboard** everybody
reads. To move the notebook to the big shared "office" (Postgres) you change **one word** (`WSH_STORAGE_URL`),
and the whole pipeline follows. With the word blank, **nothing changes** — same per-timeframe SQLite as before.

---

## 2. Before / after

| | Before | After |
|---|---|---|
| Store URL location | 3 hard-coded `sqlite:///` literals (optimizer / report / launcher) | 1 helper `optimize/storage.py` (`WSH_STORAGE_URL` or per-TF sqlite) |
| Switch to Postgres | edit 3 files in lockstep | set `WSH_STORAGE_URL=postgresql://…` (one var) |
| Behaviour, env **unset** | per-TF sqlite + WAL + 60 s busy_timeout | **identical** (per-TF sqlite + WAL + 60 s busy_timeout) |
| Engine kwargs | sqlite-only `connect_args timeout 60` | sqlite → same; postgres → `pool_size 32 / max_overflow 8` |

**The safety guarantee:** with `WSH_STORAGE_URL` unset the resolved URL is `sqlite:///…/wsh_<tf>.db` —
proven by test + a live optimizer smoke (created `t1smoke_4h` in `wsh_4h.db`, ran 2 trials). The actual
Postgres *server* is provisioned in Phase D on the box; this commit only adds the **switch**.

---

## 3. Code touched / links
| File | Change |
|------|--------|
| `optimize/storage.py` (NEW) | `storage_url()`, `is_sqlite()`, `engine_kwargs()` — the one source of truth |
| `optimize/optimizer.py` | import helper; `create_study` uses `storage_url(db_path)` + `engine_kwargs`; WAL/busy_timeout applied only when the URL is sqlite |
| `optimize/report_wsi.py` | `load_study` uses `storage_url(db_path)` (honours the env URL) |
| `optimize/server/remote_wsi.sh` | capture `WSH_STORAGE_URL`; forward via `REMOTE_ENV` + `launch.sh` export; pre-create one-liner + `cmd_counts` honour it |
| `tests/test_storage_url.py` (NEW) | 7 tests: unset→sqlite, set→pg, empty→sqlite, is_sqlite, engine_kwargs (sqlite/pg), real create_study |

Per-TF DB resolver (`_db_for`, Tier 0.3) + its legacy-shared fallback are **unchanged** — the helper sits
on top of whatever sqlite path `_db_for` resolves.

---

## 4. Verification evidence (all green)
| Gate | Result |
|------|--------|
| `py_compile` storage/optimizer/report_wsi + `bash -n remote_wsi.sh` | ✅ OK |
| `tests/test_storage_url.py` | ✅ 7 passed |
| Full `pytest` | ✅ **173 passed** (166 + 7) |
| Optimizer end-to-end smoke (env-unset, 2 trials, throwaway prefix) | ✅ created `t1smoke_4h` in per-TF sqlite, ran |
| env behaviour | ✅ unset → `sqlite:///…/wsh_4h.db`; set → `postgresql://…` |

(Engine/trade math is not on this path → `test_parity` / golden are trivially unaffected; full pytest still green.)

---

## 5. Reverting Tier 1 (local)
```bash
git revert --no-edit <TIER1_COMMIT>   # removes the helper + the 3 call-site edits
# functional fallback without reverting: simply leave WSH_STORAGE_URL unset ⇒ behaviour == pre-Tier-1
```

## 6. Status & next
- ✅ Tier 1 **local half** done: storage URL centralized, Postgres-ready, env-unset byte-identical, 173 tests.
- ▶️ **Remaining local (Phase L):** Tier 2 (watchdog/respawn + target-based idempotent runs), Tier 3
  (observability + contention smoke test), Tier 4 (Parquet/registry/capacity).
- ▶️ **Phase D (server, SSH now restored):** push → parity → provision Postgres container + set
  `WSH_STORAGE_URL` → contention smoke → launch sweep. History approach (#3) decided at D-time
  (default: fresh `wsh5` prefix).
