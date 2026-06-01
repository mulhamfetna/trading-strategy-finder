# Why Prophet, ARIMA, and Everything Else "Failed" — A Plain-Language Explainer

> You asked five things:
> 1. Why did Prophet fail?
> 2. Is it because it reads 4h candles — would 1-minute candles fix it?
> 3. What is the actual root cause?
> 4. What is "naive" in the first place?
> 5. Why did ARIMA fail too?
>
> This document answers all five, defines every term, and shows it visually. The short
> answer up front, then the long version.

---

## The 30-second answer

Nothing is "broken." Every model works correctly. They all "fail" for **one shared reason**:

> **The thing we asked them to predict — the next bar's price *move* — is almost pure randomness. The predictable part is tiny; the random part is huge. So the best any model can do is essentially tie the trivial "assume no change" guess.**

It is **not** because of 4h candles. **1-minute candles would make it worse, not better** (explained in §5). It is **not** a Prophet-specific or ARIMA-specific flaw — it's a property of liquid-futures price data itself.

---

## 1. The trap: price *looks* predictable, but price *moves* don't

Look at these two pictures of the **same** NQ data:

![Price vs returns](../plots/diagnostics/price_vs_returns.png)

- **Panel (A) — the PRICE.** Smooth, trending, "obviously" forecastable. Your eye traces the line and feels like you could guess where it goes next. This is the illusion.
- **Panel (B) — the RETURNS** (how much price *changed* each bar). Pure-looking noise scattered around zero. No visible pattern. **This is what a forecaster actually has to predict.**

Why does the model predict returns, not price? Because price is **non-stationary** — it wanders to new levels and never comes back (NQ went from \$21k to \$29k over the data). You cannot learn a stable rule from a quantity whose typical value keeps changing. Returns are **stationary** — they always hover around zero with roughly constant spread, whether NQ is at \$21k or \$29k. Stationary quantities are the only thing statistical models can learn from.

**Definitions:**
- **Price / level** — the actual dollar value of NQ at a bar's close (e.g. \$25,600).
- **Return** — the *change* from one bar to the next. We use the **log-return** = `ln(close_today / close_yesterday)`. A log-return of `+0.005` ≈ "+0.5% move". Log is used so gains and losses compose cleanly.
- **Stationary** — statistical properties (mean, variance) stay constant over time. Returns are ~stationary; prices are not.
- **Non-stationary** — mean/variance drift over time. Price is non-stationary (it trends to new levels).

---

## 2. What is "naive"? (the opponent everyone has to beat)

**Naive** is the simplest possible forecaster:

> **"Tomorrow's price = today's price."** In return terms: **"predict zero change."**

That's it. No math, no training, no parameters. It just echoes the last known close.

Why is it the benchmark? Because for a so-called **random walk** (a series whose steps are unpredictable), the mathematically *optimal* forecast of the next value **is** the current value. If prices are close to a random walk — and liquid-futures prices famously are — then naive is not a dumb baseline, it's **near the theoretical best**. Any "smart" model has to prove it can extract some real signal that naive misses. If it can't, it just adds noise and does slightly worse.

**Definition:**
- **Naive forecast (a.k.a. "persistence" or "random-walk forecast")** — predict the next value equals the most recent observed value. Error = whatever the next move turns out to be.

---

## 3. The root cause, shown in one chart

Here is the single most important picture in the whole study:

![Returns autocorrelation](../plots/diagnostics/returns_acf.png)

This is the **autocorrelation** of 4h log-returns.

**Definition — autocorrelation (ACF):** "How much does this bar's return tell you about a future bar's return?" Measured from −1 to +1.
- A value near **+1 or −1** = strong relationship = **predictable**.
- A value near **0** = no relationship = **unpredictable** (this bar's move says nothing about the next).

The red dashed lines are the **"white-noise band"** — the range within which a bar is statistically *indistinguishable from pure randomness*. **Term — white noise:** a sequence with zero autocorrelation at every lag; the formal definition of "unpredictable from its own past."

**What the chart shows:** almost every bar sits inside the red band. The biggest, at lag 1, is only **+0.068** — meaning the previous bar's return explains about **0.068² ≈ 0.5%** of the next bar's return. The other **99.5% is noise** a model cannot touch.

So the predictable signal exists, but it is **minuscule** relative to the randomness. That is the root cause of every "failure" in this study.

### The killer arithmetic

We can turn that into the exact dollar number:

```
naive RMSE  ≈  (typical price)  ×  (per-bar return volatility)
            ≈  $25,786          ×  0.00526
            ≈  $135.6
```

The **measured** naive RMSE was **\$133.6** — essentially identical. **Term — RMSE (Root Mean Squared Error):** the typical size of a forecast miss, in dollars. **Term — volatility:** the standard deviation of returns = how violently price jumps around per bar.

This identity is the whole story:

> The naive error is just **price × volatility**. That is an **irreducible noise floor**. A model can only beat it by predicting the *direction/size of the next move* better than chance — and §3's autocorrelation chart shows there's almost no such signal to find. So everyone lands at ~\$133–135. Naive wins because it spends *zero* effort and adds *zero* noise; the others each add a little estimation noise trying to chase a signal that's barely there.

---

## 4. So why, specifically, did **Prophet** "fail"?

Prophet's design assumption and this data's reality are mismatched.

**What Prophet is built for:** business time-series with **strong, repeating calendar structure** — daily web traffic, monthly sales, seasonal demand. Its internal model is literally:

```
prediction = trend(t)  +  seasonality(t)  +  holidays(t)
```

It decomposes a series into a smooth long-term **trend**, repeating **seasonal** cycles (weekly, yearly), and **holiday** bumps. It is excellent when those components are real and large (e.g. "every December sales spike 40%").

**What NQ 4h returns actually contain:** almost none of that. There is no reliable "returns are always positive on Tuesday" or "every March goes up". The seasonal/holiday/trend structure in *returns* is negligible (the trend lives in *price*, which we deliberately removed by switching to returns — see §1).

**The evidence Prophet itself gave us:** when we let Prophet's own cross-validation pick its flexibility knob (`changepoint_prior_scale`), it chose the **most rigid possible setting (0.001)**. In plain terms: **Prophet looked at the data and said "give me the least freedom to bend — there's no trend structure here worth fitting."** It correctly diagnosed that it had nothing to grab onto, flattened itself toward predicting ~zero return, and so landed a hair behind naive (it adds a tiny bit of seasonal-fitting noise that naive doesn't).

**Term — changepoint_prior_scale:** Prophet's knob for how freely the trend can bend. High = wiggly trend that chases recent moves; low = stiff, near-straight trend. CV picking "low" = "don't chase, there's no trend signal."

So Prophet didn't crash or malfunction — **it worked perfectly and the honest answer it produced was "there is nothing here for me to add."**

---

## 5. Would feeding it **1-minute candles** instead of 4h help? — No, the opposite

This is the most important practical question, and the intuition ("more data = better") is backwards here. Three reasons:

**(a) Finer bars = noisier, not clearer.** Volatility scales roughly with the square root of the time interval. A 1-minute bar's return is ~16× *smaller* and proportionally *noisier* relative to its own signal than a 4h bar. The signal-to-noise ratio gets **worse** as you zoom in, not better. The autocorrelation chart in §3 would look *flatter* (closer to pure noise) at 1-minute, not more structured.

**(b) Microstructure noise appears.** At 1-minute resolution you start measuring bid-ask bounce, individual large orders, and exchange-matching artifacts — none of which are forecastable price *direction*; they're just extra noise that swamps the already-tiny signal.

**(c) More bars ≠ more signal, just more noise samples.** Going from ~2,100 four-hour bars to ~500,000 one-minute bars gives you 250× more *rows*, but each row carries less signal. You'd train longer, hit memory limits (which already crashed the box once — see `15_system_crash_postmortem.md`), and land at the same or worse verdict.

**Where finer data *does* help — but it's a different question:** 1-minute candles are valuable for **execution** (where exactly to place a stop/entry within a 4h bar — which the live trading engine already uses via the dual-timeframe SL/TP) and for **volatility estimation** (realized volatility from 1-min data is much more accurate). It does **not** help **direction-of-next-move price forecasting**, which is what this study measured.

> **Bottom line:** 1-minute data improves *how you act inside a bar*, not *whether you can predict the next bar's move*. For this forecasting question it would lower accuracy, not raise it.

---

## 6. Why did **ARIMA** fail too? (and SARIMAX, and the deep nets)

ARIMA is the "proper" statistical tool for exactly this kind of problem, so its failure is the most telling.

**Term — ARIMA (AutoRegressive Integrated Moving Average):** a model that predicts the next value as a weighted combination of (a) recent past values — the "AutoRegressive / AR" part — and (b) recent past forecast errors — the "Moving Average / MA" part. It is the textbook approach to "predict the next step of a time series from its own past."

**Why it can't win here:** the AR part is *only as good as the autocorrelation it can exploit.* Look back at §3: the autocorrelation is ~0.068 at best and near-zero elsewhere. ARIMA fits coefficients to those autocorrelations — but when the autocorrelations are essentially zero, the fitted AR coefficients are essentially zero too, so **ARIMA's prediction collapses toward "predict the mean return" ≈ "predict zero" ≈ naive.** It cannot extract signal that isn't there.

In our results all three ARIMA implementations (pmdarima, statsmodels SARIMAX, Nixtla) landed within **±1% of naive** — slightly worse, because each spends a little accuracy *estimating* coefficients that turn out to be ~useless, and that estimation noise is a small penalty.

**The deeper models (LSTM, NBEATS, TFT via Darts) hit the same wall** for the same reason: a neural network can only learn a mapping from past→future if such a mapping exists in the data. The autocorrelation chart says it barely does. More model capacity just means more ways to overfit the noise.

**One nuance worth noting:** ARIMA and the LSTM got **directional hit-rates of ~53%** (slightly above the 50% coin-flip). So there *is* a whisper of real signal — just enough to call the *direction* right 53% of the time. But the *magnitude* of moves they predict is so small relative to actual moves that it never improves the dollar-RMSE. A 53% directional edge can still be tradeable (that's a separate question about position sizing and costs), but it does **not** make the price forecast "accurate."

---

## 7. The one-paragraph summary for a colleague

> We tried to forecast the next 4-hour NQ price. The honest finding: the *level* of price is non-stationary so we forecast *returns* instead, and 4h NQ returns are ~98–99% unpredictable noise (autocorrelation barely above the white-noise band). The trivial "naive" forecast — assume the price doesn't change — is therefore near-optimal, with an irreducible error of about `price × volatility ≈ $134`. Prophet's own cross-validation flattened itself to the stiffest setting (it found no trend to fit) and landed just behind naive; ARIMA/SARIMAX/StatsForecast and the deep nets (LSTM/NBEATS/TFT) all collapsed toward the naive prediction because there's no autocorrelation for them to exploit. Going to 1-minute candles makes the signal-to-noise *worse*, not better. The models didn't fail — they correctly reported that single-bar price direction on a liquid future is close to unpredictable. The ~53% directional hit-rate is the only whisper of signal, and it's a *direction/sizing* question, not a *price-accuracy* one.

---

## 8. What this implies for next steps (if you want to go further)

The study answered "can we forecast next-bar **price**?" with "no, and here's the proof." If the goal is a *useful* model, the productive pivots are to change **what** we predict, not **which** model:

1. **Predict volatility, not price.** Volatility (how big the next move is, ignoring direction) *is* strongly autocorrelated — calm periods cluster, wild periods cluster. This is forecastable and useful for risk/position sizing. (Tools: GARCH, or realized-volatility from 1-min data — *this* is where 1-minute candles genuinely help.)
2. **Predict direction as a classification problem** and optimise hit-rate / expected-value-after-costs, not RMSE. The 53% whisper might be real; measure it rigorously.
3. **Add information from outside the price series** — order-flow, VIX, macro events. The price's own past is nearly exhausted; new signal has to come from new data.
4. **Accept naive as the price forecast** and put the modelling effort into the trading *rules* on top of it (which is what the main `simple_strategy` system already does).

These are different studies with different success metrics — not more tuning of price-forecasting models, which §3 shows is a dead end.
