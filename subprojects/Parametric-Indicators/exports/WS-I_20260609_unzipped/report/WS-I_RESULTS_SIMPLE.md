---
name: ws-i-results-simple
description: WS-I.10 results in plain language — the what / how / when / why / how-much of the all-timeframe indicator search. No jargon.
type: report
status: complete
workstream: WS-I
---

# WS-I results — the simple version 🍼

Plain-English summary of the big search we just ran. No jargon. Five questions: **what, why, how, when, how much.**

---

## 1. WHAT did we do?

We have a trading robot. It looks at a chart of NQ (Nasdaq futures), and at certain moments it
decides to **buy** or **sell** one contract.

The robot has a bunch of **knobs** it can turn:

- **When to give up on a losing trade** (stop-loss — two of them, a soft one and a hard one).
- **When to take profit** (take-profit).
- **How calm or wild the market must be** before it's allowed to trade (a "volatility gate").
- **When to stop trading for the day** if it's losing too much (a "drawdown breaker").
- **15 helper signals** (called *indicators* — things like trend lines, momentum meters, etc.).
  Each one can be switched **on or off**, and we can say "only trade if at least **K** of them agree."

That's a *huge* number of knob combinations — billions. We can't try them all by hand.

So we asked a computer to **try thousands of combinations automatically** and keep the best ones.

---

## 2. WHY did we do it?

We wanted to answer: **"What's the best knob setting for each speed of trading?"**

"Speed" = how often the robot looks at the chart. We tested **7 speeds** (called *timeframes*):

| Speed | Looks at the chart every… |
|---|---|
| 4h | 4 hours (slow, patient) |
| 2h | 2 hours |
| 1h | 1 hour |
| 15m | 15 minutes |
| 5m | 5 minutes |
| 2m | 2 minutes |
| 1m | 1 minute (fast, hyperactive) |

We also had **one hard rule**: the robot is only allowed to be "good enough" if its **worst
losing streak stays under 25% of the money it makes.** (You can't make $100 if at some point
you were down $90 — too scary.) Settings that broke this rule were thrown out.

---

## 3. HOW did we do it?

- A smart search method (**NSGA-III**) — think of it like *breeding* the best knob settings:
  try a batch, keep the winners, mix them, try again, repeat. Over thousands of rounds it homes
  in on the good zones instead of guessing randomly.
- It juggled **3 goals at once**: make the most money 💰, have the smallest losing streak 📉,
  and win the highest % of trades ✅. (These fight each other — more money usually means bigger
  risk — so instead of one "winner" it gives a *menu* of good trade-offs.)
- To make sure a setting wasn't just lucky on one stretch of history, we **split the history into
  5 chunks** and scored each setting on all of them. The numbers below are the **middle** result,
  not the luckiest one.
- We ran it on a **big rented computer** (32-core AMD server) so it could grind all 7 speeds at
  the same time, overnight.

---

## 4. WHEN did it run?

- **Started:** evening of **8 June 2026**.
- **Finished:** morning of **9 June 2026** (the slowest speed, 1-minute, wrapped up ~07:23).
- **Total:** roughly **overnight (~8–9 hours)**, fully unattended — you closed the laptop and it
  kept going on the server.
- **Effort:** **3,000 attempts for each of the 7 speeds** = about **21,000 robot configurations
  tested and scored.**

---

## 5. HOW MUCH? (the results 💵)

For each speed, the single best money-maker that **passed the safety rule**:

| Speed | Typical profit | Worst losing streak | Win rate | Total profit over all history | How risky* |
|---|--:|--:|--:|--:|:--:|
| **4h** 🏆 | **$24,253** | $12,067 | 74% | **$56,040** | 18% — safe |
| **2h** | $15,132 | $10,835 | **90%** 🎯 | $55,836 | 17% — safe |
| **1h** | $12,284 | $4,418 | 71% | $33,280 | 24% — borderline |
| **15m** | $10,538 | $3,223 | 67% | $33,676 | 24% — borderline |
| **5m** | $9,943 | $4,344 | 66% | $36,710 | **11%** — safest ✅ |
| **2m** | $4,474 | $3,848 | 46% | $18,857 | 20% |
| **1m** | $1,876 | $1,167 | 80% | $7,681 | 15% |

<sub>*"How risky" = worst losing streak as a share of total profit. Lower = safer. Our rule capped it at 25%.</sub>

### What this says in one breath:
- **Slower is richer.** The patient 4-hour robot made the most money by far (**$56k** over the
  test history) while staying safe.
- **The 2-hour robot wins 9 out of 10 trades** — the most reliable, with almost the same profit.
- **The 5-minute robot is the calmest** — smallest risk of all.
- **The fast robots (1m, 2m) made the least** and behave twitchy — treat them with suspicion.

### Which helper signals kept showing up?
Two signals appeared in almost every winning combo — they're the MVPs:

- 📈 **`ema_trend`** — "is the price trending up or down right now?"
- 〰️ **`macd`** — "is momentum building or fading?"

A few others (`order_block`, `mfi`, `vwap`) showed up often on the slower speeds.

---

## ⚠️ The honest caveat (please read)

These results come from **one slice of history (2025 → 2026)**. That's like judging a
restaurant after eating there once — promising, but **not proof.**

- Treat these as **strong candidates to test further**, not "the answer."
- Before trusting any of them with real money, **re-run the exact chosen setting on the real
  dashboard** to confirm the numbers hold.
- Be extra skeptical of the 1-minute and 2-minute robots — fast trading racks up hidden costs
  these tests can under-count.

---

## Where to find the details

- **Full menu of good trade-offs per speed:** `optimize/results/<speed>_wsi_pareto.csv`
  (each row is a valid setting; pick by whether you prefer more money or less risk).
- **Pictures of those trade-offs:** `optimize/results/<speed>_wsi_pareto.png`
- **The technical report:** `optimize/reports/WS-I_RESULTS.md`
- **How the search itself works (technical):** `docs/NSGA3.md`
