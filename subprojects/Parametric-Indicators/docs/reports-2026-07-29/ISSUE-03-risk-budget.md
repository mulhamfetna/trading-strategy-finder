# Issue #3 — How much should we bet per trade? · **CLOSED**

**Date closed:** 2026-07-29 · Full technical version: [RISK-02](../superpowers/RISK-02-ruin-bound-honest-fills.md)
**Terms used here** (`f`, `R`, `P(ruin)`) are explained in [the glossary](./00-GLOSSARY-plain-language.md).

---

## 1. The question

*"If I have $100,000, how much of it should I risk on a single trade?"*

The old answer was **0.6%–1.2%**. That answer was built on a backtest that **understated our risk by
about 10%** (see [GAP-02](./00-GLOSSARY-plain-language.md#7-what-was-gap-02-in-baby-language)), so it
needed redoing honestly.

## 2. The one measurement that changed everything

We took every trade our 54 live strategies would have made, priced honestly, and asked a simple
question: **did the stop-loss actually limit the loss?**

> **21.8% of trades lost MORE than their stop-loss was supposed to allow.**
> The worst lost **183 times** its intended risk.

In dollars, on a $100,000 account risking $1,000 per trade: that one trade lost **$183,000**. More than
the entire account.

**This breaks the method everybody had been using.** The old sizing maths quietly assumed a stop-loss
always holds — that the worst a trade can do is lose exactly what you planned. That was *true* while the
backtest cheated on gaps. It is not true now.

## 3. Why the old calculator couldn't see the danger

The inherited simulator had two flaws that only matter once losses can exceed the stop:

1. **It could not go bankrupt.** When a trade wiped out the account, the code floored the balance at a
   hair above zero and **carried on compounding** — so ruin was recorded as "a very bad day", never as
   "the end."
2. **It reported the *typical* outcome** (the median). The catastrophe is rare by definition, so the
   typical simulated trader never experiences it — **the exact event that decides how much you can bet
   was the one being averaged away.**

Run honestly, that old calculator recommends betting **4% per trade with a 72% drawdown** — and its
"best" answer sat right at the edge of the range we tested, which is the classic sign of a broken
measurement rather than a real optimum.

## 4. The corrected answer

We rebuilt it so bankruptcy is **permanent**, and we report the *chance of disaster* rather than the
typical day:

| you risk per trade | chance of being **wiped out** | chance of **losing half** |
|---|---|---|
| 0.40% ($400) | **0.00%** | 1.7% |
| 0.60% ($600) | **0.85%** | 2.7% |
| **1.00% ($1,000)** | **1.67%** | 5.6% |
| 4.00% ($4,000) | **10.16%** | 96.5% |

**The old "ceiling of 1%" carried a 1-in-60 chance of total wipe-out.** That is the headline correction.
The old *operating range* of 0.25–0.5% was fine.

## 5. Natural gas alone was setting the limit for everything

| market | worst trade ever | biggest safe bet |
|---|---:|---:|
| Dow (YM) | −2.1× | 2.0% |
| S&P (ES) | −2.9× | 1.5% |
| gold, Russell, oil, silver, Nasdaq, copper | −9× to −36× | 1.0% |
| **natural gas (NG)** | **−183×** | **0.3%** |

Take natural gas out of the book and **the chance of ruin is 0.00% all the way up to 2%**, and everyone
else can safely bet **1.0%** instead of 0.4%.

**So one market was forcing the other eight to trade at 40% of the size they could safely handle.**

## 6. The single trade behind all of it — checked against the raw data

Because this entire conclusion rests on one trade, I traced it back to the actual price bars rather than
trusting the summary:

| | |
|---|---|
| what | natural gas, 5-minute strategy, stop-loss = **0.001017** |
| we sold short at | **3.368** — a real closing price, Friday 3 Jan 2025, 16:55 |
| we were stopped out at | **3.554** — Sunday 5 Jan 2025, 18:00 |
| what happened in between | the weekend. Gas reopened **+5.52% higher** |

We held a short position over a weekend. The market reopened 5.5% against us. Our stop-loss was worth
**0.03% of the price**. It was never going to matter.

**This is real weekend gap risk, not a data glitch.** And it says something uncomfortable: on natural
gas, the "hard stop" is not a risk control at all.

## 7. What we recommend

1. **Bet a different amount in each market**, not one number for everything:
   **NG 0.3%** · Nasdaq/gold/silver/copper/oil/Russell **1.0%** · S&P **1.5%** · Dow **2.0%**.
2. **If you must use a single number, it is 0.40%** — not 1%.
3. **Stop using "how deep is the dip" as the safety measure.** Use **chance of ruin**. Drawdown was the
   right measure only while stop-losses held.
4. ⚠️ **For natural gas, the real fix is the stop-loss, not the bet size.** A 0.001 stop on a market
   that jumps 0.19 over a weekend isn't protection. Widening it — or simply not holding gas over the
   weekend reopen — would recover far more than shrinking the bet ever can. **That is a strategy change,
   so I did not make it: it is now [issue #79](./ISSUE-79-ng-stops.md).**

## 8. Honest caveats — please read these

- **One trade drives the whole-book limit.** It is real and verified, but it is a single observation of
  an extreme. Read it as *"gas can do this"*, not as a precise frequency. **Treat 0.3% as an upper bound
  for gas, not a finely-tuned optimum.**
- **The simulation shuffles trades independently.** Real losing streaks cluster together (bad weeks are
  bad across several markets at once), so real drawdowns can be worse than shown.
- **Equal money on every strategy** is assumed. A different allocation changes the tail.

## 9. What went well / what went wrong

- **Went well:** the previous study's good ideas were kept (measuring each trade against its own stop;
  re-running with 8 different random seeds to check the answer isn't luck). The decisive trade was
  traced to raw price bars instead of being trusted. The dangerous "1% ceiling" was caught.
- **Went wrong:** this issue was marked *blocked* on the champion re-optimization for eight days. It was
  never actually blocked — it needed **54 strategies' risk data**, while that re-optimization covers
  **12**. And the earlier attempt (RISK-01) had done the maths perfectly on the **wrong strategy list**,
  skipping gas entirely — the exact market that turned out to be the whole story.
