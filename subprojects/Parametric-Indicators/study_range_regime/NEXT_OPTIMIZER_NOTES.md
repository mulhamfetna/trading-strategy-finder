# Notes for the NEXT full optimizer run (wsh5) — carry these forward

> # ⚠️ **THE FULL-DATA OPTIMIZER RUNS 4h ONLY (2026-06-15 directive)** ⚠️
> **Every full-data optimizer sweep — this one and all future ones — optimizes ONLY the 4h timeframe and
> CONCENTRATES ALL workers on it. The other timeframes (2h/1h/15m/5m/2m) are HELD (not run) for time-saving
> and study focus.** This is enforced in `optimize/server/remote_wsi.sh` (`TFS=(4h)`, `WORKERS[4h]=30`).
> **This restriction applies ONLY to the production full-data optimizer.** Parity tests, smoke tests, golden
> byte-match, and ALL engine/system development STILL consider ALL timeframes — nothing else is narrowed.
> To resume the full all-TF sweep later: set `TFS=("${TFS_ALL[@]}")` in remote_wsi.sh and restore per-TF WORKERS.



Post-`wsh4` edits that change what a fresh optimizer run should search. The deployed champion (`wsh4`,
4h decision frame / 1-min indicators) is **shared-SL/TP, all-indicators-on**; these notes widen the space.

## 1. Split long/short SL/TP is now searchable (Q3 / E2)
- New optimizer inputs available: `long_sl_soft`, `long_sl_hard`, `long_tp`, `short_sl_soft`, `short_sl_hard`,
  `short_tp` (per-side; hard = soft + delta, same per-TF bounds as the shared path).
- **Enable with:** `optimize.optimizer.run(tf, ..., split_sltp=True, study_prefix="wsh5")`.
- **Default is OFF** (`split_sltp=False`) ⇒ shared SL/TP ⇒ identical to wsh4. The wsh4 champion used
  long==short; turning this on lets buys and sells get their own stops/targets (user's point 5).
- Plumbing is golden- + fast-parity-locked (see `UPDATE_E2_split_threading.md`).

## 2. Use a NEW study prefix
Per standing rule: fresh runs use a NEW prefix (**`wsh5`**), never reuse `wsh4`. Per-TF Postgres DBs on the
AMD server (`wsh-pg`, creds in `$WSI/pg.env`).

## 2b. wsh5 IS RUNNING (launched 2026-06-15 19:39, AMD server)
The split-SL/TP run is live: `wsh5_{4h,2h,1h,15m,5m,2m}` on Postgres, `--ind-1min --split-sltp`, target 5000
trials/TF, detached w/ watchdog. Monitor `bash optimize/server/remote_wsi.sh status`; when done `pull` and
compare the split champion vs the wsh4 shared champion on OOS return/DD (adopt only if it OOS-dominates).
**This run was launched BEFORE the new vote indicators below existed — so it does NOT search them.**

## 3. NOW-WIRED vote indicators (available for a SUBSEQUENT run, not in the live wsh5)
- **IFVG, breaker, CISD** are now registered vote-source indicators (`indicators/library.py` keys `ifvg`,
  `breaker`, `cisd`) ⇒ a future optimizer run will include `en_ifvg/en_breaker/en_cisd` in the search space
  automatically (golden 6/6 unaffected; champion preset enumerates its own indicators).
- Still NOT wired: the regime study's trend-follow·pinned·widen-only TP rule, and OB/breaker entry-placement
  policy (immediate/mid/far/wait) — see `PLAN_entry_rules.md` (Q6 steps 2–3, task #218).

## 4. Adoption gate (unchanged)
Only swap the deployed champion if the new (split / wider) search OOS-dominates on return/DD under the
pre-registered walk-forward rule. Fixed champion stays deployed until then.
