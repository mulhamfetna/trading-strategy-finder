---
name: playbook-shareable-custom-keltner-rsi-stochastic-mfi
description: Fully self-contained, shareable playbook for one specific strategy configuration
  (Keltner Channel confirm + Relative Strength Index veto + Stochastic Oscillator both + Money Flow
  Index veto, confirmation threshold one). Full names, verbose, with a plain-language translation
  after every paragraph. No references to any other document; all knowledge is contained here.
type: playbook
status: shareable
---

# Strategy Playbook — "Keltner-confirm with Relative-Strength, Stochastic and Money-Flow filters"

This document explains, completely and from scratch, one specific trading-strategy configuration. It
assumes no prior knowledge and refers to no other document — everything you need is written here.
After every paragraph there is a short line in plain, simple language that re-states the same idea.

> **In plain words:** This page teaches one exact trading recipe from zero. Every hard paragraph is
> followed by an easy one that says the same thing simply.

---

## 1. The configuration this playbook describes (the exact settings)

This strategy uses four market indicators plus a small set of risk controls. The exact values are:

- **Keltner Channel** — role: *confirm* — period (number of candles) = **138**, multiplier = **3.5**.
- **Relative Strength Index** — role: *veto* — period = **53**, lower band = **40**, upper band = **65**.
- **Stochastic Oscillator** — role: *both (confirm and veto)* — main period = **39**, smoothing period = **35**, lower band = **23**, upper band = **52**.
- **Money Flow Index** — role: *veto* — period = **39**, lower band = **12**, upper band = **57**.
- **Confirmation threshold** (the minimum number of agreeing "confirm" indicators required) = **1**.
- **Entry trigger / pullback** = **0** (enter immediately, with no waiting and no pullback).
- **Cooldown** (how long the drawdown safety-switch stays off after it trips) = **0**.
- **Maximum drawdown safety level** = **100** (in account currency, i.e. one hundred dollars).
- **Point value** = **20** (each one-point move of the instrument is worth twenty dollars per contract).

> **In plain words:** The recipe turns on four tools — Keltner Channel, Relative Strength Index,
> Stochastic Oscillator, and Money Flow Index — and sets a few safety dials. The numbers above are
> the exact settings. Keep them handy; the rest of the page explains what each one does.

This configuration **does not by itself say** which timeframe to trade, how big the stop-loss or
take-profit is, or whether a separate volatility filter is on. Those are separate settings you must
choose before the strategy can place a real trade; this playbook documents only the parts listed
above.

> **In plain words:** This recipe only covers the indicators and a few safety dials. You still have
> to pick the candle size and your stop-loss / profit-target separately before it can actually trade.

---

## 2. How the strategy decides to trade (the big picture)

The strategy works in layers. First, an underlying price-box rule proposes a **direction** for each
candle — either "go long" (bet the price rises), "go short" (bet the price falls), or "do nothing".
The four indicators then act as a panel of judges that can either **approve** that proposed
direction or **block** it. A trade is opened only when the panel approves.

> **In plain words:** Something first suggests "maybe buy" or "maybe sell" on each candle. Then four
> judge-tools vote. The trade only happens if the judges allow it.

Each indicator is given one of three jobs, called its **role**:
- A **confirm** indicator can cast an *approve* vote when it agrees with the proposed direction.
- A **veto** indicator can cast a *block* vote when it disagrees with the proposed direction.
- A **both** indicator can do either — approve when it agrees, block when it disagrees.

> **In plain words:** Some judges can only say "yes" (confirm), some can only say "no" (veto), and
> some can say either "yes" or "no" (both).

The final rule for opening a trade is: **the trade is allowed only if (a) no veto-capable indicator
is currently blocking it, and (b) the number of approving "confirm" votes is at least the
confirmation threshold.** In this configuration the confirmation threshold is one, so you need **at
least one approval and zero blocks.**

> **In plain words:** To trade, you need at least one "yes" and absolutely no "no". One block from
> any blocking judge cancels the trade, even if others said yes.

---

## 3. Which indicator has which job in this configuration

- The **Keltner Channel** is a **confirm** indicator: it can only approve.
- The **Relative Strength Index** is a **veto** indicator: it can only block.
- The **Money Flow Index** is a **veto** indicator: it can only block.
- The **Stochastic Oscillator** is a **both** indicator: it can approve or block.

> **In plain words:** Keltner says only "yes". Relative-Strength and Money-Flow say only "no".
> Stochastic can say either.

This means the **approvers** (the indicators able to give the one approval you need) are the Keltner
Channel and the Stochastic Oscillator. The **blockers** (the indicators able to cancel a trade) are
the Relative Strength Index, the Money Flow Index, and the Stochastic Oscillator. Because the
confirmation threshold is one, a single approval from either Keltner or Stochastic is enough — but
any single block from Relative-Strength, Money-Flow, or Stochastic will still cancel the trade.

> **In plain words:** Only Keltner or Stochastic can give the "yes" you need. Relative-Strength,
> Money-Flow, or Stochastic can each give a "no" that kills the trade. You need one yes and no noes.

---

## 4. The Keltner Channel (the approver) — full explanation

The Keltner Channel is built from a smoothed average of recent closing prices, called an
**Exponential Moving Average**, computed over the last **138 candles**. (An exponential moving
average is a running average that gives more weight to newer prices and less to older ones.) The
channel also draws an upper and lower band around that average at a distance set by the
**multiplier (3.5)** times a measure of recent price range. In this strategy the **approval rule
only looks at the average line itself**: if the current price is **above** the 138-candle average,
the Keltner Channel approves a "go long" direction; if the price is **below** the average, it
approves a "go short" direction.

> **In plain words:** Keltner draws a slow average line over the last 138 candles. If price is above
> the line, it says "yes" to buying; if below, "yes" to selling.

Note carefully: because the approval only uses the average line, the **multiplier of 3.5 has no
effect on the approval vote** in this configuration — the multiplier only changes the width of the
upper and lower bands, which this approval rule does not use. It is recorded here for completeness
and because it is part of the saved settings, but it does not change any trading decision on its own.

> **In plain words:** The "3.5" number does not actually change anything here. It only widens bands
> that this rule ignores. It is written down only because it is part of the saved settings.

---

## 5. The Relative Strength Index (a blocker) — full explanation

The Relative Strength Index measures how strong recent gains are compared to recent losses, over the
last **53 candles**, and reports a number between zero and one hundred. High numbers mean price has
been rising strongly; low numbers mean it has been falling strongly. This configuration uses a
**lower band of 40** and an **upper band of 65**. The index is read as a momentum direction: numbers
at or above **65** mean "strongly up / possibly overbought", numbers at or below **40** mean
"strongly down / possibly oversold", and numbers in between lean up if above the midpoint (fifty) or
down if below it.

> **In plain words:** This tool counts whether recent candles went up more than down, over 53
> candles, as a score from 0 to 100. Above 65 = very up. Below 40 = very down. Around the middle =
> mild.

As a **veto (blocker)**, the Relative Strength Index blocks a trade that fights its momentum reading.
Concretely: when its reading is bullish (oversold, or above the midpoint), it **blocks "go short"
trades**; when its reading is bearish (overbought at or above sixty-five, or below the midpoint), it
**blocks "go long" trades**. In short, it refuses to let the strategy trade against the prevailing
momentum it sees.

> **In plain words:** This judge says "no" when you try to trade against the recent trend. If things
> are going up, it forbids selling; if going down, it forbids buying.

---

## 6. The Money Flow Index (a blocker) — full explanation

The Money Flow Index is similar to the Relative Strength Index but it also uses **trading volume**
(how many contracts changed hands), not just price. It looks at the last **39 candles** and produces
a number from zero to one hundred that rises when buying pressure (price up on strong volume)
dominates and falls when selling pressure dominates. This configuration uses a **lower band of 12**
and an **upper band of 57**.

> **In plain words:** This tool is like the previous one but it also counts how much was traded, over
> 39 candles. High = strong buying. Low = strong selling.

As a **veto (blocker)** it works the same way as the Relative Strength Index: when its reading is at
or above the upper band of **57** (treated as "overbought"), it **blocks "go long" trades**; when its
reading is at or below the lower band of **12** ("oversold"), it **blocks "go short" trades**; in
between it leans the same up/down way around the midpoint. Because the upper band is set quite low
(fifty-seven), this blocker will frequently treat the market as "overbought" and therefore **block
buy trades often** — that is a direct consequence of the chosen numbers and you should expect it.

> **In plain words:** This judge says "no" to buying whenever buying pressure is high (above 57) and
> "no" to selling whenever selling pressure is very high (below 12). Because 57 is a low bar, it will
> say "no" to buying a lot of the time.

---

## 7. The Stochastic Oscillator (approver and blocker) — full explanation

The Stochastic Oscillator measures where the current price sits inside the high-to-low range of the
last **39 candles**, as a number from zero to one hundred (zero = at the bottom of the range, one
hundred = at the top). That raw number is then smoothed over **35 candles** to reduce noise. This
configuration uses a **lower band of 23** and an **upper band of 52**.

> **In plain words:** This tool asks "within the last 39 candles, is price near the top or the bottom
> of its range?" — then it averages that answer over 35 candles to keep it steady.

Because its role is **both**, it can approve or block. When its reading is at or below the lower band
of **23** ("oversold") it favours upward trades: it **approves "go long" and blocks "go short"**.
When its reading is at or above the upper band of **52** ("overbought") it favours downward trades:
it **approves "go short" and blocks "go long"**. Note that the upper band here is set very close to
the midpoint (fifty-two), so the tool spends most of its time on the "favour downward" side; this
makes it lean toward approving sell trades and blocking buy trades much of the time, which again is a
direct result of the chosen numbers.

> **In plain words:** Near the bottom of its range it says "yes to buy, no to sell". Near the top it
> says "yes to sell, no to buy". Because the top bar is set very low (52), it spends most of its time
> saying "yes to sell, no to buy".

---

## 8. Putting the votes together (a worked rule)

On each candle where the underlying box rule proposes a direction, the software reads all four
indicators and applies the rule from Section 2: **allow the trade only if there is at least one
approval and no block.** A worked example: suppose the box proposes "go long". The trade opens only
if (the Keltner Channel sees price above its 138-candle average **or** the Stochastic Oscillator is
oversold) **and** none of the Relative Strength Index, the Money Flow Index, or the Stochastic
Oscillator is in a state that blocks longs. If even one of those three is blocking longs, the long
trade does not open.

> **In plain words:** To actually buy, at least one approver must say "yes to buy" and none of the
> three blockers may say "no to buy". One "no" cancels it.

A practical observation about these specific numbers: the Money Flow Index blocks buys whenever its
reading is at or above fifty-seven, and the Stochastic Oscillator blocks buys whenever it is at or
above fifty-two. Both of those bars are low, so **buy trades will be blocked frequently** and the
configuration will tend to allow **sell trades more often than buy trades.** This is not a bug; it is
what the chosen settings mean.

> **In plain words:** With these exact numbers the strategy will say "no" to buying a lot, and will
> tend to take more sell trades than buy trades.

---

## 9. Warm-up: why the strategy is silent at the start

Every indicator needs a minimum number of finished candles before its reading can be trusted; until
then it stays neutral (it neither approves nor blocks). The required number of candles, called the
**warm-up**, for this configuration is:

- Money Flow Index: **39 candles**.
- Relative Strength Index: **53 candles**.
- Stochastic Oscillator: **73 candles** (its main period of thirty-nine plus its smoothing of
  thirty-five, minus one).
- Keltner Channel: **138 candles**.

> **In plain words:** Each tool must watch a certain number of candles before it is allowed to vote.
> Until then it stays quiet. The counts are 39, 53, 73, and 138 candles.

Because a trade needs at least one **approval**, and the only approvers are the Stochastic Oscillator
(ready after 73 candles) and the Keltner Channel (ready after 138 candles), **no trade can occur at
all until at least 73 candles have passed** — that is the first moment any approver can speak. The
strategy is therefore completely silent for the first 73 candles, and only gains its full set of
approvers after 138 candles. The number of real days this represents depends on the candle size you
choose: for example, on four-hour candles roughly five candles form per trading day, so 138 candles
is on the order of twenty-eight trading days; on one-hour candles it is fewer days; on daily candles
it is many months. Always make sure the data window you test is comfortably longer than 138 candles,
or the Keltner approver never wakes up.

> **In plain words:** Nothing can trade for the first 73 candles, because the only tools that can say
> "yes" aren't ready before then. Keltner isn't ready until 138 candles. How long that is in days
> depends on your candle size — make sure you have far more than 138 candles of data.

---

## 10. The risk and safety dials

**Entry trigger / pullback = 0.** This means that once a trade is approved, it is entered
**immediately at the signal price**, with no waiting period and no requirement for the price to pull
back first. A non-zero value would make the strategy wait or demand a pullback before entering;
zero removes that.

> **In plain words:** When the judges approve, the trade goes in right away — no waiting, no "wait
> for a dip first".

**Cooldown = 0.** The strategy has a drawdown safety-switch (described next) that can pause trading.
The cooldown is how many trades it stays paused after the switch trips. A cooldown of zero means the
switch, even if it trips, **releases immediately and pauses essentially nothing** — so in this
configuration the safety-switch provides almost no real protection. If you want genuine pauses after
a losing stretch, this number must be greater than zero.

> **In plain words:** The "take a break after losses" feature is set to zero, so it basically never
> takes a break. If you want real breaks, raise this number above zero.

**Maximum drawdown safety level = 100 dollars.** "Drawdown" is how far the running account balance
has fallen from its highest point so far. This dial is the loss-from-peak level at which the safety
switch reacts. Here it is set to one hundred dollars, which is **very small** relative to the size of
a single trade on a twenty-dollar-per-point instrument. Combined with the cooldown of zero (which
releases the switch instantly), this safety system will trip almost constantly yet pause nothing,
so in practice it does not limit your losses in this configuration. Treat risk control as effectively
**off** here unless you raise both this level and the cooldown.

> **In plain words:** The "stop trading if I lose this much from my best point" alarm is set to just
> $100, which is tiny, and the break length is zero — so the alarm rings constantly but does nothing.
> Real protection needs a bigger number here and a non-zero break.

**Point value = 20 dollars.** Every one-point move of the instrument's price is worth twenty dollars
per contract. So if a trade moves ten points in your favour, that is two hundred dollars per
contract; ten points against you is a two-hundred-dollar loss per contract. Use this to translate any
point-based stop-loss or target you set into real money.

> **In plain words:** One point of price movement equals twenty dollars per contract. Multiply points
> by twenty to get dollars.

---

## 11. What is NOT defined here, and why it matters

This configuration specifies the four indicators, the confirmation threshold, the entry trigger, the
cooldown, the maximum-drawdown level, and the point value. It does **not** specify: the **candle size
(timeframe)**, the **stop-loss distance**, the **take-profit distance**, any **volatility filter**,
the **trade direction flip**, or the **date range** to test. The strategy cannot place a complete,
realistic trade until those are chosen, because the stop-loss and take-profit decide where each trade
exits and the timeframe decides how often it acts. Choose them deliberately before relying on any
result.

> **In plain words:** This recipe is missing the candle size and the stop-loss / profit-target. Pick
> those yourself before trusting it — without them the strategy can't really finish a trade.

---

## 12. Honest cautions

This configuration leans heavily toward sell trades and blocks buys often (Sections 6–8); its safety
switch is effectively disabled (Section 10); and it is silent until at least 73 candles have passed
(Section 9). None of these are errors — they are the direct, predictable meaning of the numbers you
chose. Before trusting any profit figure, test it over a date range far longer than 138 candles, set
a real stop-loss and take-profit, and raise the maximum-drawdown level and cooldown if you want
genuine loss protection. And remember that any single historical test is evidence, not proof.

> **In plain words:** Expect mostly sells, few buys, almost no safety net, and silence for the first
> 73 candles — that is what these numbers do. Add a real stop-loss, a real profit-target, and real
> safety limits before trusting it, and don't treat one backtest as the final truth.

---

## 13. One-line settings table (for re-entry into the software)

| Setting (full name) | Software field | Value |
|---|---|---|
| Keltner Channel — role / period / multiplier | keltner: mode / n / m | confirm / 138 / 3.5 |
| Relative Strength Index — role / period / lower / upper | rsi: mode / n / lower / upper | veto / 53 / 40 / 65 |
| Stochastic Oscillator — role / period / smoothing / lower / upper | stochastic: mode / n / d / lower / upper | both / 39 / 35 / 23 / 52 |
| Money Flow Index — role / period / lower / upper | mfi: mode / n / lower / upper | veto / 39 / 12 / 57 |
| Confirmation threshold | k | 1 |
| Entry trigger / pullback | retrace_amount / wait_bars | 0 / 0 |
| Cooldown | cooldown | 0 |
| Maximum drawdown safety level | dd_limit | 100 |
| Point value | pv | 20 |

> **In plain words:** This table is the cheat-sheet to type the exact recipe back into the program.
