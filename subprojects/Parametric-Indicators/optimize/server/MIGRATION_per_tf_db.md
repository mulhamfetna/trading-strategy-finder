# Migration — Per-Timeframe Optuna DB Files (backward-compatible)

**Date:** 2026-06-11 · branch `dev`
**Author:** engineering
**Status:** PLANNED → (verification results appended after implementation, §7)
**Origin:** Step 3 of the bottleneck-prevention roadmap in `REPORT_system_scaling_study.md`, itself a
response to `INCIDENT_wsh4_sqlite_contention.md`.

> **Read this fully before touching anything.** This change alters where Optuna studies are stored. It is
> designed to be **backward-compatible** and is applied **local-only** — it is **NOT** pushed to the AMD
> server until the in-flight wsh4 results are pulled. A rollback snapshot commit is created *before* the
> change (see §6).

---

## 1. Why (rationale)

The `wsh4` incident: all 6 timeframe studies share **one** SQLite file (`optimize/studies/wsh.db`), so
~30 concurrent Optuna workers serialize on a single database write-lock → `database is locked` →
`StorageInternalError` → dead workers → 4h/1h under-sampled. Full post-mortem in
`INCIDENT_wsh4_sqlite_contention.md`.

Steps 1–2 (already applied) make this survivable: `catch=` keeps a lock blip from killing a worker, and
WAL + 60 s `busy_timeout` cut the contention. **Step 3 removes the contention structurally**: give each
timeframe its **own** DB file so the lock is split ~6× (≈5 writers per file instead of 30 on one).

---

## 2. Before-state (what exists today)

**Storage = one shared file**, referenced in three places (all pointing at `wsh.db`):

| File | Location | Role |
|------|----------|------|
| `optimize/optimizer.py` | `_DB = _STUDIES / "wsh.db"` (~line 68) | **writer** — `create_study(storage=…wsh.db)` |
| `optimize/report_wsi.py` | `_DB = _HERE/"studies"/"wsh.db"` (line 34); `load_study(... sqlite:///{_DB})` (line 76) | **reader** — builds WS-I report |
| `optimize/server/remote_wsi.sh` | `create_study(... 'sqlite:///optimize/studies/wsh.db' ...)` in `cmd_run`; `cmd_counts`; `cmd_pull` | **launcher / counts / pull** |

The server is **currently producing** `wsh.db` (single file) with the live wsh4 studies. Any reader must
keep being able to read that single file.

---

## 3. The change (what we will do)

1. **Writer (`optimizer.py`):** make `_DB` per-timeframe — `wsh_{tf_name}.db` — inside `run_study()`
   (where `tf_name` is known). The WAL/busy_timeout hardening (Step 2) applies per file.
2. **Reader (`report_wsi.py`):** for each timeframe, **prefer** `wsh_{tf}.db`; if it does not exist,
   **fall back to the shared `wsh.db`** and print a **loud `⚠️ FALLBACK` warning** naming the file used.
   This guarantees it still reads the server's single-file output, and never silently loses studies.
3. **Launcher (`remote_wsi.sh`):** `cmd_run` creates per-TF files; `cmd_counts` reads per-TF with the
   same shared-file fallback (loud warning); `cmd_pull` unchanged in shape (it runs the reader, which now
   handles both layouts).

**Backward-compatibility contract:** with no `wsh_<tf>.db` present (e.g. on the server, or on a fresh
clone of the existing local `wsh.db`), every reader transparently uses `wsh.db` and says so loudly. New
local runs create and use per-TF files.

---

## 4. Blast radius & non-interference

- **Local-only.** None of this is pushed to the server until after `./remote_wsi.sh pull` brings the
  wsh4 results home. The server keeps running its own (single-file) code, untouched.
- **The `pull` stays valid.** `pull` executes the *server's* current `report_wsi.py` against its single
  `wsh.db`. Even if the *local* `report_wsi.py` is changed, that has no effect on the server-side run.
- **The running sweep is unaffected** — its processes already loaded their code; local edits cannot reach
  them.

---

## 5. Verification plan (results in §7 after implementation)

1. `optimize/test_parity.py` → engine parity unchanged (`$7,735 / $3,670 / n=66`).
2. New-run smoke: a throwaway-prefix 2-trial run creates `wsh_4h.db` (per-TF file appears); study then
   deleted.
3. **Fallback test:** point the reader at a timeframe that has only the shared `wsh.db` (no per-TF file)
   and confirm it (a) reads it and (b) prints the loud `⚠️ FALLBACK` warning.
4. `pytest` suite green (88/88 baseline).

---

## 6. Rollback / reverse steps

A **snapshot commit** is created on `dev` *before* Step 3 (containing Steps 1–2 + these docs). It is the
known-good state to return to.

**To undo Step 3 only** (keep Steps 1–2):
```bash
cd /mnt/data/projects/trading
git revert --no-edit <STEP3_COMMIT_SHA>        # inverse commit, history preserved
# or, to discard the working-tree change before committing Step 3:
git checkout -- subprojects/Parametric-Indicators/optimize/optimizer.py \
                subprojects/Parametric-Indicators/optimize/report_wsi.py \
                subprojects/Parametric-Indicators/optimize/server/remote_wsi.sh
```

**To return entirely to the pre-change snapshot:**
```bash
git reset --hard <SNAPSHOT_COMMIT_SHA>         # hard reset dev to the rollback point
```

**Data side:** per-TF `wsh_<tf>.db` files are *additive* — deleting them and relying on the shared
`wsh.db` is always safe; no existing study is moved or rewritten by this change.

> SHAs are filled in §7 once the commits exist.

---

## 7. After-implementation — verification results & SHAs

*(populated after the edits + tests run)*
