# `wshgap` — the 2026-07-21/22 honest-fill re-optimization (ARCHIVED, **do not adopt**)

Issue #2. These files were recovered on **2026-07-29** from the server, where they had survived only as
**untracked** files in `~/Mulham/code/.worktrees/fundamental` and `~/Mulham/fa-m1/`. Nothing here was ever
committed, and the Optuna studies themselves are gone (0 of 238 studies in `wsh-pg` match `%gap%`), so
this directory is now the **only** record of that run. That is exactly the failure the
"LOCAL = source of truth" rule exists to prevent: for a week the issue read *"Running now on the server"*
while the only evidence lived on a box nobody was reading.

## What the run was

Warm-started re-optimization of **NQ + GC × {4h, 2h, 1h, 15m, 5m, 2m}** = 12 studies under gap-aware
fills (`gap_fills=True`, `--ind-1min`), prefix `wshgap`. It completed 12/12 with no failures, and its
findings were written up in `docs/superpowers/GAP-03-reoptimization-before-after.md`.

## Why its verdicts must not be reused

**1 — It was warm-started from a superseded champion set (the serious one).**
`optimize/optimizer.py: warm_start_seeds()` read `wsh4_champions_full*.json`, but the deployed set had
moved to `best_*` eight days earlier (`DEFAULT_CHAMPION_SET = "best"`, commit 4585648, 2026-07-14).
Optuna's warm start guarantees the returned front is **≥ its seed** — so the guarantee held against
`wsh4`, a set that was already retired. Fixed 2026-07-29; see `optimize/test_warm_start_seed_set.py`.

**2 — Its before/after table used that same wrong set as "deployed".**
`full_compare.py` loads `wsh4_champions_full*.json` as `dep`. GAP-03 therefore reported
**+$52,443 full / +$35,475 2026-OOS "vs deployed"**. Against the set that is actually deployed
(`best_*`), the same 12 slots come out **+$94,522 full but −$12,832 OOS** — see `best_vs_wsh4.txt`,
which was produced on 2026-07-22 at 16:05 (*after* the adoption) and then never acted on.

The three "winners" measured against the real deployed champions:

| slot | best_ OOS | wshgap OOS | Δ |
|---|---:|---:|---:|
| NQ 1h | 27,203 | 38,008 | **+10,805** |
| GC 15m | 37,897 | 40,123 | **+2,226** |
| NQ 2h | 40,745 | 26,728 | **−14,017** |
| **net** | | | **−986** |

So the adopted trio is roughly a wash out-of-sample, and **NQ 2h is materially worse** than what we
already run. GAP-03's headline gain was an artifact of the baseline, not an edge.

**3 — Params are persisted at 4 decimal places (provenance only, here).**
The precision fix (`_sig`, 12 significant digits, commit 090d24b) was **not** in the
`fundamental-analysis` worktree, so these were extracted by the old `round(x, 4)` path — the bug that
flipped NG 5m's sign. **For NQ and GC specifically this is not materially distorting**: the smallest
stop in these files is GC 2m `sl_soft=2.2426`, still 5 significant figures (~0.002% distortion). It
matters for provenance and would be fatal if this run were ever extended to NG or HG.

## Where the adoption went

Commit `105a2da` wrote the trio into `optimize/results/wsh4_champions_full{,_GC}.json` — the **retired**
set, not the deployed `best_*`. Consequence: **the deployed book was never actually changed**, so no
live champion was harmed by any of the above. `wsh4_*` is not a registered champion set
(`optimize/test_champion_sets.py` forbids the prefix), but note `presets.py` still reads it directly for
the dashboard's "wsh4 regime" preset dropdown, which bypasses that registry check.

Golden baselines for 1h/2h were re-captured to the adopted values in `96eb8de`, so the gate is
self-consistent with `wsh4` — not with the deployed set.

## Files

| file | what it is |
|---|---|
| `wshgap_champions_full{,_GC}.json` | the 12 re-optimized champions (4-dp, see above) |
| `extract_wshgap.sh` / `.txt` | how they were extracted from the Optuna studies |
| `full_compare.py` / `.json` | the before/after that fed GAP-03 — **baseline is `wsh4`** |
| `best_vs_wsh4.py` / `.txt` | the true-baseline comparison that caught the error |
| `STATUS.txt` | run status at completion |

## What supersedes this

A re-run seeded from `best_*` on the current engine. The engine changed materially after this run
(#62 indicator acceleration, #74 cross-series measurement, #75 cross-series wiring — which changed
cross-series vote behaviour outright), so these numbers would not reproduce today even with correct
seeding.

> Note: the two run logs are committed as `.txt`, not `.log` — the repo gitignores `*.log`, and
> being untracked is precisely how this whole run went missing for a week.
