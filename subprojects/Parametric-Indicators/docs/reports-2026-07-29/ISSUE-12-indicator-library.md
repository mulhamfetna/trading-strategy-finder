# Issue #12 — The 143 new indicators · **CLOSED**

**Date closed:** 2026-07-29 · **Status:** all work complete, but read §5 before using the library

---

## 1. What this was about, in plain language

An **indicator** is a small calculation that looks at price history and votes on a trade: *"yes, this
looks good"* (confirm) or *"no, don't"* (veto). We started with **18** of them. This issue added
**143 more**, taking the library to **165**.

Each new one had to be wired into four places: the backtester, the dashboard, the optimizer's search,
and the tests.

## 2. What was left open, and how it got closed

Two boxes were still unticked. Both were closed by other work:

| open item | closed by | result |
|---|---|---|
| the four **cross-market** indicators (ones that watch a *second* market to judge the first) were never properly measured | **#74** | they had been timing at *0.00 seconds* — because they were silently never running. Really 27.4s; now 1.9s |
| ...and were never properly *connected* | **#75** | the second market's data **never actually reached them**. Turning one on took a strategy from 13 trades to **zero** |
| should the new 143 be allowed into the champion search? | **#14** | **No — default OFF.** See §5 |

Verified before closing: the library really does hold **165** indicators and all four cross-market ones
are present and connected.

## 3. ⚠️ The bug that belongs to this issue

When the 143 indicators shipped, so did a broken safety valve.

There is a setting called `--max-enabled` that says *"never let a strategy use more than N indicators at
once."* When the optimizer exceeded that limit, it trimmed the list by **keeping the first N in
registry order**. The original 18 sit at positions 0–17; the 147 new ones start at position 18.

**So the original 18 always won. Always.**

> Measured: **0 out of 1,500 trials** contained a single new-library indicator. Not "few". **Zero.**

Any earlier study that used `--max-enabled` and believed it was searching 165 indicators was in fact
searching 18. It has been fixed (a fair random subset, seeded reproducibly — 98.1% of trials contained a
new indicator afterwards), and `optimize/perf/check_max_enabled_bias.py` exists to test any old study.

## 4. What went well / what went wrong

- **Went well:** all seven build phases landed, 86 unit tests, and full agreement between the fast and
  slow engines. The scale of the wiring job was genuinely delivered.
- **Went wrong — and this is the real lesson:** **the library was built with no tracking issue at all.**
  143 indicators plus a gate were written before anyone opened a ticket. Three separate defects
  (`--max-enabled`, the cross-market measurement gap, the cross-market wiring gap) then hid inside that
  undocumented work for weeks. Every one of them looked *fine* from the outside — nothing crashed,
  nothing errored, the numbers just weren't what everyone believed they were.

## 5. ⚠️ Read this before using the new library

**#14 tested whether the 143 indicators actually make money, and the answer was: don't switch them on.**

But be precise about *why*. The verdict is **"we cannot tell"**, not **"they don't work"**:

- the best strategy built from them **lost to the deployed champion by $42,774** on unseen data, and
- it **could not beat a placebo** (random votes), so there is no case for adopting it — **but**
- the test could only have detected an effect **3.5× larger than the one being looked for.**

So the *decision* (don't adopt) is solid. The *scientific claim* ("the new indicators are useless") is
**not supported**, and this should never be quoted as if it were.

Also note the champion re-optimization now searches **only the original 18**, precisely because of this
verdict — a champion has no business being built from indicators we decided we can't justify.
