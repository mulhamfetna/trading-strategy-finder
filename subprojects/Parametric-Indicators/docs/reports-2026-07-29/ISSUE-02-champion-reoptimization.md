# Issue #2 — Re-tune the champions for honest pricing · **IN PROGRESS**

**Date:** 2026-07-29 · **Status:** the July attempt is **retracted**; a corrected re-run is **running now**

---

## 1. What this is about, in plain language

Our "champions" are the specific strategy settings we actually trade — the stop-loss distance, the
profit target, and which indicators vote.

Those settings were **tuned on a backtest that cheated on gaps** (it gave us the price we asked for even
when the market jumped past it — see
[GAP-02](./00-GLOSSARY-plain-language.md#7-what-was-gap-02-in-baby-language)). Once we made the backtest
honest, the natural question was: **if we re-tune the champions honestly, do we get better strategies?**

## 2. First finding: the July run was never lost — it was never saved

An earlier note of mine said this work had vanished, because no trace of it existed in the optimizer
database. **That was a bad conclusion.** The run had finished perfectly well — 12 studies, 8 hours 34
minutes — but its results existed **only as loose, untracked files on the server**. They are now
committed to the repository at `optimize/reports/gap_fills/reopt_wshgap/`.

> **And I got it wrong a second time.** I then reported that the optimizer's own database records were
> gone too, because a search of our Postgres database found nothing. **I searched the wrong database.**
> The optimizer only uses Postgres when specifically told to; by default it writes to ordinary files on
> disk, one per timeframe. **All 12 studies are intact**, with every trial preserved (5,900 each).
>
> The practical upshot: July's run can be **re-read at full precision** without re-running it. It still
> shouldn't be *adopted* — §3 and §5 are unaffected — but "lost" was wrong twice over, and both times I
> concluded it from a search that came back empty rather than from checking where the data actually
> lives. **An empty result only means "not here"; it never means "nowhere".**

> This is exactly what the "the local repository is the source of truth" rule exists to prevent. For a
> week the issue said *"Running now on the server"* while the only evidence sat on a machine nobody was
> reading.

## 3. Second finding: its conclusions were wrong — and the headline reverses

The July run reported that three re-tuned strategies beat the ones we deploy. **They were compared
against the wrong list.**

We changed our official champion list on **14 July**. The July run — on **21–22 July** — still compared
against the **old, retired list**.

Scored against the strategies we *actually run*:

| | full history | the unseen year |
|---|---:|---:|
| what July claimed ("vs deployed") | +$52,443 | **+$35,475** |
| **vs what is truly deployed** | +$94,522 | **−$12,832** |

| the three "winners" | change vs the real deployed champion |
|---|---:|
| Nasdaq 1-hour | **+$10,805** ✅ |
| gold 15-minute | **+$2,226** ✅ |
| Nasdaq 2-hour | **−$14,017** ❌ |
| **net** | **−$986** |

**So the trio is a coin-flip overall, and the Nasdaq 2-hour "winner" is $14,017 worse than what it was
meant to replace.**

**The most uncomfortable part:** a file called `best_vs_wsh4.txt`, which shows exactly this, was
generated on 22 July at **16:05 — forty minutes *after* the champions were adopted.** The check was run.
Nobody read it.

## 4. Why it happened (the root cause — and it is bigger than this issue)

The optimizer is given a head start: it is seeded with the current champion, which guarantees the answer
it returns is **never worse than what we already run**.

That seeding read the champion list **by filename**. When the official list changed on 14 July, nothing
updated the filename. So the guarantee kept working perfectly — **against a list we had retired.**

> **Every warm-started re-optimization between 14 July and 29 July was measured against the wrong
> starting point.** Nothing failed; every internal check still passed. That is what made it invisible.

**Fixed:** the seed is now looked up through the same mechanism the dashboard uses, and each study
**prints which file actually seeded it**. A test verifies this fails on the old code.

## 5. Two more flaws in the July run

- **Its "out-of-sample" year wasn't out-of-sample.** The tool for holding a year back didn't exist until
  last week. So the optimizer had *already seen* 2026 when it was scored on 2026. (This flatters the
  results — so the two configurations July *rejected* were rejected despite the advantage, and those
  rejections stand.)
- **Its numbers were saved to 4 decimal places.** For Nasdaq and gold this is harmless. It would have
  been fatal on natural gas. (Now fixed everywhere — see §7.)

**Nothing live was damaged:** the July adoption wrote into the *retired* file, so the strategies we
actually trade were never changed.

## 6. Third finding: the re-run I launched was itself wrong — twice

**Attempt 1** searched all **165** indicators. July searched only the original **18**. Same command,
same flags, completely different search — because July's copy of the code predated the bigger library.
Worse, it contradicted [#14](./ISSUE-12-indicator-library.md#5-read-this-before-using-the-new-library),
which concluded the 143 new indicators should stay **off**. A champion has no business being built from
indicators we decided we can't justify.

**Attempt 2** restricted the indicators correctly — but the *trial budget* didn't notice. The optimizer
sizes its workload from the number of things it's searching, and that calculation still counted all 165.
It budgeted **47,100 trials for a 59-dimension search — 8× too many.**

> That's **~20 hours per study instead of ~45 minutes** — about **10 days** for the campaign instead of
> ~9 hours. Nothing errored. It would simply have run, and run, and run.

Both are fixed and tested. The budget now reproduces July's figures exactly (59 dimensions → 5,900
trials).

## 7. What is running now

| setting | value |
|---|---|
| study name | `wshgap4` |
| markets | Nasdaq + gold, all 6 timeframes = **12 studies** |
| head start | **the truly deployed champions** (verified in the log) |
| indicators searched | **18 of 165** — matching July and honouring #14 |
| training data | **2025 only** — 2026 is genuinely held back |
| pricing | honest gap fills (now the default) |
| progress | study 1 of 12; ~25 min each; **~5 hours total** |

A watcher reports each study as it completes, and — importantly — **alerts if the run dies** rather than
going quiet.

## 8. What happens when it finishes

Each re-tuned strategy is compared against the deployed champion **on the 2026 year neither has seen**.
A strategy is only proposed for adoption if it improves that year **and** doesn't worsen risk. Given
§3, my expectation is that **few or none will qualify** — and that is a perfectly good result.

## 9. What went well / what went wrong

- **Went well:** the lost work was recovered rather than redone from scratch; the root cause turned out
  to affect *every* re-optimization for a fortnight, not just this one; three separate bugs
  (wrong seed, 8× over-budget, wrong indicator scope) were caught **before** burning ~10 days of compute.
- **Went wrong:** an issue said "running now" for a week while nothing was running; the disproving
  evidence was generated and ignored; and **I twice launched a long job without first checking that its
  search matched the run it was meant to reproduce.** Comparing the two plan printouts — which takes ten
  seconds — would have caught both immediately.
