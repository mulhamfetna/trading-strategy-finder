---
name: workstream-pin-2026-08-03
description: "PIN of the optimizer/search workstream as of 2026-08-03 — complete state, every issue with its verdict, every default and why it is what it is, every trap, and the exact open questions. Written so this workstream can be resumed cold, or left alone safely while another workstream runs beside it."
type: pin
date: 2026-08-03
status: PINNED
---

# WORKSTREAM PIN — optimizer / search — 2026-08-03

**This workstream is pinned, not finished.** Nothing below is in flight. No run is executing, no branch
is half-merged, no experiment is awaiting a result.

**Read `docs/research-103/00-SYNTHESIS.md` first if you only read one thing.**

---

## 0. State at the moment of pinning

| | |
|---|---|
| branch | `dev` @ `8c10fd0` |
| `dev` vs `main` | **116 commits ahead** — main is stale by design (PR-only, deliberate) |
| tree | clean (one untracked dir `code/`, pre-existing, not ours) |
| server suite | **1,221 passed / 1 skipped / 0 failed** (`amd`, correct data root) |
| local suite | 1,197 / 14 skipped / 0 failed (10 extra skips = numba absent locally) |
| open issues | 20 |
| closed this session | #88, #94, #95, #96, #97, #99, #101 |
| opened this session | #102, #103, #104, #105, #106, #107, #108 |
| branches parked | `research/arch-a-one-stage-mixed`, `research/arch-b-two-stage-specialist` — **created, pushed, EMPTY of work** |
| worktrees | `legacy18/` — nested worktree, branch `research/legacy-18-baseline` (a SEPARATE workstream; see `legacy18/START-HERE.md`) |

**No compute is running on the server.** Run scripts left in place at `~/Mulham/run88*.sh`,
`~/Mulham/run101ab.sh`, outputs under `~/Mulham/runs/issue{88,88r2,88r3,88r4,88r5,101}/`. All results
have been scp'd back and committed under `optimize/results/issue*/`.

---

## 1. The headline: what this workstream concluded

The workstream started from *"we grew the indicator library 18 → 165 and the search keeps breaking"*.
It ends with a different diagnosis than it began with.

> **The search was never the binding constraint.**
>
> Identifying *which* 7 of 165 indicators matter needs ~79 observations (Wainwright's sharp threshold);
> we have **2,119** — a 27× margin. **Validating** the winner needs, at 4,000 trials, **13.2 years** of
> history (Bailey et al. Minimum Backtest Length); we have **1.38**. With 1.38 years the supported
> number of independent trials is **≈ 5**. We run **4,000–47,100**.
>
> **A better optimiser makes this worse** — it raises the in-sample maximum found per unit of budget,
> which is exactly the quantity that is spurious at this sample size.

That explains the workstream's own record: **1 of 8 pre-registered criteria passed**, and the one pass
evaporated when a condition changed.

**Consequence: #87 (only 1.38 years of price history) is now the highest-value asset in the project,
ahead of any optimiser work.**

---

## 2. Complete issue ledger with verdicts

### Closed with a verdict this session

| # | title | verdict |
|---|---|---|
| **#88** | MAP-Elites archive 9× too large for its budget | **Shape defect real and fixed** (1,494 → 81 niches, registry-independent). Benefit **scoped to warm-started search** — 8/8 warm (+23.1%), failed cold twice (3/8, then 5/8 on fresh seeds). 5 rounds, 4 failed criteria, 1 narrow pass. |
| **#101** | 70% of evaluations never reach the archive | **Measured and accepted as a property of the space.** The archive IS the population (~30 genomes). Tripling it via stepping stones **FAILED 1/8 — the peak got worse**. Widening the parent pool trades peak quality for coverage. `--stepping-stones` kept, OFF. |
| **#94** | repo root hardcoded in 49 places | 6 root causes, one symptom. `roots.py` shipped. **A path from `__file__` is right for CODE, wrong for DATA.** |
| **#95** | SMC excluded from committee on a stale cost | Exclusion **removed** — it was 4.4% of a trial, not 90%; 4 of 6 were never expensive. **Whether SMC helps is still UNKNOWN** → #98. |
| **#96** | contributor search unaffordable at its own budget | `--contrib-only` shipped → #100 to prove it. |
| **#97/#99** | compress the 460-dim indicator layer | **Do not adopt.** Conditional parameter drawing: median trial LOST money vs the rectangular arm making it; 3.4× fewer trials scored. |
| **#89** | constants calibrated for registry=18 | 4 call sites of one 8× budget defect. Playbook rules S1–S7. |

### Open, with why

| # | title | status |
|---|---|---|
| **#87** | history is only 1.38 years | ⭐ **Now the top-priority issue in the project.** #103 shows every other limit is downstream of it. |
| **#103** | is this space searchable at all? | **Research complete**, 6 documents, all 6 questions answered. Children #104–#108 spawned. |
| #104 | does Stage A rank by the wrong quantity? | Specified, pre-registered, **not run**. Gates the two architecture branches. |
| #105 | measure EFFECTIVE independent trials | ⭐ **Cheapest, highest-value next measurement.** Data already on disk. Every other #103 question is conditional on it. |
| #106 | PBO + Deflated Sharpe on real studies | Specified, data on disk, not run. |
| #107 | `TRIALS_PER_DIM` contradicts MinBTL | **An operational contradiction, not a research question.** Two budget policies point in opposite directions. |
| #108 | CMA-MAE (resolution-invariant QD) | Filed so the option is not lost. **Not recommended yet** — its documented cliff is below 200×200 archives; ours is 9×9. |
| #102 | cold start is the default | **Shipped.** Left open pending the owner's review of its cost. |
| #85 | two-stage eliminates indicators at factory defaults | ⭐ **Confirmed mathematically by #103.** Stage A judges the median indicator at **0.02%** of its behaviour. |
| #81 | 18→165 growth, components mis-calibrated | Largely addressed by #88/#89/#101; closes when #90 does. |
| #90 | re-validate MAP-Elites and two-stage | **Untouched.** Their accepted results predate every recalibration. |
| #98, #100 | `[needs-run]` — implemented, unproven | Parked at owner's instruction. |
| #79, #83, #84, #86, #91, #92, #93 | engine/dashboard/instrument work | Unrelated to this workstream. |

---

## 3. Defaults that changed, and why (these bite hardest if forgotten)

| default | was | is now | why |
|---|---|---|---|
| **indicator frame** | `--ind-1min` opt-IN | **1-minute is DEFAULT**; `--tf-indicators` opts out | Wrong frame scores the **deployed champion INFEASIBLE** ($38k P&L / $23.6k DD vs $147k / $14k). Produced an empty archive that looked like a broken algorithm. **The tell it was wrong: every production caller already passed `ind_1min=True` by hand.** |
| **warm start** | ON by default | **cold start is DEFAULT**; `--warm-start` opts in | Warm start seeds one basin and evolution grows on one side, killing settings that would win from elsewhere. ⚠️ **Removes the ≥-champion guarantee.** Cost measured: discards rise 68→74%, and **3 of 8 cold runs produce NOTHING in the 3–10 indicator band**. |
| **MAP-Elites indicator axis** | raw count (166 columns) | **9 buckets**, unbounded `51+` catch-all | Archive width tracked the registry ⇒ 0.27 visits/niche ⇒ "keep the first, not the best". |
| **rounding** | `round(x, 4)` / 12 sig digits | **round NOTHING** | A live `round()` flipped NG 5m's sign. THE FAST ENGINE NEVER LIED. |
| **`build_argv`** | omitted flags at default | **always states frame AND start** | A launched command is a record of what was run. |

⚠️ **`--ind-1min` and `--no-warm-start` still parse** — they now restate the defaults, so every existing
run script, playbook and dashboard call keeps working.

---

## 4. Traps — the ones that cost real time

1. **`/tmp/wsh_l1_cache` is SHARED and unkeyed by workstream.** Clear it after any P&L change. **Two
   agents on this device will silently corrupt each other's results through it.**
2. **Wrong data root ⇒ ~32 FAKE regressions.** Only `~/Mulham/wsg-i` has `ALL_STOCKS`. Correct server
   invocation: `WSH_DATA_BASE=/home/dev/Mulham/wsg-i WSG_DATA_ROOT=/home/dev/Mulham/wsg-i/data`.
3. **`| head -N` on a long run SIGPIPEs the process** — killed a 285s run mid-A/B, and because the grep
   filter missed stderr it presented as a silent crash with exit code 0.
4. **`pkill -f <pattern>` matches your own shell.** Kill by port.
5. **A green test can pin a defect.** `test_behavior_binning` asserted `== (2, 8)` and was green
   throughout — it was asserting the bug.
6. **Presentation code can lose a measurement.** `niche_label` raised an `IndexError` at the *last step*
   of a completed run; 400 paid-for evaluations nearly lost.
7. **Two runs agreeing on the SAME seeds is not replication.** 8/8 at +55% became 5/8 at −4% on fresh
   seeds. It is the same eight dice rolls counted twice.
8. **A counter that rises as things get worse is a WRONG instrument, not a weak one.** An archive of junk
   is easy to improve, so "improvements" went UP as the archive got worse.
9. **A default you did not choose is a condition of your experiment.** 48 runs were warm-started by
   omission and the headline result did not survive removing it.
10. **Optuna studies live in per-TF SQLite unless `WSH_STORAGE_URL` is set.** Check both backends before
    declaring a study missing.

---

## 5. Infrastructure

| | |
|---|---|
| server | `amd-trading` → **78.89.209.212 port 33362**, user `dev`, key `~/.ssh/amd_trading`. 32 cores, 123 GB RAM. (The private `192.168.50.62` address is NOT reachable from the agent sandbox.) |
| server code | `~/Mulham/code` on `dev`, kept in sync by `git pull --ff-only origin dev` |
| server venv | `/home/dev/Mulham/.venv/bin/python3` — **has numba** (local does not; local MAP-Elites is ~7× slower and skips 10 SMC-parity tests) |
| data root | `WSH_DATA_BASE=/home/dev/Mulham/wsg-i`, `WSG_DATA_ROOT=/home/dev/Mulham/wsg-i/data` |
| thread caps used | `OMP/OPENBLAS/MKL/NUMEXPR_NUM_THREADS=4` |
| browser | Chrome extension **cannot reach this sandbox's loopback**; `file://` is blocked. UI verification must be done by the owner. |

---

## 6. The measured constants worth remembering

| quantity | value |
|---|---|
| indicators / parameter dims | 165 / 295 |
| deployable region (7 of 165 × params) | 10^36.9 |
| coverage by 4,000 evals / by 1 trillion | 10⁻³³·³ / 10⁻²⁴·⁹ |
| NQ 4h decision bars / span / bars per fold | 2,119 / 1.38 yr / 423 |
| candidate 7-indicator structures per decision bar | **10^8.4** |
| MinBTL at 4,000 / 47,100 trials | **13.2 yr / 17.8 yr** |
| independent trials supported by 1.38 yr | **≈ 5** |
| Stage A's view of the median indicator | **1 of 4,851 settings = 0.02%** |
| evaluations discarded (warm / cold) | 69.2% / 74.6% |
| achieved evals per niche | **1.46** (published QD settings: 6.6–2,048) |
| deployed NQ 4h champion (1-min frame) | median fold P/L **$23,328**, full **$147,191**, DD **$14,043** |

---

## 7. Document map

| path | what |
|---|---|
| `docs/research-103/00-SYNTHESIS.md` | ⭐ **all six questions answered — read first** |
| `docs/research-103/01-ANALYSIS-search-space-and-staging.md` | space size, coverage, the staging theorem |
| `docs/research-103/02-PRIOR-ART-statistical-limit.md` | MinBTL / DSR / PBO / haircut, verified |
| `docs/research-103/03-ANALYSIS-are-our-fixes-predictable.md` | our 1-in-8 record |
| `docs/research-103/04-PRIOR-ART-algorithms-and-staging.md` | Powell/Tseng, NAS τ decay, mixed-variable optimisers |
| `docs/research-103/05-PRIOR-ART-quality-diversity-scaling.md` | QD scaling, CMA-MAE, stepping-stone literature |
| `docs/reports-2026-08-03/ISSUE-88-COMPLETE-RECORD.md` | all 98 #88 runs, 4 criteria, 3 apparatus bugs |
| `docs/reports-2026-08-03/ISSUE-88-ROUND5-FINAL.md` | the fresh-seed collapse |
| `docs/reports-2026-08-03/ISSUE-101-result.md` | stepping stones refuted |
| `docs/reports-2026-08-01/ISSUE-88-explained-visually{,.ar}.md` + `.html` | the plain-language/visual explainers, EN+AR |

Raw per-seed results: `subprojects/Parametric-Indicators/optimize/results/issue{88,88r2,88r3,88r4,88r5,101}/`.

---

## 8. If this workstream is resumed, do these in this order

1. **#105** — effective independent trials (PCA on the trial matrix). Cheap, data on disk. **Every other
   question is conditional on it.**
2. **#106** — PBO + Deflated Sharpe on real studies and the deployed set.
3. **#107** — resolve which budget policy governs; they currently contradict.
4. **#104** — the τ test, only if search work is still judged worthwhile after 1–3.
5. **#90** — re-validate MAP-Elites and two-stage.

**Do not** start #108 (CMA-MAE) or either architecture branch before 1–4 report. Both are search
improvements, and #103 says search improvement is the wrong lever at 1.38 years of history.
