# The Risk Re-Cut, Explained From Scratch (plain language)

**Date:** 2026-07-22 · Companion to the technical write-up [RISK-01](./RISK-01-sizing-recut-honest.md).
**Who this is for:** anyone, no maths background needed. Every term is spelled out. Money examples are real.

---

## Part 0 — What is "position sizing" and why does it matter at all?

Imagine you have a strategy that, over hundreds of trades, makes money on average. There is still one huge
question left: **on each single trade, how much money do you put on the line?**

- Bet **too little** on each trade → even a great strategy barely grows your account.
- Bet **too much** on each trade → a normal run of bad luck can wipe you out *even though the strategy is
  a winner overall*. (This is the famous "gambler's ruin": with a real edge but oversized bets, variance
  still kills you.)

So there is a "just right" amount to risk per trade. We call that the **risk budget** or **position size**.
It is usually written as a **percentage of your account risked per trade** — for example, "risk 0.5% per
trade" means you arrange the trade so that if it hits its safety-net (its stop-loss), you lose 0.5% of your
money. Finding that percentage, honestly, is what this whole report is about.

---

## Part 1 — Why we re-opened this question now

We already had an old answer for the risk budget from earlier work. Two things made us go back and redo it:

1. **We discovered our risk numbers had been rose-tinted.** In earlier work (the "gap-aware fills" fix) we
   found that when the price *jumps* straight past a safety-net instead of trading through it, the old
   simulator pretended we escaped at the safety-net price. In reality you get filled at a **worse** price.
   Correcting this showed our **worst-case dips (drawdowns) were about 10% bigger than we had believed.**
   A bet-size built on "smaller-than-real" risk is automatically **too aggressive.**

2. **We had just built better strategies.** We re-optimized the champions (see the before/after report,
   [GAP-03](./GAP-03-reoptimization-before-after.md)) and adopted three improved ones. New strategies →
   you must re-check the bet-size for the new set.

The task, in one sentence: **"Re-work the bet-size using honest risk numbers and the new strategies."**

---

## Part 2 — The two things that were actually wrong

### Problem A — rose-tinted risk (already described above)

The old bet-size was tuned on drawdowns that were ~10% too small. Betting on understated risk = betting too big.

### Problem B — the broken measuring-stick (the "STOP=40" bug)

This one is subtle but important. To compare trades **across different markets and speeds**, you must first
put every trade on a common scale — "how bad is a *full* loss on this trade?" A gold trade and a Nasdaq
trade lose totally different dollar amounts, so you can't just throw their raw numbers in one pile.

The old code put everything on a common scale by dividing every trade by a **fixed 40 points.** But the real
safety-nets are nowhere near 40 for most trades:

| Trade | Real safety-net (hard stop) |
|---|---|
| Gold, 15-minute | ≈ **8 points** |
| Nasdaq, 1-hour | ≈ **94 points** |
| Nasdaq, 4-hour | ≈ **151 points** |

So dividing all of them by 40 is like **measuring everyone's height with a ruler you always assume is 40 cm
long** — the resulting "heights" are meaningless, and worse, they're wrong in different directions for
different people. A "risk fraction" computed this way is **not** a real fraction of your account.

Why this matters extra: this is the **same family of mistake** (a silent hidden default number) that
*already* ruined two earlier studies on this project. So we now treat it as a serious bug, not a rounding
detail. The fix module even **prints the real safety-net it used for every trade**, so a wrong number can
never hide again.

---

## Part 3 — How we fixed it

Three changes, all in the direction of "stop lying to ourselves":

1. **Use honest fills** — the real (worse) price when the market jumps a safety-net.
2. **Give every trade its own ruler** — divide each trade by **its own** safety-net, not a fixed 40. Now a
   full stop-loss = exactly **−1 "risk unit"** for *every* trade, fairly, whether it's gold or Nasdaq. The
   resulting bet-size is finally a **true fraction of your account.**
3. **Look at the whole book** — pool both markets (Nasdaq + Gold) across the main speeds, about **10,500
   trades**, so the answer reflects the real portfolio, not one slice.

Then we run a **simulation** (a "Monte Carlo"): for a range of possible bet-sizes, we shuffle the real
trades into thousands of different possible orderings and, for each bet-size, measure three things —
**how much the account grows**, **its worst dip along the way (drawdown)**, and the ratio **growth ÷ dip**
(our preferred yardstick: reward per unit of pain).

---

## Part 4 — The trap we nearly walked straight into

The very first simulation run gave a tidy, exciting answer: *"the new champions let you bet 33% bigger."*
It would have been easy to write that down and move on.

We didn't — because of a house rule: **never trust one run of a random simulation.** We re-ran it with **8
different random shuffles** and watched where the "best bet-size" landed each time:

```
Best bet-size per shuffle (Nasdaq+Gold, current book):  0.6, 0.3, 0.8, 0.4, 1.2, 1.2, 0.1, 0.1  (%)
Best bet-size per shuffle (with the new champions):     0.8, 0.1, 0.3, 0.3, 0.1, 1.2, 0.8, 0.8  (%)
```

The "best" answer **jumps all over the place** — from 0.1% to 1.2%. That's the tell: **there is no sharp
best point.** The reward-per-pain is basically flat across a wide range, and the shiny "33% bigger" from the
first run was just the luck of *that one shuffle*. This check is exactly what stops us from shipping a
made-up number. (We call it the **noise check**, and it has saved us before.)

---

## Part 5 — The honest result

- There is a **wide comfortable zone**: risking roughly **0.1% to 0.8% of your account per trade** is all
  about equally good on reward-per-pain.
- **Above ~1%** things get bad quickly — the worst dip balloons past 20% of the account, and reward-per-pain
  falls. Full-throttle "Kelly" betting (~3%) means a ~50% dip — far too wild for us.
- **The new champions did not change the budget.** The current book and the re-optimized book are
  **indistinguishable** for sizing (reward-per-pain 0.938 vs 0.935 — the new one is if anything a hair
  lower). The improvement in the strategies is real, but it's **too small next to the big single-trade
  losses** to justify betting more. (This "the fat single-trade loss beats every edge" pattern keeps
  showing up across the whole project.)
- **Recommendation: risk about 0.25%–0.5% of your account per trade. Hard ceiling ~1%.** Same for both
  books. Do **not** size up for the new champions.

---

## Part 6 — What this means in actual dollars

"Risk 0.25% per trade" means: size the position so that if the trade hits its **full** safety-net, you lose
0.25% of your account. Because different trades have different safety-nets (and each point is worth different
money — a Nasdaq point is $20, a gold point is $100), the account you need to trade even **one contract**
safely differs a lot:

| Trade | Full stop-loss = | ...in dollars per 1 contract | Account needed to keep that ≤ 0.5% |
|---|---|---|---|
| Nasdaq 1-hour | 94 points × $20 | **$1,888** | ≈ **$378,000** |
| Nasdaq 4-hour | 151 points × $20 | **$3,020** | ≈ **$604,000** |
| Gold 15-minute | 8 points × $100 | **$800** | ≈ **$160,000** |

**Plain takeaway:** one contract of Nasdaq 4-hour puts $3,020 at risk; for that to be only 0.5% of your
account you'd need about $600k. With a smaller account you can only *safely* trade the cheaper, finer slots
(like gold 15-minute), or you are forced to bet above the safe ceiling — which the simulation says is where
the account-wrecking dips live.

---

## Part 7 — What went well, and what to still watch

**Went well:**
- We caught a fake "bet 33% bigger" before it could ship — the noise check did its job.
- We fixed the broken measuring-stick, so the bet-size number now genuinely means "% of your account."
- We used honest (worse, real) prices throughout.

**Still watch (we are being upfront):**
- The simulation uses a **simplified version of each trade** (entry + safety-net only; it ignores the
  time-limits and circuit-breakers the live strategies also use). It captures the *shape of the risk* well,
  which is what sizing needs, but a fuller version is a good next refinement.
- It assumes trades are **independent**. In reality bad trades can **cluster** (some gold slots hit their
  stop more than half the time), so a real losing streak can be worse than the typical simulated dip. Stay
  on the conservative side of the range for that reason.

---

## Bottom line (one paragraph)

We went back to the "how much do we bet per trade?" question because our risk numbers had been rose-tinted
and we had new strategies. Fixing a broken measuring-stick (which had been dividing every trade by a fake
fixed number) and using honest prices, we found there is **no single magic bet-size** — just a wide safe
zone of roughly **0.1%–0.8% of your account per trade**, with a hard ceiling near **1%**. The new champions
are better at making money but **do not let you bet more**, because the occasional large single-trade loss
dominates. **Bet about 0.25%–0.5% of your account per trade, and never above ~1%.**
