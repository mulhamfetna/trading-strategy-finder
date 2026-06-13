# Update Report — Scaling Tier 4: data layer (opt-in Parquet, dataset registry, capacity formula)

**Date:** 2026-06-12 · branch `dev` · `ACTION_PLAN_scaling_tiers.md` Phase L · **local-only** · **completes Phase L**
**Type:** data layer — **default path byte-identical** (golden 4h/2h/1h MATCH). pyarrow 24.0.0 present.

---

## 1. What changed (plain + professional)

**Professional.**
- **4.1 Opt-in Parquet** — `loader.load_data` reads a `<csv>.parquet` sibling **only** when `WSH_USE_PARQUET`
  is set AND the sibling exists; otherwise the CSV path runs **unchanged**. `optimize/to_parquet.py` writes
  each sibling from the EXACT post-load CSV frame, so the Parquet load is **byte-identical** (float64 +
  datetime64 preserved) — just faster/smaller for the instruments-×-windows growth.
- **4.2 Dataset registry** — `optimize/dataset_registry.py` records `path + sha256 + bytes + mtime` per
  input file, so any run can stamp the exact data version it consumed (reproducibility).
- **4.3 Capacity formula** — documented at the `WORKERS` map in `remote_wsi.sh`: `workers ≈ cores − 2`;
  SQLite ~5 writers/DB-file (6 per-TF files ⇒ ~30); **PostgreSQL lifts the write-lock cap (MVCC)** so scale
  up there, gated by the Tier-3 `smoke`.

**Baby.** (4.1) We can save the data in a faster file format, but only if you flip a switch — and we proved
the fast file gives the **exact same numbers** as the old one, so nothing can drift. (4.2) Every run writes
down a fingerprint of the data it used, so results are always traceable. (4.3) We wrote down the rule for
"how many workers is safe," and noted Postgres lets you use many more.

---

## 2. Before / after
| | Before | After |
|---|---|---|
| Data load | CSV only | CSV by default; **opt-in Parquet** (env + sibling) — byte-identical |
| Reproducibility | implicit (file on disk) | optional registry: sha256 + size + mtime per dataset |
| Worker sizing | a comment ("sum ≈ 30") | + explicit capacity formula incl. the Postgres lift |
| Default behaviour | — | **unchanged** (golden 4h/2h/1h MATCH; env-unset CSV path identical) |

---

## 3. Code touched / links
| File | Change |
|------|--------|
| `loader.py` | `+import os`; opt-in `<csv>.parquet` branch gated on `WSH_USE_PARQUET`; CSV path unchanged |
| `optimize/to_parquet.py` (NEW) | converter: post-load CSV frame → `<csv>.parquet` (parquet-read forced off while writing) |
| `optimize/dataset_registry.py` (NEW) | `file_sha256`, `describe`, `register` + CLI |
| `optimize/server/remote_wsi.sh` | capacity-formula doc at the `WORKERS` map |
| `tests/test_data_layer.py` (NEW) | 4 tests: Parquet load == CSV (exact, incl. dtypes); disabled-by-default; registry sha256 == hashlib; registry JSON |

---

## 4. Verification evidence (all green)
| Gate | Result |
|------|--------|
| `tests/test_data_layer.py` | ✅ 4 passed |
| Full `pytest` | ✅ **183 passed** (179 + 4) |
| `perf/check_golden.py 4h 2h 1h` (loader feeds golden) | ✅ ALL MATCH — default byte-identical |
| `py_compile` + `bash -n` | ✅ OK |

---

## 5. Reverting Tier 4
```bash
git revert --no-edit <TIER4_COMMIT>     # removes the opt-in parquet branch + converter/registry + doc
# functional disable without reverting: leave WSH_USE_PARQUET unset ⇒ CSV path (already the default)
```

## 6. Status — Phase L COMPLETE
- ✅ Tier 1 (storage URL central, Postgres-ready) · ✅ Tier 2 (watchdog/respawn + target-based) ·
  ✅ Tier 3 (observability + contention smoke) · ✅ Tier 4 (opt-in Parquet + registry + capacity).
- All local, parity-locked, **183 tests**, golden byte-identical, each tier independently revertible.
- ▶️ **Phase D (server rollout, SSH restored)** — needs your go + the history decision (#3): push → parity →
  `smoke` → provision Postgres + `WSH_STORAGE_URL` → `smoke` → `run` (target trials/TF) → `stats` watch → `pull`.
