---
name: explained-for-beginners
description: A plain-language ("for babies") walkthrough of the whole model-research effort — what we tried to do, why the price models failed, the difference between "the science says no" and "the wiring broke", and which improvements are actually worth chasing.
type: explainer
---

# What we did, why it didn't predict price, and what's actually worth trying — explained simply

No jargon left undefined. If you read only one section, read **§2** and **§9**.

---

## 1. The goal, in one sentence

We have NQ (Nasdaq futures) candles. We wanted a model that, looking at the past, can
**guess the next 4-hour candle's closing price** better than a dumb guess. If we could,
we'd trade on it.

A **candle** = one time slice of the market showing 4 numbers: where price Opened, the
Highest it went, the Lowest, and where it Closed. "4h candle" = each candle covers 4 hours.

---

## 2. The single most important idea: the "naive" yardstick

Before judging any clever model, you need something dumb to compare against. Ours is the
**naive guess**:

> **"Tomorrow's price = today's price."** (Next candle's close = this candle's close.)

That's it. No math, no learning. It sounds stupid, but for things that wander randomly
(like prices), it's shockingly hard to beat. It's our **yardstick**: a model is only
useful if it beats the naive guess. We measure "how wrong" with **RMSE** — basically the
typical size of the error in dollars (smaller = better).

**The whole story of this project:** *nothing beat the naive guess.*

---

## 3. Why predicting the next price is so hard (the honest reason)

Imagine flipping a coin and taking one step left (tails) or right (heads) each time. That's
a **random walk**. Where you are next depends almost entirely on where you are *now*, plus
an unpredictable coin flip. The best guess for your next position is… your current position
(the naive guess). The coin flip itself is **un-guessable** — that's what "random" means.

4-hour price moves behave almost exactly like that coin flip. We proved it two ways:
- **Direction is a coin toss:** every model guessed "up or down next" correctly about
  **50%** of the time — same as flipping a coin.
- **There's no echo in the data.** We measured **autocorrelation** (does the last move
  tell you the next move?). For price moves it was ~**0.07** — basically zero. Statisticians
  call near-zero-autocorrelation noise **"white noise"**: pure static, no pattern to learn.

So the bad news isn't that our models were weak. It's that **the thing we asked them to
predict has (almost) no predictable pattern.** No model can learn a pattern that isn't there.

---

## 4. Who competed (the contestants), in plain words

We ran a tournament of forecasting methods, simplest to fanciest:

| Model | What it is, simply |
|---|---|
| **naive** | "next = last." The dumb yardstick. |
| **prophet** | Facebook's tool for trend + seasonal cycles (good for things like website traffic). |
| **arima / sarimax** | Classic statistics that fit recent ups-and-downs with a formula. "regressors" = also fed extra clues (the box levels). |
| **statsforecast** | A fast auto-tuning version of ARIMA. |
| **darts-rnn (LSTM)** | A neural network with "memory" of recent steps. |
| **darts-nbeats** | A bigger neural network specialized for time series. |
| **darts-tft** | A **transformer** — the same family as ChatGPT, very large and data-hungry. |
| **neuralprophet** | Prophet + neural network. |

"plain" = model sees only past prices. "regressors/covariates" = model *also* sees extra
clue-columns (our box levels) hoping they help.

---

## 5. The final scoreboard (lower error = better)

| Place | Model | Typical error (RMSE, $) | Better than the dumb guess? |
|---|---|---:|---|
| 🥇 1 | **naive (dumb guess)** | **133.6** | — (it's the yardstick) |
| 2–7 | prophet, arima, sarimax, rnn-plain, statsforecast | 134–135 | **No** — basically tied, a hair worse |
| 8–10 | rnn+clues, nbeats, nbeats+clues | 144–182 | **No** — clearly worse |
| 11–12 | tft (transformer) | 329–427 | **No** — way worse, it fell apart |

Read it top to bottom and you see the punchline: **the fancier and bigger the model, the
WORSE it did.** The dumb guess won.

---

## 6. The causes of failure — and a crucial distinction

There are **two completely different kinds of "failure"** here. Don't mix them up.

### 6a. "Failure" that is actually the correct scientific answer
These models didn't crash — they ran fine and **lost to naive**. That's not a bug; that's
the experiment *succeeding* and telling us the truth:
- **The signal isn't there** (§3). You can't predict a coin flip.
- **The extra clues didn't help.** Every "+clues" model did *worse* than its plain version
  (e.g. rnn −0.5% → −8%). The box levels carry no next-bar price information.
- **Big models "hallucinate" on small data.** The transformer (TFT) has millions of dials
  and we only have ~1,500 candles to train on. With nothing real to learn, it invents
  patterns and produces wild guesses — that's why its error is 3–4× worse. Like asking a
  genius to find a deep meaning in random static: they'll confidently make one up.

**Lesson:** these are not things to "fix." They are the answer: *next-bar price is
unpredictable.*

### 6b. Failure that was just broken plumbing (real bugs we fixed)
Separately, three of the neural runs **crashed** at first — nothing to do with the science,
just wiring problems in our code/environment. We fixed each:

| What broke | Baby explanation | Fix |
|---|---|---|
| GPU was "paused" for months | Our old computer's graphics card couldn't do the heavy math; the big models also ran out of memory. | Moved to the new server (strong GPU + lots of memory). |
| GPU "invisible" to the software | The server's GPU model isn't officially supported, so the software pretended it wasn't there. | One magic setting (`HSA_OVERRIDE_GFX_VERSION=10.3.0`) tells it "treat this card as the supported one." |
| `NameError` crash | We used a tool in the code without first "getting it off the shelf" (missing import line). | Added the import. |
| "covariates" crash | We handed the clue-columns to the model the wrong way: one model only accepts clues labelled "known for the future," and our two clue-tables were misaligned by a row. | Labelled clues correctly per model + aligned the tables. |
| Missing library | The deep-learning engine (`pytorch-lightning`) wasn't installed. | Installed it (without breaking the GPU one). |

**Lesson:** 6b is "we made the experiment run." 6a is "the experiment told us the answer."
We needed to clear all of 6b just to be *sure* 6a was real and not an excuse.

---

## 7. What we *actually* tried (the journey)

1. **Locally**, on a weak PC: ran the simple models (naive, prophet, arima, sarimax,
   statsforecast). All tied or lost to naive.
2. The **neural** models (RNN, NBEATS, TFT) were **paused** — the local GPU didn't work and
   memory ran out. NeuralProphet was **blocked** for a different reason (it can't handle the
   weekend gaps in futures data — a structural mismatch).
3. Got a **new server** with a real GPU. Set up a clean workflow: data stays on our
   computer, only the *training* runs on the server, results come back to us.
4. **Ran all six neural models on the GPU**, fixed the bugs in §6b, and built the final
   12-model scoreboard.
5. Earlier, we also pivoted and tried predicting **volatility** instead of price (see §8) —
   and that one actually worked.

So the honest tally: **~21 model setups tested.** Champion: the dumb guess.

---

## 8. What's actually worth improving (where the real opportunity is)

Stop trying to predict the next *price* — that door is closed. The doors that are **open**:

1. **Predict volatility / range instead of price.** We can't say *where* price goes, but we
   *can* predict **how big the move will be** (the candle's high-to-low range). That signal
   is real — autocorrelation ~0.5 (vs 0.07 for direction). A simple model (called **HAR**)
   beat naive by ~16% here. Volatility is the genuinely predictable thing. ✅ *already shown
   to work — worth pushing further.*
2. **Know when to flip the strategy.** Our trades made money in 2025 and lost in 2026 —
   doing the *opposite* in 2026 would have won. We built a smart, small-memory detector
   (**CUSUM**) that spots when the edge flips and switches sides. Promising, but only one
   such flip has ever happened in our data, so it needs more history to trust. ✅ *worth
   hardening.*
3. **Use volatility as a safety gate.** When the predicted move is dangerously big, sit out.
   This reduces losses even if it doesn't improve price prediction.
4. **Get more data.** More years and more instruments would (a) let the big models actually
   learn, and (b) let us trust the flip detector. The single biggest unlock.
5. **Combine signals.** Only flip the strategy when *two* independent signals agree (the
   edge-flip detector **and** a volatility-regime change) — much safer than trusting one.

What is **NOT** worth more effort: bigger/fancier price-prediction models. We now have proof
(LSTM, NBEATS, transformer, all with and without clues) that they don't beat the dumb guess.
Adding more of them just wastes time.

---

## 9. The whole thing in one paragraph

We tried hard to predict the next 4-hour price — about 21 model setups, from a one-line
"dumb guess" up to a ChatGPT-style transformer, finally running the heavy ones on a new GPU
server. **Nothing beat the dumb guess.** That's not because our models were bad; it's
because next-bar price moves are essentially a coin flip (we measured it: ~50% direction
accuracy, near-zero pattern), and the fancier the model, the more it *hallucinated* patterns
that weren't there — so it did worse. A handful of crashes along the way were just plumbing
bugs (GPU settings, a missing library, mislabeled inputs), which we fixed to be certain the
"can't beat naive" result was real. The good news: while price is unpredictable,
**volatility (how big the move is) IS predictable**, and a small **flip detector** can tell
us when to switch sides. Those two — plus simply getting more data — are where the real
improvement lives. Chasing more price-prediction models is a dead end.
