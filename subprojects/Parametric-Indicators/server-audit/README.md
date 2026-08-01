---
name: server-audit-archive
description: Work that existed only on the server, harvested 2026-07-31 under #94. A record, not live code.
type: archive
issue: 94
---

# `server-audit/` — harvested from the server, not live code

## What this is

Material that existed **only** on the AMD server and had never been committed anywhere. Recovered on
2026-07-31 while investigating why local and server keep drifting (#94).

**Nothing in here is live code.** It is a record of how a finished result was produced. Do not import
it, do not run it expecting it to work — these scripts carry server paths and server assumptions, and
that is a *property of the record*, not a defect to be fixed. `test_roots.py` exempts this whole tree
from the "no hardcoded absolute paths" sweep for exactly that reason: rewriting them would destroy the
evidence they exist to preserve.

## Why it mattered enough to keep 620 MB

`2026-07/` holds two workstreams that ran entirely on the server:

| dates | what |
|---|---|
| **2026-07-13** | the **end-of-day cap campaign** — `eod1_*.py`, `run_cap_campaign.sh`, per-instrument `caprun/*.log` |
| **2026-07-14** | the **precision-bug investigation** and the build of the **`best_*` champion set** — `build_best_set.py`, `best_snap.py`, `verify_best_deploy.py`, `measure_precise.py`, `decide_precise.py`, `ng_proof.py`, `ng_precision_probe.py` |

> **The champion set built by these scripts is the one currently deployed.** The champions themselves
> were committed. The code that produced and verified them was not. The deployed set was running while
> no longer being reproducible — losing that one machine would not have stopped trading, but it would
> have permanently ended anyone's ability to explain where those numbers came from.

It also contains **nine per-instrument WS-I reports** (ES, GC, SI, HG, CL, NG, RTY, YM, plus a
different run of `WS-I_RESULTS.md`) that were never pulled home. The reason is exact and worth
remembering: `remote_wsi.sh cmd_pull` names **one** filename. When each new instrument was onboarded,
its report was written on the server and the return path never learned about it. **Nine of ten reports
stranded by a one-line allow-list that stopped matching reality** — the same defect shape as the trial
budget (#2) and the "all 15 indicators" report header (#89).

## What was harvested, and what was not

Selection was by **content hash against the entire local repo**, so "unique" means genuinely nowhere
else, not merely at a different path.

| | files | size | kept |
|---|---:|---:|---|
| source written on the server | 146 | 3.9 MB | **yes** — 115 exist nowhere else |
| result JSON | 288 | 13.8 MB | **yes** |
| reports (`.md`) | 22 | 0.1 MB | **yes** |
| plots (`.png`) | 515 | 271 MB | **yes** — requested explicitly |
| run logs | 57 | 333 MB | **yes** — requested explicitly |
| data artifacts (`.csv`, `.npz`, `.db`) | 1,457 | 38.1 GB | no — belongs in a data root |
| archives (`.zip`) | 9 | 778 MB | no — repo policy never commits archives |

Plots and logs were included at the repo owner's explicit request. The cost is honest and worth stating
once: git keeps blobs forever, so this permanently adds ~620 MB to a public repository's history and
every future clone pays it.

Candidate list with per-file dates, sizes and status:
`../optimize/server/WSGI_HARVEST_CANDIDATES.tsv`

## The 31 "edits"

Of the 146 source files, 31 are **older versions of files that still exist** in the live tree. They are
kept as historical copies, not as anything to merge. If you want to know what changed, diff them
against the live path — but the live path is the truth.

## See also

- `docs/ISSUE-94-local-server-sync-root-cause.md` — the six root causes and the design
- `docs/ISSUE-94-wsgi-inventory.md` — the full inventory this harvest came from
