---
name: legacy-18-baseline-start-here
description: "Onboarding for the agent operating the legacy-18-baseline workstream — what this project is, what is already known, what is isolated and why, and the rules that are not negotiable. Read this completely before touching anything."
type: onboarding
date: 2026-08-03
workstream: legacy-18-baseline
branch: research/legacy-18-baseline
---

# START HERE — `legacy-18-baseline` workstream

> ⚠️ **Data location changed 2026-08-22:** market data lives ONLY on the server (`~/Mulham/wsg-i`, `~/Mulham/data_2010_1s`); the local checkout has NO data trees. Authoritative map: `docs/DATA-AND-KNOWLEDGE-MAP.md`.

**You are one of two agents working on this project on this device, at the same time.** The other
agent works in `/mnt/data/projects/trading` on branch `dev`. You work **only** here, in
`/mnt/data/projects/trading/legacy18`, on branch `research/legacy-18-baseline`.

Read this whole file before running anything. It is short on purpose; the deep material is linked.

---

## 1. What this project is

A futures trading strategy research system. It searches for "champion" strategy configurations —
entry/exit rules plus a set of technical **indicators** that vote to confirm or veto trades — and
backtests them against real price history.

- **Main code:** `subprojects/Parametric-Indicators/`
- **Language/stack:** Python (backtest engine, optimizer), Vue+Vite frontend under `frontend/`
- **Optimizer:** Optuna (NSGA-III), plus a two-stage decomposition and a MAP-Elites quality-diversity
  archive
- **The repo is PUBLIC** on GitHub (`mulhamfetna/trading-strategy-finder`)

---

## 2. What makes THIS workstream different

The indicator library grew from **18 → 165**. That growth broke a long series of things, and a large
research programme (issue **#103**) concluded that at the current sample size the growth cannot be
validated at all.

**Your workstream deliberately searches only the ORIGINAL 18 indicators** — the registry as it was
before the expansion — while keeping every fix that has landed since.

The 18, in registry order (12 classic + 6 SMC):

```
ema_trend  sma_trend  macd  vwap  keltner  obv  cci  rsi  stochastic  mfi  bollinger  adx
structure_trend  order_block  fvg  ifvg  breaker  cisd
```

They are pre-set in your environment as `$WS_IND18`. **Every optimizer invocation must pass
`--only-indicators "$WS_IND18"`.** That flag forces every other indicator off.

**You start from `dev` HEAD, not from an old commit.** This is deliberate: many fixes landed that also
benefit the old 18 (precision, gap-aware fills, cold start, the 1-minute indicator frame, root/preflight
handling). Rewinding would throw those away.

**Your actual research question will be given to you by the owner.** It is *not* in this file. This file
exists so that when you get it, you start from solid ground.

---

## 3. Isolation — what is separated and what is shared

**Source `.wsenv/env.sh` before every command.** Nothing below works otherwise.

```bash
cd /mnt/data/projects/trading/legacy18
source .wsenv/env.sh
```

| resource | isolated? | how |
|---|---|---|
| code checkout | ✅ | separate git worktree, branch `research/legacy-18-baseline` |
| Python env | ✅ | `.venv/` here — use `$WS_PY`, never bare `python3` |
| **L1 disk cache** | ✅ | `TMPDIR` → `/tmp/ws-legacy18` (sibling uses `/tmp/wsh_l1_cache`). **This is the one that would silently corrupt both workstreams.** See §4. |
| Optuna studies | ✅ | `optimize/studies/` resolves from `__file__`, so the worktree separates it. `WSH_STORAGE_URL` is force-unset. |
| results | ✅ | `optimize/results/` — same mechanism |
| study names | ✅ | always prefix with `$WS_PREFIX` (`lg18_`) |
| CPU | ⚠️ shared | thread caps set to 4 so you cannot starve the other agent |
| **price data** | ⚠️ **shared, read-only** | not workstream-specific; **never write to it** |
| GitHub issues | ⚠️ shared repo | your issues carry the `workstream:legacy-18` label + milestone |
| the server | ⚠️ shared | see §6 — coordinate, do not assume it is free |

---

## 4. The trap that will get you if you skip §3

`optimize/l2/payload.py` caches L1 backtest results to disk:

```python
_DISK_CACHE = Path(tempfile.gettempdir()) / "wsh_l1_cache"
```

`tempfile.gettempdir()` honours `TMPDIR`. **Without `TMPDIR` set, you and the other agent share one
cache.** The cache key is a hash of lean params + instrument + a version string — it does **not**
include the engine or indicator code. So if either workstream changes the engine, indicators, or fill
logic without bumping `_L1_CACHE_VER`, the other silently consumes poisoned P&L. **No error, no
warning — every number just becomes wrong.**

This already caused a real incident in the other workstream: a cached path reported `$50,030` against
a true `$14,235` divergence and it looked like a parity bug.

**Sourcing `.wsenv/env.sh` fixes it. Do it every time.**

---

## 5. Rules that are not negotiable

These come from the project owner and have been learned the hard way. They are enforced socially, not
by code.

1. **Open a GitHub Issue BEFORE starting any work.** Issues are the board. Label yours
   `workstream:legacy-18` and attach the milestone.
2. **Pre-register your criterion before you run.** Write down what counts as pass/fail, commit it, then
   run. This workstream's sibling ran 8 pre-registered criteria and **1 passed** — the discipline is the
   only reason that is known rather than spun.
3. **No silent defaults.** Never `dict.get(key, default)` for a strategy or measurement parameter. Print
   the parameters actually used. A default you did not choose is a *condition of your experiment*.
4. **Never a NEGATIVE result without a power analysis. Never a POSITIVE result without a dumb control
   and a noise check.** A single seed can produce a false pass — it did, at 2.06× when the median was
   1.55×.
5. **Fresh seeds are not a formality.** An 8/8 result at +55% became 5/8 at −4% on unseen seeds. Two
   runs agreeing on the *same* seeds is not replication.
6. **No heavy compute on this box without explicit permission.** Default to the server (§6).
7. **LOCAL (git) is the source of truth for CODE + EVIDENCE.** Every output produced on the server
   must be `scp`'d back and committed. **MARKET DATA is the exception since 2026-08-22: it lives ONLY
   on the server** (`docs/DATA-AND-KNOWLEDGE-MAP.md`); the local checkout has no data trees and must
   never grow them back.
8. **Stay in this worktree.** Never switch branches or worktrees unless told to out loud.
9. **Verify, don't assume.** Never conclude from truncated output. ⚠️ `| head -N` on a long run
   **SIGPIPEs the process**, and a filter that misses stderr hides the reason.
10. **Everything you generate is a LOCAL FILE by default.** Do not publish, upload, email, or post
    anything without being asked in that message. Pushing to the existing git remote is fine.

---

## 6. The server

Heavy compute goes here. **It is shared with the other workstream — check before launching.**

```bash
ssh amd-trading                      # 78.89.209.212 port 33362, user dev, key ~/.ssh/amd_trading
```

- 32 cores, 123 GB RAM, has numba. **Your local venv also has numba** (the sibling's does not) — see §8b.
- Server checkout: `~/Mulham/code` — currently tracks `dev`. **You must not repoint it.** Create your
  own checkout or worktree for this workstream.
- Data root on the server (required, or ~32 tests fail as fake regressions):
  `WSH_DATA_BASE=/home/dev/Mulham/wsg-i WSG_DATA_ROOT=/home/dev/Mulham/wsg-i/data`
- Server venv: `/home/dev/Mulham/.venv/bin/python3`
- ⚠️ `pkill -f <pattern>` matches your own shell. **Kill by port.**
- ⚠️ The private address `192.168.50.62` is **not** reachable from the agent sandbox; use the public
  host above.
- ⚠️ The Chrome extension cannot reach this sandbox's loopback and `file://` is blocked — browser
  verification must be done by the owner.

---

## 7. What is already known — do not re-derive this

Read these before proposing anything. They will save you weeks.

| document | why it matters to you |
|---|---|
| `docs/WORKSTREAM-PIN-2026-08-03.md` | ⭐ complete state of the sibling workstream: every issue and its verdict, every changed default, 10 traps, all measured constants |
| `docs/research-103/00-SYNTHESIS.md` | ⭐ why the 165-indicator search cannot be validated: 1.38 years supports ~5 independent trials; we ran 4,000–47,100 |
| `docs/reports-2026-08-03/ISSUE-88-COMPLETE-RECORD.md` | how a search fix was measured across 98 runs and 5 criteria — the template for doing this properly |
| `docs/EXPANSION_ROUND_PLAYBOOK.md` | read BEFORE adding any indicator, instrument, timeframe or layer |

**The single most important inherited finding for you:**

> With **1.38 years** of history, the number of independent trials that keeps an in-sample Sharpe of 1
> meaningful is **≈ 5**. Searching 18 indicators instead of 165 shrinks the *space* — it does **not**
> change the sample size. If you run thousands of trials on 18 indicators you inherit the same
> multiple-testing problem.
>
> **Your advantage is that with 18 indicators a much smaller number of trials can cover a meaningful
> fraction of the space.** Use that. Do not simply point the old budget at the smaller space.

Relevant open issues: **#87** (history too short — now the highest-value issue in the project),
**#85** (two-stage eliminates indicators at factory defaults), **#90** (MAP-Elites/two-stage results
predate recalibration), **#103** + children **#104–#108**.

---

## 8. Defaults you will inherit, and their history

| default | value | why |
|---|---|---|
| indicator frame | **1-minute** (`--tf-indicators` opts out) | the wrong frame scores the *deployed champion* infeasible and yields an empty archive that looks like a broken algorithm |
| start | **cold** (`--warm-start` opts in) | warm start seeds one basin and kills settings that would win from elsewhere. ⚠️ removes the ≥-champion guarantee |
| rounding | **none** | a live `round(x,4)` once flipped a P&L sign |
| MAP-Elites indicator axis | 9 buckets, `51+` catch-all | archive width used to track the registry size |

`--ind-1min` and `--no-warm-start` still parse; they now restate the defaults.

---

## 8b. Environment facts you must know before comparing any number

**This environment is NOT identical to the other workstream's local environment.** Three differences,
all of which can move results:

| | this workstream | main workstream (local) |
|---|---|---|
| **numba** | **0.66.0 — INSTALLED** | absent |
| numpy / pandas / optuna | 2.4.6 / 3.0.5 / 4.9.0 | 2.3.5 / 3.0.2 / 4.8.0 |
| suite result | **1,230 passed / 4 skipped / 0 failed** | 1,197 passed / 14 skipped |

**Why numba matters:** with it present, the 10 SMC numba-parity tests actually RUN here (they *skip* in
the other local env), and MAP-Elites is roughly 7× faster. It also means you exercise the compiled
kernel paths, not the pure-Python reference. That is a genuine advantage — and a genuine reason your
timings and any float-sensitive result are not directly comparable to the sibling workstream's local
numbers. **Compare against the server, or against your own baseline.**

The exact package set is frozen in `.wsenv/requirements-lock.txt`. If you need bit-comparability with
the sibling workstream, pin from theirs instead — but say so out loud when you do.

**Data is NOT local any more (2026-08-22):** `ALL_STOCKS`, `Full_Canldes_Data`, `data`, `2024_data`,
`2026_last_20_days_data` and all delivery/vendor zips were merged onto the server and deleted here.
Every data-backed run happens on `amd-trading` with `WSH_DATA_BASE=/home/dev/Mulham/wsg-i
WSG_DATA_ROOT=/home/dev/Mulham/wsg-i/data` — exact paths and coverage in `docs/DATA-AND-KNOWLEDGE-MAP.md`.
A local `FileNotFoundError` under `/mnt/data/projects/trading/...` is the rule working, not a bug.

⚠️ **A residual of #94 lives here:** at least one code path builds a data path from the *checkout*
rather than from `roots.py`'s `DATA_ROOT` (`tests/test_smc_numba_parity.py` wanted
`<worktree>/data/full_data/NQ_full_data.csv`). The symlinks work around it. If you touch data paths,
prefer `roots.data_path(...)` and consider filing the residual.

---

## 9. Your first commands

```bash
cd /mnt/data/projects/trading/legacy18
source .wsenv/env.sh

# sanity: the 18 are what you think they are
$WS_PY -c "
import sys; sys.path.insert(0,'subprojects/Parametric-Indicators')
from indicators import library
R=list(library.REGISTRY); print('registry size:', len(R)); print('first 18:', R[:18])"

# the shape of a run for THIS workstream (dry-run the budget first, never launch blind)
cd subprojects/Parametric-Indicators
$WS_PY optimize/optimizer.py 4h --only-indicators "$WS_IND18" --plan
```

`--plan` prints the search-space size and the dimension-proportional trial budget **without running**.
Read it against the multiple-testing limit in §7 before you accept it.

---

## 10. When you are given your research question

1. Open the Issue first, labelled `workstream:legacy-18`.
2. State the criterion, commit it, *then* run.
3. Report the result whichever way it goes.

The sibling workstream's record — 4 failed criteria, 1 narrow pass, one explicit prediction that was
wrong — is on the record in full. That is the standard here: **the failures are the part that made the
work trustworthy.**
