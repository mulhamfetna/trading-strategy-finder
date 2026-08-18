---
name: issue-94-wsgi-inventory
description: What is actually in the 578 uncommitted files in ~/Mulham/wsg-i — 2,757 files unique to the server, of which 456 (17.8 MB) are worth keeping and the rest is data.
type: inventory
status: awaiting your decision
issue: 94
date: 2026-07-31
---

# `~/Mulham/wsg-i` — what is actually in there

You asked to see the inventory before deciding. Here it is, by content hash rather than by filename, so
"unique to the server" means **genuinely not anywhere in the local repo**, not merely "sitting at a
different path".

## The headline

| | files | size |
|---|---:|---:|
| files touched by `git status` (expanded from 578 entries, incl. directories) | 5,028 | |
| already present locally, **byte-identical** | 2,271 | |
| **unique to the server** | **2,757** | **39.5 GB** |
| ...of which **worth keeping** | **456** | **17.8 MB** |
| ...of which data, archives, plots and giant logs | 2,301 | 39.5 GB |

**The thing to notice: 39.5 GB looks alarming and is not the problem. 17.8 MB is the problem.** Almost
all the bulk is instrument data and bundle archives that should never be in git anyway. What matters is
a small pile of source and results that exists in exactly one place, on one machine, with no remote.

## What is worth keeping — 456 files, 17.8 MB

| category | files | size | what it is |
|---|---:|---:|---|
| **source written on the server** | **146** | 3.9 MB | of these, **115 exist nowhere else**; 31 are edits of files we do have |
| result JSON | 288 | 13.8 MB | champion sets, verification output, per-instrument results |
| reports (`.md`) | 22 | 0.1 MB | including **9 per-instrument WS-I reports that were never pulled** |

Full list with dates, sizes and per-file status:
`subprojects/Parametric-Indicators/optimize/server/WSGI_HARVEST_CANDIDATES.tsv`

### The 115 scripts that exist nowhere else

They are not miscellaneous. Read by date they are **one coherent workstream**:

| dates | scripts | what it is |
|---|---|---|
| 2026-07-13 | `eod1_package.py`, `eod1_verify.py`, `eod1_decide.py`, `eod1_snap.py`, `eod1_uipass.py`, `run_eod1_chain.sh`, `run_cap_campaign.sh`, … | the **end-of-day cap campaign** |
| 2026-07-14 | `build_best_set.py`, `best_snap.py`, `best_package.py`, `verify_best_deploy.py`, `build_best_precise.py`, `measure_precise.py`, `decide_precise.py`, `ng_proof.py`, `ng_precision_probe.py`, … | the **precision-bug investigation and the build of the `best_*` champion set** |

> **This is the chain that built and verified the champion set that is currently deployed.** The
> champions themselves are committed; the code that produced and checked them is not. If this machine
> were lost tomorrow, the deployed set would still run — and would no longer be reproducible.

### The 9 stranded reports — RC-5, quantified

```
WS-I_RESULTS_ES.md   WS-I_RESULTS_GC.md   WS-I_RESULTS_SI.md
WS-I_RESULTS_HG.md   WS-I_RESULTS_CL.md   WS-I_RESULTS_NG.md
WS-I_RESULTS_RTY.md  WS-I_RESULTS_YM.md   WS-I_RESULTS.md (a different run to the tracked one)
```

`remote_wsi.sh cmd_pull` pulls exactly **one** filename: `WS-I_RESULTS.md`. When each new instrument
was onboarded, its report was written on the server and the return path never learned about it.
**Nine of ten reports stranded, by a one-line allow-list that stopped matching reality** — the same
defect shape as the trial budget and the "all 15 indicators" header.

## What is NOT worth keeping

| category | files | size | why |
|---|---:|---:|---|
| data artifacts (`.csv`, `.npz`, `.db`) | 1,457 | 38.1 GB | instrument data and study databases — belongs in a data root, not in git |
| archives (`.zip`) | 9 | 778 MB | repo policy: never commit archives |
| plots (`.png`) | 515 | 271 MB | regenerable from the results JSON |
| run logs | 79 | 333 MB | `caprun/*.log` are ~7 MB each; the *conclusions* are in the reports |

## My recommendation

1. **Harvest the 456 files (17.8 MB)** into `subprojects/Parametric-Indicators/server-audit/2026-07/`,
   preserving their server paths, with a README explaining that this is rescued material and that the
   31 "edits" are historical copies rather than current source.
2. **Then demote `wsg-i` to a pure data directory** — keep `ALL_STOCKS` and `Full_Canldes_Data`, remove
   its `.git`. That removes a whole code-drift source; the data it holds is exactly what the test suite
   needs and stays where it is.
3. Leave the 39.5 GB of data, archives, plots and logs where they are. Nothing is deleted by this plan.

**Why not push it as a branch instead:** its history is a server-local audit trail with no relationship
to `dev`, and keeping it alive keeps a second code repo — which is the drift source we are trying to
remove. Harvesting the material preserves everything that carries information; the *commit history* of
a repo nobody can push to does not.

## What I need from you

Confirm the harvest scope. Default if you say nothing specific: **the 456 files above** — all 146
source, all 22 reports, all 288 result JSON. Say so if you also want the `caprun` logs (333 MB) or the
plots (271 MB), and I will include them; I would rather ask than quietly drop a third of a gigabyte.
