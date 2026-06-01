# Is "Return" Useful Information At All — or Just Noise With Workarounds?

> The capstone question after docs 16–22. After proving that no model beats naive on price,
> that exp/gross/simple are all the same, and that no monotone workaround escapes the noise band —
> the natural doubt is: **is "return" useful information in any form, or is it a dead end we keep
> dressing up?**
>
> **Verdict: Return is essential information — but it has THREE jobs, and we spent the whole study
> demanding it do the ONE job it's bad at.** It is not "useless with workarounds." It is
> "indispensable for two jobs (representation + risk/volatility) and near-useless for one
> (next-direction)." The mistake was the target, not the quantity.

---

## 1. Reframe: "return" isn't one thing, it has three jobs

The confusion comes from treating "use returns" as a single decision. It's really three separate uses, with three different answers:

| Job | What it means | Is return useful for it? |
|---|---|---|
| **A. Representation** | convert raw price → a learnable, stationary quantity | **YES — essential, not a workaround** |
| **B. Predict next *direction*** | forecast the sign of the next move (up/down) | **NO — near-useless, no workaround rescues it** |
| **C. Predict/measure *magnitude* (volatility & risk)** | forecast/measure how big moves are; size positions; measure risk | **YES — this is where the value was hiding** |

The whole study (Phases 1–D) was Job B. That's why it "failed." But Jobs A and C are where returns are not just useful but irreplaceable.

---

## 2. Job A — Representation: returns are ESSENTIAL (and this is not a workaround)

Converting price to return is the step that makes the data **stationary** — properties constant over time, which is the precondition for *any* statistical model to learn anything. This is not a trick or a workaround; it is the correct, necessary representation.

**Proof from our own data:** the original `prophet_test.py` forecast *raw price* and reported RMSE = \$5,625. Re-expressed correctly via returns + walk-forward, the honest naive RMSE is \$133.6 — a 42× difference. Most of that gap was the failure to use returns. So:

> **Using returns instead of raw price is worth ~42× in error.** That alone settles "is return useful information" — yes, enormously, as a representation.

And the *shape* of the return (log / simple / gross / exp) doesn't matter for this job — they're monotone relabelings of each other (docs 20, 22). Convention: use **log returns** for additivity + symmetry. But any shape gives the stationarity benefit.

**Verdict on Job A: essential. The 42× error reduction is the benefit.**

---

## 3. Job B — Predict next direction: near-useless, and no workaround helps

This is the job that generated all the "failure" findings, and the honest conclusion is blunt:

- Signed-return autocorrelation ≈ **0.07** — barely above pure noise (docs 16, 21).
- Every model (Prophet, ARIMA×3, LSTM, NBEATS, TFT) collapsed to ~naive (the leaderboard).
- Every transform workaround — log, gross, simple, `exp(R)`, `exp(100·R)` — stays at ~0.07 because they're monotone and preserve the unpredictable sign (doc 22).
- The "near-zero values" was never the issue; the issue is there is **almost no information** about next direction in the past (doc 21: collapse, not curable by relabeling).

> **For predicting next direction, returns (in any shape, with any workaround) carry almost no usable information.** This is the part that feels like "useless info with workarounds" — and for *this job*, that feeling is correct. Stop trying to rescue it.

**Verdict on Job B: near-useless. Accept it; don't keep building workarounds.**

The one residual: a ~53% directional hit-rate (vs 50% coin-flip) in ARIMA/LSTM. A whisper of signal — possibly tradeable with the right sizing and costs, but *not* a "useful price forecast." That's a separate classification/EV study, not a price-RMSE one.

---

## 4. Job C — Magnitude / volatility: returns are GOLD here

This is the payoff the study kept pointing at from every angle. The return splits as:

```
return  =  sign (direction, ~noise)  ×  magnitude (volatility, predictable)
```

The **magnitude** — `|R|`, `R²`, or the bar range `high−low` — is *derived from the return* and is strongly autocorrelated:

| quantity (from return) | autocorrelation | predictable? |
|---|---:|---|
| signed return `R` (Job B) | 0.07 | no |
| `|R|` (magnitude) | **0.30** | yes |
| `R²` (variance) | **0.15** | yes |
| range `high−low` | **0.56** | strongly |

So returns **are** highly useful information — *once you extract magnitude instead of direction.* And magnitude/volatility is exactly what the live trading system needs:
- **Stop-loss / take-profit distances** (the dual-SL/TP engine).
- **Position sizing** (smaller when predicted volatility is high).
- **Risk measurement** (volatility = std of returns; drawdown; Sharpe).

> **For magnitude/volatility, returns are the indispensable raw material.** This is not a workaround — it's the correct use of the information that was there all along.

**Verdict on Job C: highly useful. This is the real value of returns for this project.**

---

## 5. The honest one-line answer to your question

> **Returns are useful information — just not for guessing the next direction (Job B), which is what we spent the study on. They are essential as the stationary representation (Job A, worth 42× in error) and as the raw material for volatility/risk (Job C, where the real forecasting signal lives). The "workarounds" (exp, scaling, gross-vs-simple) were all attempts to rescue Job B, and they're genuinely useless because Job B has no signal to rescue. The fix is not a better workaround — it's redirecting returns from the direction question to the magnitude question.**

---

## 6. So what should actually be done with returns (decision table)

| If the goal is… | Use returns how? | Useful? |
|---|---|---|
| Make price data model-ready | transform price → log-return (stationarity) | ✅ essential |
| Forecast next bar's **price/direction** | …don't. It's ~unpredictable; naive ties everything | ❌ accept naive |
| Forecast next bar's **range/volatility** | model `|R|` / range (GARCH, EWMA, realized-vol from 1-min) | ✅ the real lever |
| Size positions / set stops | use predicted volatility from returns | ✅ direct payoff |
| Measure realized risk/performance | std of returns, Sharpe, drawdown | ✅ always |
| A faint directional edge | classify `sign(R)`, optimise hit-rate after costs (not RMSE) | ⚠️ maybe, separate study |

---

## 7. Connection to the rest of the project

This resolves the entire meta-prophet arc:

- Docs 16, 18 — *why price/direction forecasting failed*: Job B has no signal.
- Docs 19, 20, 22 — *return shapes & transforms are equivalent*: shape doesn't matter for Job B, and no monotone workaround helps.
- Doc 17 — *OHLC / range is predictable*: that's Job C surfacing through the candle.
- This doc — *the verdict*: returns are essential for Jobs A & C, useless for B; pivot to C.

**Recommended next study (Phase F):** forecast **range/volatility** from returns (`|R|`, range), baselined against naive-range and EWMA, modelled with GARCH and optionally realized-volatility from 1-minute data — scored as lift-over-naive on range. That is the study where returns finally pay off, and it feeds straight into the live engine's stop/sizing logic.

---

## 8. One-paragraph summary

"Is return useful information, or noise with workarounds?" — it's useful, but for different jobs than the one we tested. As a **representation**, converting price to return is essential and worth ~42× in error (it makes the data stationary; the original raw-price attempt scored \$5,625 vs the honest \$134). As a **next-direction predictor**, returns in *every* shape (log/simple/gross/exp) carry almost no usable signal (autocorrelation 0.07), and the exp/scaling workarounds are genuinely futile because they're monotone and can't manufacture predictability — this is the part that feels useless, and for this job it is. But as the raw material for **magnitude/volatility** (`|R|` 0.30, range 0.56), returns are gold, and that's precisely what the live trading system needs for stops and sizing. The takeaway: returns aren't the problem and weren't a workaround — we were aiming them at direction (no signal) instead of magnitude (strong signal). Redirect, don't discard.
