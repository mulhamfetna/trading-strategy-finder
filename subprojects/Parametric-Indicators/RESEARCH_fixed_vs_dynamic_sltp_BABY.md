# Baby version — the two bottom-line points, explained slowly

**Plain-language companion to `RESEARCH_fixed_vs_dynamic_sltp.md`.** The big study confirmed: **keep the fixed
SL/TP, and refresh them by re-optimizing now and then.** It then added **two warnings/ideas**. This file
explains those two, slowly, with everyday pictures. No jargon.

First, two words we'll keep using:
- **SL/TP** = the exit doors of a trade. **Stop-loss (SL)** = the "I was wrong, get me out" door. **Take-profit
  (TP)** = the "good enough, bank it" door.
- **Re-optimize** = re-run the big search that picks the best SL/TP (and the other settings) on fresh data, to
  get an up-to-date set of numbers.

---

## POINT 1 — "Don't assume 6 months. Measure the right gap, and don't fool yourself when you re-search."

You suggested: *re-optimize every 6 months to refresh the fixed numbers.* Great instinct. The research says the
**idea is right, but two details matter**, and "6 months" was a guess.

### 1a. Don't guess the gap — measure it 🛢️
**Picture an oil change.** Nobody says "every car gets an oil change every 6 months." It depends on the car and
how you drive — some need it at 5,000 km, some at 15,000. Picking "6 months" for *everything* is just a guess.

Same with re-optimizing. How fast the best numbers "go stale" depends on the strategy and the market. The
research found:
- The right gap is **not a fixed guess** — you should **test** how long the numbers actually keep working
  before refreshing (the study calls the gap itself a "knob you must tune, not assume").
- In one real study, the numbers **stayed good for about 2 years** without any refresh. So **6 months might be
  too often** — refreshing more than needed just wastes effort (and, see 1b, risks new mistakes).
- Our own check agreed: our best SL/TP barely drifted over ~2 years.

**So:** keep the plan, but instead of "every 6 months by the calendar," either (a) measure what gap keeps it
working, or (b) put up a "smoke alarm" that tells you when the numbers actually start slipping, and only refresh
then. (That alarm is "Option 4" from the earlier decision doc.)

### 1b. When you re-search, don't fool yourself 🎰
Here's the trap. Re-optimizing means **trying lots of combinations** and **keeping the best one.** That sounds
safe — but it's dangerous if you try *too many* combinations on *too little* data.

**Picture flipping coins.** Give 1,000 people a coin and ask them to flip 10 heads in a row. A few will succeed —
**by pure luck.** If you then crown "the winner" and bet on them, you'll lose: they were never skilled, just
lucky. Trying thousands of strategy settings on a short history is the same — some will look amazing **by
accident**, and they'll fall apart with real money.

The research even gives a **speed limit** (called "Minimum Backtest Length"):
- With **5 years** of data, you can safely try about **45** different setting-combinations.
- With **2 years**, only about **7**.
- Go past that, and the "best" result you find is basically guaranteed to look great on paper and be **worthless
  live** (it fit the noise, not the market).

**So when we re-optimize we must:** (1) **count** how many combinations we try and **keep it under the limit**
for the data we have; and (2) **always check the winner on a chunk of data it never saw** before trusting it.
Good news: our optimizer already uses **walk-forward** testing (it checks on unseen data) — we just need to keep
the trial count honest.

**Point 1 in one line:** *Re-optimizing to refresh fixed numbers is right — but pick the timing by measuring
(or by a drift alarm), not by guessing "6 months," and don't try so many combos that the "best" is just luck.*

---

## POINT 2 — "The one 'smart/adaptive' trick that actually works here isn't smart EXITS — it's smart POSITION SIZE."

You originally wanted **smart, auto-adjusting SL/TP** (the exit doors move themselves). The research says:
auto-adjusting **exit doors** don't reliably beat good fixed doors. **But** there *is* one adaptive trick the
evidence supports for a market like ours — and it's a **different lever**.

### 2a. Two different dials — don't mix them up 🎛️
- **Dial A = where you exit** (SL/TP price levels). ← this is what we tried to make "smart," and it didn't help.
- **Dial B = how big your bet is** (how many contracts you hold). ← this is the one the research supports.

These are **not the same thing.** You can keep simple fixed exit doors (Dial A) *and* still be smart about how
big each trade is (Dial B). The big winning evidence in the literature is all about **Dial B**, not Dial A.

### 2b. "Volatility-targeted position sizing" — in plain words 🌊
It just means: **trade smaller when the market is wild, bigger when the market is calm**, to keep your risk
roughly steady.

**Picture driving in weather.** You don't change *where* your destination is (that's the exit door). You change
your *speed*: slow down in a storm, speed up when it's clear. "Vol-targeted sizing" is the same — when the market
gets stormy (high volatility), you shrink the position; when it's calm, you grow it.

### 2c. What it actually buys you — mostly a smoother ride, not more money 🛡️
This is the key honest part. For markets like **NQ (a stock-index future, a "risk asset")**, the research found:
- It can **slightly** improve the reward-for-risk on stock-type assets (its effect on bonds/currencies/
  commodities is basically zero — so it's *not* a universal magic trick).
- Its **biggest, most reliable** benefit across *everything* is **fewer giant losses and smaller drawdowns** —
  a calmer equity curve — **not** a big jump in profit.
- **Why:** the worst crashes happen when the market is already wild. If you're *already holding a small position*
  during wild times (because you shrank it), the crash hurts you much less.

### 2d. Why we are NOT rushing to add it
- It's a **future idea**, separate from the SL/TP question we just closed — it would be its own experiment.
- Our strategy **already does part of this job**: it has a **volatility gate** (skips trades when it's too wild)
  and a **drawdown breaker** (halts after losses). So the *extra* benefit of adding vol-sizing on top might be
  small.
- It only becomes worth building if we specifically decide we want **lower drawdown / a smoother ride** (and
  it must still pass the same honest re-optimization checks from Point 1).

**Point 2 in one line:** *Smart EXIT doors don't beat fixed ones — but for a market like NQ, trading SMALLER in
storms and BIGGER in calm ("vol-targeted position sizing") is a real adaptive trick; it mostly buys a smoother
ride (less drawdown), not more profit, so it's a "maybe later," not a "do now."*

---

## The whole thing in three sentences
1. Keep the **fixed** SL/TP; refresh them by re-optimizing.
2. Don't refresh on a blind 6-month timer — **measure** the right gap (or use a drift alarm), and when you
   re-search, **don't try so many combos that the winner is just luck**.
3. The only adaptive trick worth a *future* look is **changing position size with volatility** (smaller in
   storms) — which makes the ride **smoother**, not richer — and we're not building it now.
