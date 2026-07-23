# DAILY-BOX-01 — Do the ignored daily boxes on NQ carry anything? — Results

**Date:** 2026-07-23
**Branch:** `research-daily-boxes`
**Spec:** `docs/superpowers/specs/2026-07-23-daily-boxes-characterization-design.md`
**Plan:** `docs/superpowers/plans/2026-07-23-daily-boxes-characterization.md`
**Status:** COMPLETE — verdict below
**Compute:** server (`~/Mulham/daily-boxes`), golden gate 6/6 before **and** after

---

## 0. The one-paragraph answer

The daily boxes we have been throwing away **do generate a lot of new trade signals** — on the 4-hour chart
they add **439 signals the current system never sees**, enough to raise the trade count by roughly **a
quarter**. That part is real and it is big. But when we tested whether those signals actually *predict*
anything, they did not: a daily zone put at a **completely random price** did just as well. Across **9 fair
comparisons** on two different chart speeds, the real daily zones beat the random ones **zero times**.

**So: lots of new trades, no evidence of any new edge. Recommendation — do NOT spend a re-optimization
campaign on them.**

---

## 1. What we were actually testing (plain language)

Our strategy trades off "boxes" — price zones drawn around important past highs and lows. Each zone has a
**top edge** and a **bottom edge**, so it is a band, not a line.

We currently load two kinds of zone:

- **Weekly** zones (`W…` columns) — about **48 points** tall.
- **Monthly** zones (`M…` columns) — about **109 points** tall.

There is a third kind sitting in the very same spreadsheet rows that we **throw away when we load the file**.
`box_lookup.py` says so in its own header, lines 8–10:

> *"Both weekly and monthly levels live on the same row (W\* and M\* columns). **Daily (D\*) columns exist in
> the raw file but are ignored at load time.**"*

Those are the **daily zones** — about **22 points** tall, roughly half a weekly zone and a fifth of a monthly
one. In money, at NQ's **$20 per point**, one contract:

| Zone type | Height in points | Height in dollars |
|---|--:|--:|
| **Daily** (ignored) | **22.2** | **$444** |
| Weekly (used) | 48.5 | $970 |
| Monthly (used) | 108.8 | $2,176 |

Two facts made this worth investigating rather than assuming, both measured on the real file:

1. **They are there every single day.** The four main daily zones are filled in on **363 of 363** days in the
   2025–26 file and **263 of 263** in the 2024 file — 100%. This is not an occasional extra; we discard it on
   every bar.
2. **They are not copies of what we already use.** A daily zone sits in the same place as the weekly zone on
   **0.0–0.6%** of days. They mark genuinely different prices.

### The two terms you need

- **A "signal"** — the rule that turns a zone into a trade idea. The champions' rule is *touch-and-close-beyond*:
  the bar must physically touch the zone, and then close **above the top** (a buy) or **below the bottom** (a
  sell). A bar that opens and closes the same (a "doji") is ignored.
- **The "gate"** — a set of filters (volatility check, indicator veto, confirmation vote) that throws away most
  signals. Only signals that pass the gate can ever become trades.

---

## 2. What we measured, and what we found

```mermaid
flowchart TB
  A["daily zones we discard"] --> M1["M1 — SUPPLY<br/>how many NEW signals?"]
  M1 --> M2["M2 — GATE SURVIVAL<br/>how many could we actually take?"]
  A --> M3["M3 — INFORMATION<br/>do they predict anything<br/>vs a random zone?"]
  M2 --> V{"verdict"}
  M3 --> V
  V --> OUT["large supply<br/>+ zero information<br/>= do NOT pursue"]
```

### M1 — Supply: yes, a lot

| | 4-hour chart | 1-hour chart |
|---|--:|--:|
| Bars examined | 2,119 | 8,121 |
| Signals today (weekly+monthly) | 829 | 1,759 |
| Signals from daily zones alone | 989 | 2,190 |
| **NEW signals** (daily fires where today's system is silent) | **439** | **1,355** |

"NEW" is the number that matters — a daily signal that merely repeats a weekly one adds nothing.

**Sanity check that we measured the right thing:** our day counts came out at **431 trading days, 340 with a
signal, 91 with none**. The earlier `RESEARCH_SLEEPING_DAYS` note independently reported *the same* 340/431 and
the same 91 "scarce" days. Two separate implementations landing on identical numbers is good evidence the
measurement is sound.

The daily zones create a signal on **49 of those 91 previously-silent days** (4h) — so they genuinely do fill
in dead days.

### M2 — Gate survival: still large

Most signals die at the gate, so the honest question is how many *survive*.

| | 4-hour | 1-hour |
|---|--:|--:|
| New signals | 439 | 1,355 |
| **New signals that pass the gate** | **65** | **82** |
| Current trade count (deployed champion) | 277 | 353 |
| **Potential increase in trades** | **23.5%** | **23.2%** |
| Pre-committed band | **large** | **large** |

By the decision rule we fixed *before* looking at any number (≥20% ⇒ "large"), both charts land in the **large**
band. On supply alone, this looked like a green light.

> **Two honest caveats on that 23.5%.**
> **(a)** The script's own printout said 26.2% because the helper it uses to count baseline trades
> (`champion_taken_trades`) runs the champion **without its time cap**, giving 248 trades instead of the
> deployed 277. We use the deployed **277**, so **23.5%** is the correct figure. Either way it stays "large".
> **(b)** This is an **upper bound**. It ignores that the strategy is often already in a trade, on cooldown, or
> halted by the loss breaker — any of which blocks a bar the gate allowed. The real number is lower.

### M3 — Information: no

This is where it falls apart. We asked the only question that matters for trading: **after a daily-zone signal
fires, does price keep going the way the signal pointed?** We measured that 1, 3 and 6 bars later, and compared
it against **two dumb controls**:

| Control | What it does | What it rules out |
|---|---|---|
| **Random location** | Same zone *height*, moved to a **random price** | "Any line drawn near price looks meaningful" |
| **Random date** | Give today **another day's** zones | "Any zone shape works, the date does not matter" |

Comparing two overlapping error-bars by eye is **not** a test of whether one is better. So we bootstrapped the
**difference itself** (real minus control) and asked whether it is reliably above zero.

**Result — real vs the random-location control, the meaningful one:**

| Chart | Window | 1 bar | 3 bars | 6 bars |
|---|---|--:|--:|--:|
| 4h | 2025–26 | −3.30 | −3.44 | +5.59 |
| 4h | 2024–26 | −1.08 | −4.63 | −4.67 |
| 1h | 2025–26 | −0.07 | +1.26 | −1.34 |

*(points; every single confidence interval includes zero)*

**Real zones beat randomly-placed zones in 0 out of 9 comparisons.** Seven of the nine point estimates are
**negative** — the random zones did slightly *better*.

**The one place "real" won, and why it does not count.** Against the weaker *random-date* control on the 4h
champion window, real won all three horizons (+30.4, +27.0, +45.8 points). But that same test **fails on the
longer 2024–26 window** (+8.3, +8.6, +23.9, all including zero). A result that vanishes when you add a year of
data is not a finding. It is also the weaker control by construction: shuffling dates flings zones far away
from current price, so only 89 signals survive and they are odd ones. Total across both charts: real wins
**3 of 18** comparisons, and **all 3 are that single non-replicating cell**.

---

## 3. The verdict

| Option | Verdict |
|---|---|
| **B — use daily zones as a new entry signal** | **NO.** Supply is large but carries no measurable information. |
| **C — use daily zones as a veto/filter** | **NOT TESTED** — see the honest limitation below. |
| Keep discarding them | **Yes, for entry purposes.** |

**Why "no" to B even though supply is large.** The whole cost of Option B — re-optimizing every champion,
re-capturing the golden baselines — is only worth paying if the new signals carry an edge. They do not. Adding
~440 (4h) or ~1,355 (1h) signals of no demonstrated value is precisely the pattern that **already killed the
intra-candle feature**: that feature also added entries, and the optimizer *avoided* it because the extra
trades blew up drawdown. We should not re-run that experiment under a new name.

### The limitation I will not paper over

**This study does not test Option C.** We measured whether *breaking through* a daily zone predicts
continuation. A veto is a different claim — that *entering toward* an unbroken zone is bad because price
bounces off it. That is a separate measurement we did not run. So C is **open but untested**, not disproved.
Note it is also a *quantity-reducing* change, which runs against the stated "increase entries" direction.

### Power — how much could we have missed?

Being straight about this. On the 4h chart at 1 bar, the smallest per-trade effect we could reliably detect was
**13.3 points ≈ $265 per trade**; the real zones showed **+3.7 points ≈ $75**. So a *small* edge cannot be
excluded by any single test, and the difference intervals are wide (e.g. −16.0 to +9.1 points).

What carries the weight is not one interval but the **pattern**: across 9 comparisons spanning two chart
speeds, three horizons and two date ranges, the estimates cluster at zero with **no positive trend** — 7 of 9
negative. A genuine edge would show up as consistently positive, not consistently zero.

---

## 4. What went well / what went wrong

**Went well**
- **Caught three spec errors before spending compute.** Reading the code rather than trusting the older
  research note revealed (i) the champions use *touch-and-close-beyond*, not `BoxLookup`'s traversal state
  machine, so the original plan would have measured signals the champions never see; (ii) `BoxLookup` is not
  even on the champion path — `engine.py:55` is; (iii) the champion window is 2025–26, so the planned 2024 box
  merge would have added rows nothing ever reads.
- **Zero production files touched.** The redesign put the study in its own package with the level list as a
  *required* argument. Golden stayed **6/6 before and after** — proof nothing moved.
- **The measurement self-validated.** Day counts (431/340/91) independently reproduced the earlier note's
  numbers.
- **Adding the difference test changed the conclusion's strength.** Eyeballing the per-arm intervals suggested
  "probably nothing"; the differential test made it **0 of 9**, which is a far firmer basis for a decision.
- **Fixed a real path bug found at run time:** the study read candles from the wrong root, which silently
  "worked" on 4h and would have broken on 1h.

**Went wrong / would do differently**
- **My pre-committed decision rule had a gap.** It branched on supply first (≥20% ⇒ go B) and only consulted
  informativeness if supply was small. It never contemplated **large-but-uninformative** supply — which is
  exactly what happened. Following the rule literally would have said "go B". Future rules must require the
  edge test to *pass* before size of supply matters.
- **The random-date control is weak.** By flinging zones away from price it collapses the sample to 89 and
  produces a non-replicating "win". The random-*location* control is the one worth keeping.
- **The 2024 extension only exists for 4h** (there is no `NQ_1h_2024.csv`), so 1h got no power boost. The run
  prints that it skipped, so it can never be mistaken for a measured null.
- **Still one bull era.** Everything here is 2024–2026. Nothing in this study speaks to a bear market.

---

## 5. Reproduce

```bash
# server, from ~/Mulham/daily-boxes/subprojects/Parametric-Indicators
env WSH_DATA_BASE=/home/dev/Mulham/wsg-i WSG_DATA_ROOT=/home/dev/Mulham/wsg-i/data \
  /home/dev/Mulham/.venv/bin/python3 -m research.daily_boxes.run_study \
  --tf 4h --horizons 1,3,6 --seed 20260723 --draws 1000 --block 20 --loc-frac 0.02
```

Outputs: `results/daily_boxes/{tf}_supply.csv`, `{tf}_informativeness.csv`, `{tf}_real_vs_control.csv`.
Local unit tests (no server data): `python3 -m pytest tests/test_daily_boxes_*.py` → 29 passed.
