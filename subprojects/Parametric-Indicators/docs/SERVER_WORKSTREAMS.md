# Server layout — one workstream, one branch, one section

Two agents work this box in parallel. Before this, both wrote into a single 40 GB directory
(`~/Mulham/wsg-i`) that had **no git remote at all** — it was an rsync copy stranded on a stale `master`
with 61 modified and 509 untracked files. Fixes survived there only as loose `scp`'d files, and a single
`git checkout` would have silently reverted them. That is how a champion set ended up existing *only* on
this disk while version control held a corrupted one.

The rule now: **what is deployed is what is committed.**

```
~/Mulham/
  code/                          git clone of origin (THE source of truth for code)
    └─ branch: dev               ← workstream: timecap-eod    ← the dashboard runs from HERE
    .worktrees/
      └─ fundamental/            ← workstream: fundamental-analysis (its own branch)

  runs/
    ├─ timecap-eod/              outputs of the dev workstream
    │    scripts/  metrics/  logs/  bundles/  snapshots/
    └─ fundamental/              outputs of the FA workstream
         scripts/  metrics/  logs/  reports/

  shared/
    ├─ data      -> wsg-i/data          market data (84 MB)
    └─ data_1s   -> data_2010_1s        1-second bars (33 GB) — symlinked, NEVER duplicated

  wsg-i/                         LEGACY. Frozen. Do not add to it. Still holds pg.env + the real data dir.
```

## Which is which

| workstream | branch | code | outputs |
|---|---|---|---|
| **timecap-eod** | `dev` | `~/Mulham/code` | `~/Mulham/runs/timecap-eod` |
| **fundamental-analysis** | `fundamental-analysis` | `~/Mulham/code/.worktrees/fundamental` | `~/Mulham/runs/fundamental` |

## Rules

1. **Never edit code in `wsg-i/`.** It is not connected to git. Work in your worktree, commit, push, pull.
2. **Never write outputs into another workstream's `runs/` section.** That is how they got mixed.
3. **The dashboard serves `~/Mulham/code` on `dev`.** To deploy a change: commit → push → `git pull` in
   `~/Mulham/code` → `dash.sh refresh`. If it is not committed, it is not deployed.
4. **Data is shared and symlinked.** Never copy it — the 1-second set alone is 33 GB.
5. **Clear `/tmp/wsh_l1_cache` after any change that can affect P/L.** The cache key does not include the
   point value or the strategy params, so a stale entry will happily serve the previous answer.

## Champion sets (dashboard dropdown)

| set | files | what it is |
|---|---|---|
| `best` | `best_*` | **DEPLOYED** — best of three candidates per slot, decided on the held-out 2026 year |
| `incumbent` | `cap1p_*` | the incumbents, re-extracted at full precision |
| `eod` | `eod1p_*` | the forced-end-of-day campaign, whole |

`results/superseded-4dp/` holds the retired `wsh4_*` files. They were persisted with `round(x, 4)` — four
DECIMAL places. Natural gas trades at $3.57, so its stop of 0.0008 kept **one significant digit**; on NG 5m
that flipped +$38,079 into −$1,714 and got 10 of the 54 head-to-head verdicts wrong. `test_champion_sets.py`
fails the build if any set is pointed back at them.
