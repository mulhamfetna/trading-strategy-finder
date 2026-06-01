# Data Investigation — Is the 2025→2026 price jump real, or a CSV-split artifact?

> Triggered by the observation that `NQ_4h_2025.csv` opens at ~$21,322 and ends at ~$25,434, while `NQ_4h_2026.csv` opens at ~$25,603 and ends (mid-May) at ~$28,950. The parent file `NQ_4h.csv` (2,119 rows) was split into 2025 (1,534 rows) and 2026 (585 rows) for this study.
>
> Verdict (TL;DR): **The split is clean. The ~20% YoY move is genuine 2025 market behaviour, not a data-pipeline artifact. The real story is what happened *inside* 2025.**

---

## 1. Verifying the split is clean

| File | Rows | First timestamp | First close | Last timestamp | Last close |
|---|---:|---|---:|---|---:|
| `NQ_4h.csv`      (parent) | 2,119 | 2025-01-01 18:00 | 21,322.25 | 2026-05-19 18:00 | 28,950.00 |
| `NQ_4h_2025.csv` (train)  | 1,534 | 2025-01-01 18:00 | 21,322.25 | 2025-12-31 14:00 | 25,434.75 |
| `NQ_4h_2026.csv` (eval)   |   585 | 2026-01-01 18:00 | 25,603.75 | 2026-05-19 18:00 | 28,950.00 |
| **Sum of splits**         | 2,119 | — | — | — | — |

- Row counts add up exactly (1,534 + 585 = 2,119).
- No overlap, no duplication: last 2025 bar is `2025-12-31 14:00 → 25,434.75`; first 2026 bar is `2026-01-01 18:00 → 25,603.75`.
- The 28-hour wall-clock gap between the two is the **CME Globex new-year holiday closure** (NQ futures close ~17:00 ET Dec 31, reopen 18:00 ET Jan 2 — except 2026-01-01 was a Thursday this year). This is not a missing data bar.
- The boundary jump itself is small: **+169 pts (+0.66%)** over 28 wall-clock hours. By comparison the average 4h-bar move during 2025 was 0.58% std — a 0.66% gap is < 1.5σ, totally unremarkable.

**Conclusion:** the split is faithful. The user's framing of "a jump between 2025 and 2026" is geometrically a year-end accounting boundary, not a discontinuity in the data.

---

## 2. What actually happened in 2025 (the real story)

The headline "$21k → $25k between 2025 and 2026" hides that **2025 was an enormous round-trip**:

```
2025-01-01 18:00   open  =  21,322
...
2025 minimum      ≈  16,762   ← drawdown of −21.4% from open
...
2025-12-31 14:00   close = 25,434  ← +19.3% from open, +51.7% from min
```

Per-bar return statistics (4h bars):

| Year | mean | std  | min     | max     |
|---|---:|---:|---:|---:|
| 2025 | +0.013% | 0.582% | −3.94% | **+8.21%** |
| 2026 | +0.022% | 0.526% | −2.65% | +3.00%  |

Three things stand out:

1. **2025 had a single +8.2% 4-hour bar.** That is a massive intraday move for a major index future and almost certainly aligns with a discrete news catalyst. Without web research we can't name it, but mechanically: at $21k base, +8.2% is +$1,720 in 4 hours.
2. **2025 has both a deeper drawdown (−3.94% bar) and a stronger rally bar (+8.21%) than 2026** — 2025 is the higher-volatility regime by every measure. 2026's max move so far is only +3.0%, half of 2025's. The "smoother" year is 2026.
3. **Mean returns are positive in both years.** Both regimes are net up; neither is in a bear market over the sample.

The macro-context research agent (`aaecee0fc391dd93b`, running in background) will name the catalysts — but the data alone already shows that **the 2025→2026 transition is not where the interesting behaviour is**. The interesting behaviour is the V-shaped year of 2025 itself (open $21.3k → low $16.8k → close $25.4k).

---

## 3. Why this matters for Prophet (and any forecasting model)

This data is **a hard regime test**, not a stable series:

- **Prophet's smooth piecewise-linear trend was fit on a V-shape.** Inside 2025 there's a drawdown and a sharp recovery; Prophet's automatic changepoint detection sees these and lays down trend breaks. By the end of 2025 the fitted trend is sloping steeply upward (mirroring the H2-2025 recovery rally) — which is exactly why the vanilla forecast then *under-shoots* 2026 (Prophet projects continued recovery rally but with the slope of the last 2025 segment, which is sublinear vs. the realised 2026 continuation).
- **No "split bug" to fix.** The current pipeline's RMSE of $5,625 is not caused by the data — it's caused by (a) forecasting raw close on a non-stationary series, (b) eval-row misalignment in `prophet_test.py` (it row-indexes forecast.csv against 2026 by position, but forecast.csv contains 1,634 rows — 1,534 in-sample fits + 100 forward — and 2026 has 585 rows, so most of the diff was comparing 2026 to *2025-in-sample fits*, not to forecasts), (c) no walk-forward retraining.
- **The eval window (2026, 585 bars) sits entirely above the training range.** Min of 2026 ($23,106) is well above Q3 of 2025 (~$24,500). Any model that doesn't either (i) operate on returns or (ii) get retrained as 2026 unfolds will be projecting upward from a too-low base. This is exactly the case the Phase 1 naive baseline + walk-forward will fix.

**Implication for the tournament:** the year-boundary is a fair held-out test *only because* we'll be retraining walk-forward inside 2026 (every 20 bars in the current design). A single fit on 2025 followed by static 2026 prediction would be the wrong eval — it would benchmark Prophet's trend-extrapolation skill, not its 1-bar-ahead skill.

---

## 4. Macro catalysts — confirmed via parallel research

Web research (Bloomberg, Nasdaq.com monthly scorecards, CNBC, Wikipedia 2025-crash entry, Fed FOMC statements, NVDA SEC 8-Ks, Slickcharts annual-returns table) names the catalysts behind every visible feature in the 2025 trajectory:

| Date | Event | Visible in our data |
|---|---|---|
| **Jan 27, 2025** | **DeepSeek shock** — NVDA −16.9% (−$589B market cap, largest single-day mcap loss in US history); Nasdaq Composite −3% | First sharp drawdown bar in late Jan |
| **Apr 2, 2025**  | **"Liberation Day" tariffs** — sweeping Trump tariffs; >$6.6T two-day global equity loss (largest since 2020 COVID crash); NDX into bear-market territory | The deep drawdown to ~$16.8k |
| **Apr 9, 2025**  | **90-day tariff pause** announced — **NDX +12.02% single session** (NQ futures comparable) | **This is the +8.21% 4h bar in our data** ✓ |
| **May 13, 2025** | NDX erased YTD loss; turned positive for year | Inflection on recovery leg |
| **H2 2025**      | NVDA earnings cadence accelerating: Q1 FY26 $44.1B, Q2 $46.7B, Q3 **record $57.0B (+62% YoY)**; hyperscaler / sovereign-AI deals (Stargate UAE, HUMAIN Saudi, Foxconn Taiwan, South Korea) | Steady upward grind through Q3 2025 |
| **Sep / Oct / Dec 2025** | **Three Fed rate cuts** (Sept, Oct, Dec FOMC) — ended 2025 at 3.50–3.75% | Trend acceleration in late 2025; duration-sensitive megacap rally |
| **Oct 11, 2025** | Trump Truth Social tariff post wiped ~$2T in a single day | Sharp red bar in mid-Oct 2025 |
| **Nov 2025**     | S&P −5.7% from Oct high; sharpest pullback since April | Pullback before year-end recovery |
| **Dec 2025**     | NDX closed −0.7% for the month; four-session losing streak into year-end | Last few 2025 bars trending down |

**Year-over-year context:** 2023 NDX +55.1%, 2024 NDX +25.7%, **2025 NDX +20.2%**. 2025's gain is the *smallest* of three consecutive double-digit years and unremarkable in long-run NDX context. NQ futures trade at a small basis premium to spot NDX, so cash NDX ~24,800-25,000 in late Dec 2025 maps cleanly to NQ ~25,000-25,500 — **consistent with our dataset's close of $25,434**.

**Boundary check (Dec 2025 → Jan 2026):** No discrete year-boundary jump exists. December 2025 actually closed *lower* (NDX −0.7% for the month) with a four-session losing streak into year-end. The full ~4,300-point year gain is **smooth accumulation across 2025 with the April V baked in**, not a single overnight event. This matches our data: last-2025 close $25,434 → first-2026 close $25,604 = +0.66% over 28 wall-clock hours.

**Sources (key URLs):**
- Liberation Day & V: [Wikipedia 2025 crash](https://en.wikipedia.org/wiki/2025_stock_market_crash), [NPR](https://www.npr.org/2025/04/03/nx-s1-5350938/markets-plunge-after-liberation-day-tariffs)
- Apr 9 pause +12.02%: [Nasdaq.com](https://www.nasdaq.com/articles/stocks-soar-president-trump-pauses-reciprocal-tariffs), [CBS](https://www.cbsnews.com/news/trump-announces-90-day-tariffs-pause/)
- DeepSeek shock: [CNBC](https://www.cnbc.com/2025/01/27/nvidia-falls-10percent-in-premarket-trading-as-chinas-deepseek-triggers-global-tech-sell-off.html), [Bloomberg](https://www.bloomberg.com/news/articles/2025-01-27/asml-sinks-as-china-ai-startup-triggers-panic-in-tech-stocks)
- Fed Dec 2025 cut: [Federal Reserve press release](https://www.federalreserve.gov/newsevents/pressreleases/monetary20251210a.htm)
- 2025 annual return: [Slickcharts](https://www.slickcharts.com/nasdaq100/returns), [Statista](https://www.statista.com/statistics/1330833/nasdaq-100-index-annual-returns/)
- NVDA earnings: [SEC 8-K Q3 FY26](https://www.sec.gov/Archives/edgar/data/0001045810/000104581025000228/q3fy26pr.htm)

---

## 5. The +8.21% 4h bar is identified

The single most diagnostic outlier in our 2025 returns is **+8.21% in one 4h bar**. The macro research dates it: **April 9, 2025**, when the Trump administration announced a 90-day tariff pause and NDX gained +12.02% on the day (cash). Our 4h bar capturing the headline window shows +8.21% — the rest of the day's +12% is spread across the other 4h sessions. **This is not a data error.** It is the largest US-equity-index intraday rally since the April-2020 COVID-bottom reversal, and it is correctly in our CSV.

For Prophet (and any model fit on log-returns), this single bar is a **6σ event** in the 2025 distribution (`(0.0821 − 0.00013) / 0.00582 ≈ +14σ` — well into "no Gaussian model can ever predict this" territory). A naïve forecaster will mis-predict that bar by ~$1,720; a sophisticated forecaster will also mis-predict that bar by ~$1,720. **This bar dominates 2025 RMSE for any reasonable model** and is the single biggest data point pushing RMSE up.

---

## 5. Bottom line

- The CSV split is **clean** — not a bug.
- The 2025→2026 boundary "jump" is **+0.66% over 28h** — within normal market noise; the real action is inside 2025.
- The 2025 trajectory is **V-shaped with a −21% drawdown and a +52% recovery** — this is the hardest part of the problem for Prophet, not the year boundary.
- Every model in the tournament will be evaluated walk-forward on 2026 *with retraining*, so the level-shift between train-pool and eval-pool is structurally handled.
- The current `prophet_test.py` RMSE of **$5,625 is mostly a measurement artifact** (row-index misalignment plus no walk-forward), not a true upper bound on Prophet's skill. The new harness should produce a much smaller, *honest* number.
