# Complete Experiment Log — Every Trial, Every Number, Every Verdict

**A total record of the 2026-07-11 → 07-13 session. Sixty-five experiments across two workstreams.
Nothing omitted, including the failures, the retractions, and the self-inflicted wounds.**

Branch `fundamental-analysis` · Reports in `docs/superpowers/`

> 🇸🇦 النسخة العربية: [`REPORT_complete_experiment_log_AR.md`](REPORT_complete_experiment_log_AR.md)

---

## HOW TO READ THIS

Every experiment gets: **what we asked · how we tested it · the exact numbers · the verdict · what it
changed.** Verdicts use a fixed vocabulary:

| Symbol | Meaning |
|---|---|
| ✅ **CONFIRMED** | Measured directly. Not an inference. Stands regardless of sample size. |
| ❌ **DEAD** | Tested and failed on evidence that is adequate for the claim. |
| ⚠️ **RETRACTED** | I claimed this and was wrong. Withdrawn. |
| 🔬 **INCONCLUSIVE** | Tested, but the sample was too small to decide. **Not** a negative result. |
| ⭐ **PROMISING** | Positive signal, not yet proven. |
| 🔴 **SELF-INFLICTED** | My own error, documented so it isn't repeated. |

---

# PART 0 — THE MASTER TABLE (all 65 experiments)

| # | Experiment | Result | Verdict |
|---|---|---|---|
| **DATA ACQUISITION** | | | |
| 1 | Scrape BLS release schedule | **403 Forbidden** on all 5 endpoints | ❌ Blocked |
| 2 | Probe BEA / Fed / FRED endpoints | BEA 200 · Fed 200 · FRED 200 · BLS 403 | ✅ Route found |
| 3 | FRED `release_id=8` (retail sales) | **0 dates** — guard refused to write | 🔴 Wrong ID |
| 4 | FRED `release_id=9` (retail sales) | **19 dates** | ✅ Correct |
| 5 | Fed `calendar.json` structure | `events` (2,577), not `mc`. **3 different "FOMC" types** | ✅ Trap avoided |
| 6 | Search FRED for ISM | **Not carried** (proprietary) | ❌ Known gap |
| 7 | Build calendar (2025–26) | **103 events** | ✅ Built |
| 8 | Build calendar (2024–26) | **177 events** | ✅ Extended |
| **VERIFICATION** | | | |
| 9 | Timezone (volume-peak method) | Peaks at **09:30 / 15:59** ⇒ **US Eastern** | ✅ CONFIRMED |
| 10 | Volatility envelope (−60…+60) | **8.32× at offset 0**, exactly on the print | ✅ CONFIRMED |
| 11 | Pre-release ramp? | **0.78× at −2 min — the market goes QUIET** | ✅ CONFIRMED (kills a planned head) |
| 12 | Derive window bounds | **pre=0, post=12** (threshold 1.5×) | ✅ Measured |
| 13 | The "+60 min echo" | **4.91×** — but it's the **09:30 cash open** | 🔴 Trap caught |
| 14 | ISM gap cost | **10:00 = 3.61×** baseline (vs 2.12× at 11:00) | ✅ Quantified |
| 15 | **Lockup leak test** | 07:45–08:28 = **0.81–0.89×** vs control. **NO LEAK** | ✅ CONFIRMED |
| **ENGINE** | | | |
| 16 | Golden baseline (before changes) | **6/6 MATCH** | ✅ |
| 17 | Golden after `news_veto` | **6/6 byte-identical** | ✅ |
| 18 | Golden after excursion tracker | **6/6 byte-identical** | ✅ |
| 19 | Engine ↔ fast-engine parity | **11/11, zero mismatches** | ✅ |
| 20 | News-veto unit tests | **7/7** | ✅ |
| 21 | Excursion unit tests | **9/9** | ✅ |
| **HEAD 1 — THE VETO** | | | |
| 22 | Null test, 4h | real **+$30** · fakes **+$573** · **p=0.548** | ❌ DEAD |
| 23 | Null test, 15m | real **+$1,665** · fakes **+$998** · **p=0.290** | ❌ DEAD |
| 24 | Null test, 5m | real **+$552** · fakes **+$614** · **p=0.290** | ❌ DEAD |
| 25 | How often does the veto fire? | **3–4% of trades** (7/265 · 19/488 · 21/600) | ✅ CONFIRMED |
| 26 | Are we even holding at releases? | **Flat for 77%.** Median hold **1.4 h** | ✅ CONFIRMED |
| 27 | Can 4h bars see 08:30? | **NO.** 4h bars: 02/06/10/14/18/22. **88% of events invisible** | 🔴 Wrong test bed |
| **HEAD 2 — TRADE THE REACTION** | | | |
| 28 | 30-cell (k × h) sweep, 50 fakes | **0 of 30 significant** (1.5 expected by luck) | ❌ DEAD |
| 29 | The "$72,170 fade edge" | **Fakes reproduce it** ⇒ ordinary NQ mean-reversion | 🔴 Mirage caught |
| **HEAD 3 — TRADE THE CONTENT** | | | |
| 30 | ALFRED first-print vs revised | Payrolls revised by **−801k to −1,032k jobs** | ✅ CONFIRMED |
| 31 | Surprise → direction (in-sample) | **corr −0.322, p=0.021** at h=5 | ⚠️ RETRACTED |
| 32 | Surprise → direction (out-of-sample) | 2025 **−0.432** → 2026 **−0.011**. **SIGN FLIPPED** 2/4 | ❌ DEAD (regime) |
| **ROBUSTNESS (9 MARKETS)** | | | |
| 33 | Bootstrap, 9 markets, 400 draws | **All 9 negative.** 5/9 CI excludes zero | ⚠️ Forced a correction |
| 34 | Cross-market correlation | Equity bloc **0.95**. **Effective markets = 3.2, not 9** | ✅ CONFIRMED |
| 35 | First principal component | **47.5%** of variance | ✅ |
| 36 | Shuffled null, 36 cells | **7 significant** vs 1.8 expected | 🔬 |
| 37 | Bonferroni (p<0.0014) | **0 of 36 survive** | ⚠️ RETRACTED (see #45) |
| 38 | **Silver** | **p=0.007**, and **STRENGTHENED OOS** (−0.140 → −0.500) | ⭐ OPEN |
| **THE PATTERN (n=52)** | | | |
| 39 | Magnitude — 4 measures | **+0.105 to +0.121**, all p > 0.38 | 🔬 (see #46) |
| 40 | Persistence | **46.2%** — a coin flip | 🔬 |
| 41 | Shape (4 clusters) | **p = 0.107** | 🔬 |
| **🚨 THE POWER ANALYSIS** | | | |
| 42 | Power at r=0.11, n=52 | **12%.** Need **647** events. Had **8%** | 🔴 **THE FINDING** |
| 43 | Power to clear Bonferroni | **≈ 0%** for any realistic effect | 🔴 |
| 44 | **RETRACTION** | "Scheduled macro is priced in" | ⚠️ **WITHDRAWN** |
| 45 | Corrected 4 artifacts + memory | Spec · Seminar EN · Seminar AR · Robustness report | ✅ Done |
| **EXTENDED (2024 FOLDED IN, n=117)** | | | |
| 46 | **Magnitude, re-run** | **+0.187 (p=0.044)** · **+0.206 (p=0.027)** | ⭐ **SIGNIFICANT** |
| 47 | Persistence, re-run | **49.6%** — still a coin flip | ❌ DEAD |
| 48 | Shape, re-run | **p = 0.131** | ❌ DEAD |
| 49 | Magnitude out-of-sample | IS **+0.21–0.23** · OOS **+0.12/+0.11/~0** · **power 3–8%** | 🔬 INCONCLUSIVE |
| 50 | Magnitude year-by-year | **+0.29 / +0.22 / +0.12** — **positive every year, NO flip** | ⭐ PROMISING |
| **STOP-LOSS: THE TRACKER** | | | |
| 51 | Speed baseline | 4h **32.8 ms** · 15m 107.2 · 5m 134.9 | ✅ |
| 52 | Naive excursion impl | **+19.8% CPU** | ❌ Too slow |
| 53 | Profile the cost | Arithmetic = **0.8 ms**. Rest = **numpy dispatch** | 🔴 Insight |
| 54 | `reduceat` batch impl | **+14.6% CPU** (0% when off) | ✅ Fixed |
| 55 | **The 74% phantom benchmark** | Load avg **49–53**; one python at **1602% CPU** | 🔴 SELF-INFLICTED |
| **STOP-LOSS: WHAT IT REVEALED** | | | |
| 56 | Giveback | **158/373 losers (42%) were once +20 up.** **$145,640** given back | ✅ CONFIRMED |
| 57 | Winner heat | median **11.2**, 99th pct **37.9** (stop at **40**) | ✅ CONFIRMED |
| 58 | Loser heat | median **41.5** | ✅ |
| 59 | Separability | **P(winner heat > loser heat) = 0.014** | ✅ (but I over-read it) |
| **STOP-LOSS: THE COUNTERFACTUAL** | | | |
| 60 | Ignore the stop (3× floor) | **46.8% recovered to TP.** **+$20,000** | ⭐ Looked real |
| 61 | **Sweep the disaster floor** | Recovery = **gambler's ruin at EVERY floor.** Dev **+0.34 pp** | ❌ **DEAD** |
| 62 | Post-stop drift, 7 horizons | **ALL NEGATIVE** (−0.02 to −5.31 pts) | ❌ Continuation |
| 63 | The skew | **Median POSITIVE, mean NEGATIVE** | 🔴 **The trap** |
| 64 | MFE as a predictor | 43.9% / 44.2% / 55.8% / 46.3% — no monotone | ❌ Not predictive |
| 65 | Prior-art research | Osler · Kaminski-Lo · Liaudinskas · Doob | ❌ All point the same way |

---

# PART 1 — DATA ACQUISITION (Experiments 1–8)

## Exp 1–2: Can we get the release schedule?

**Method:** HTTP-probe every plausible source with a browser User-Agent.

| Endpoint | Result |
|---|---|
| `www.bls.gov/schedule/news_release/empsit.htm` | **403** |
| `www.bls.gov/schedule/schedule.ics` | **403** |
| `www.bls.gov/feed/bls_latest.rss` | **403** |
| `download.bls.gov/pub/time.series/` | **403** |
| `api.bls.gov/publicAPI/v2/...` | **200** |
| `www.bea.gov/news/schedule` | **200** |
| `www.federalreserve.gov/json/calendar.json` | **200** |
| `api.stlouisfed.org/fred/release/dates` | **200** (needs free key) |

**Verdict:** ❌ BLS blocks all scraping. ✅ **FRED is the route in.**

**Why it mattered more than expected:** the 2025 and 2026 **government shutdowns rescheduled releases**.
BLS publishes *"Revised news release dates following the 2025 and 2026 lapses in appropriations."*
**The one dataset I had called "un-revisable" had been revised.** FRED's `release/dates` records when a
statistic **actually came out**, so reschedules are captured for free.

## Exp 3–4: The guessed ID that a guard caught

```
  nonfarm_payrolls   release_id=50   ->  17 dates
  cpi                release_id=10   ->  17 dates
  ppi                release_id=46   ->  17 dates
  gdp                release_id=53   ->  17 dates
  pce                release_id=54   ->  18 dates
  retail_sales       release_id=8    ->   0 dates      ← !!
RuntimeError: refusing to write a partial calendar.
```

**Correct ID: 9** ("Advance Monthly Sales for Retail and Food Services") → **19 dates.**

**Verdict:** 🔴 My error. ✅ Caught by a **three-line refuse-on-empty guard.** Without it we'd have
silently shipped a calendar missing 16 events.

## Exp 5: Three different "FOMC" events

The Fed's JSON has **135 entries** of `type: FOMC`. They are **not the same thing**:

| Entry | Time | What | Kept? |
|---|---|---|---|
| **FOMC Meeting** | 2:00 pm | The **rate decision**. Enormous. | ✅ |
| FOMC Press Conference | 2:30 pm | Big — **but only listed from Sept 2025** ⇒ partial coverage | ❌ |
| FOMC Minutes | 2:00 pm | Notes, 3 weeks later. Far smaller impact. | ❌ |

Also: the file is served with a **UTF-8 byte-order mark** (needs `utf-8-sig`), and its structure is an
`events` array — **not** the `mc` shape I had assumed.

## Exp 6: ISM — the gap we refused to paper over

**FRED does not carry ISM.** It is a private company; its PMI data is proprietary. I *could* have
rule-derived the dates (1st/3rd business day). **I chose not to** — guessed dates are exactly the class
of unverified data this design exists to avoid, and we had *just* learned that even official schedules
lie. **Documented as a known gap and its cost measured (Exp 14).**

## Exp 7–8: The calendars

| Build | Window | Events |
|---|---|---|
| Original | 2025-01-01 → 2026-06-30 | **103** |
| **Extended** | **2024-01-01 → 2026-06-30** | **177** |

Composition (extended): CPI 29 · Payrolls 29 · Retail 29 · PPI 28 · PCE 27 · GDP 23 · FOMC 12.

---

# PART 2 — VERIFICATION (Experiments 9–15)

## Exp 9: Timezone — proved, not assumed

**Method:** find the highest-average-volume minutes of the day.

| Minute | Mean volume |
|---|---|
| **15:59** | **8,453** |
| **09:30** | **4,972** |
| 09:31 | 3,455 |
| 16:00 | 3,433 |
| **10:00** | **2,685** |

09:30 and 15:59–16:00 are the **US cash equity open and close**. Session starts 18:00 = the **CME Globex
reopen**. ⇒ **The `datetime` column is US Eastern wall-clock.** Releases are announced in Eastern time,
so **no timezone conversion, and daylight saving handles itself.**

**Verdict:** ✅ **CONFIRMED.** An entire class of silent bug eliminated.

## Exp 10–11: The envelope — and the finding that killed a planned feature

| Minutes from release | −6 | −5 | −4 | −3 | **−2** | −1 | **0** | +1 | +6 | +12 | +25 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **Volatility vs normal** | 1.01× | 1.06× | 1.16× | 0.86× | **0.78×** | 1.34× | **8.32×** | 3.03× | 2.43× | 1.62× | 1.13× |

**Two findings:**

1. **8.32× at offset 0, landing exactly on the predicted minute.** No wrong ID or timezone bug could
   produce that. **The calendar validated itself.**
2. **The market goes QUIET before a release** — 0.78× at two minutes out, *below* an ordinary minute.
   **There is no pre-release volatility ramp.** The planned "widen the stop to survive the run-up" head
   was built to solve **a problem that does not exist.**

## Exp 12: The window, measured not chosen

`derive_bounds(threshold=1.5)` → **pre = 0, post = 12 minutes.**
(At threshold 1.3: pre=1, post=21.)

## Exp 13: 🔴 The "+60 minute echo" that wasn't

At +60 min, volatility jumps back to **4.91×**. My instinct: *"the release is still echoing!"*

**It isn't.** Most releases are 08:30. Sixty minutes later is **09:30 — the cash open.** A completely
different event. A calm gap at +22…+27 (1.13×–1.35×) separates them cleanly, so `derive_bounds` stops at
+13 and cannot swallow the morning. **Pinned in a test** so nobody "fixes" it.

## Exp 14: The ISM gap, priced

| Clock | Volatility vs baseline |
|---|---|
| 08:30 (our releases) | 3.13× |
| **09:30 (cash open)** | **4.58×** |
| **10:00 (ISM — WE HAVE NO DATA)** | **3.61×** |
| 11:00 (nothing) | 2.12× |
| 14:00 (FOMC) | 1.73× |

**Verdict:** the gap is **real and it costs us**. Measured, not hand-waved.

## Exp 15: ✅ THE LOCKUP TEST — does the news leak?

US macro data sits with journalists in a **sealed lockup room for ~30 minutes** before publication.
**If it leaked, we would see it.**

| Clock | **Release days** | Control days | **Ratio** | |
|---|---|---|---|---|
| 07:45 | 0.78× | 0.92× | **0.85×** | normal |
| **08:00** | 0.96× | 1.19× | **0.81×** | **nothing** |
| 08:05 | 0.91× | 1.04× | 0.88× | normal |
| 08:15 | 0.89× | 0.99× | 0.89× | normal |
| 08:20 | 1.10× | 1.07× | 1.03× | normal |
| 08:25 | 1.07× | 0.85× | 1.26× | mild |
| **08:28** | 0.75× | 0.92× | **0.82×** | **normal** |
| 08:29 | 1.35× | 0.82× | 1.65× | last-minute |
| **08:30** ⚡ | **8.53×** | 1.44× | **5.94×** | **THE PRINT** |
| 08:31 | 2.93× | 1.37× | 2.14× | |
| 08:35 | 1.91× | 1.05× | 1.82× | |

**Verdict:** ✅ **NO LEAK.** From 07:45 to 08:28 release days are **indistinguishable from — in fact
QUIETER than — ordinary weekdays.** The 08:29 uptick is **market-makers pulling quotes** (08:28 is quiet
at 0.82×), not information.

**The publication instant is the only one that matters. Our calendar is correct. And the US statistical
lockup system demonstrably works.**

---

# PART 3 — ENGINE INTEGRATION (Experiments 16–21)

| Gate | What it proves | Result |
|---|---|---|
| **Golden 6/6** (baseline) | The server reproduces our champions | ✅ 4h $148,670 · 2h $105,462 · 1h $80,339 · 15m $77,098 · 5m $23,926 · 2m $29,777 |
| **Golden 6/6** (after `news_veto`) | Feature OFF ⇒ **byte-identical** | ✅ ALL MATCH |
| **Golden 6/6** (after excursions) | Feature OFF ⇒ **byte-identical** | ✅ ALL MATCH |
| **Engine ↔ fast-engine parity** | Both engines agree trade-for-trade | ✅ **11/11, zero mismatches** |
| News-veto tests | Entry-block, force-exit, profit exemption | ✅ **7/7** |
| Excursion tests | Sign invariants, bracketing, speed | ✅ **9/9** |

**Two discoveries in our own code:**

1. 🔴 **The parameter named `veto_mask` does not veto.** It only drives flip / carry-abort / rescue. The
   real blocker is the composite `entry_gate` (`engine.py:520`, `fast_engine.py:97`). **If I'd trusted
   the name, the feature would have silently done nothing.**
2. 🔴 **There is no unrealized-P/L anywhere.** Trades carry only static price lines. Profit exists only
   at exit. This made "was this stop-out a giveback?" **literally unanswerable** — and forced Task #2.

---

# PART 4 — HEAD 1: THE VETO (Experiments 22–27)

## Exp 22–24: The null tests

| Timeframe | **Baseline** | **With veto** | Change | **FAKE calendars** | p |
|---|---|---|---|---|---|
| 4h | $42,187 · 209 trades | $42,217 · 208 | **+$30** | +$573 ± $4,568 | **0.548** |
| 15m | $4,239 · 323 | $5,904 · 321 | **+$1,665** | **+$998 ± $1,075** | **0.290** |
| 5m | $693 · 132 | $1,245 · 132 | **+$552** | +$614 ± $3,055 | **0.290** |

**The damning column is the fakes.** On 15m, a calendar of **completely invented dates** earned **+$998**
against the real one's +$1,665. **Randomly cutting trades makes this strategy money.** That's a fact about
our stop placement, not about news.

## Exp 25–26: Why it failed — the structural reason

| | |
|---|---|
| Median hold time | **1.4 hours** |
| Releases with a position open | **24 of 103 (23%)** |
| **Releases we're ALREADY FLAT for** | **77%** |
| Trades the veto touches | **3–4%** (7/265 · 19/488 · 21/600) |

**The premise — "don't hold naked through a release" — assumed we often hold through releases. We don't.
There was almost nothing to protect. We built an umbrella for a man already indoors.**

## Exp 27: 🔴 THE WRONG TEST BED

| 4h decision bars land at | 02:00 · 06:00 · 10:00 · 14:00 · 18:00 · 22:00 |
|---|---|
| **Releases land at** | **08:30** and 14:00 |

**08:30 — which is 88% of all our events — can NEVER coincide with a 4-hour bar.** Only the twelve
FOMC statements can. The 4h veto touched **11 bars out of 2,119** and removed **one trade out of 209.**

**I was measuring whether a feature worked while it was effectively switched off.** One line
(`mask.sum()`) would have caught it.

---

# PART 5 — HEAD 2: TRADE THE REACTION (Experiments 28–29)

**Method:** does the move in the first *k* minutes predict the move over the next *h*? Swept
k ∈ {1,2,3,5,10,15} × h ∈ {15,30,60,120,240} = **30 cells**, scored against **50 fake calendars**.

**Result: 0 of 30 significant.** (Chance alone predicts ~1.5.) Hit rates **42–57%** — coin flips.

## Exp 29: 💰 THE $72,170 MIRAGE

There *was* a pattern. At long horizons momentum **lost money consistently** — negative correlation at
**every** k (−0.14 to −0.23 at h=240). Losing reliably means **doing the opposite wins**:

**+$760/trade × 95 releases = +$72,170.**

**Then the fake calendars showed the same thing.** Fading a 4-hour move makes money on **random days with
no news at all.** It's ordinary Nasdaq mean-reversion wearing a news costume.

**Verdict:** 🔴 **A $72,000 "edge" that was just a property of the index. The null test caught it.**

---

# PART 6 — HEAD 3: TRADE THE CONTENT (Experiments 30–32)

## Exp 30: Why point-in-time data matters — ALFRED

| Payrolls, reference month | **Printed that morning** | **In the database today** | **Revised away** |
|---|---|---|---|
| Jan 2025 | 159,069,000 | 158,268,000 | **−801,000** |
| Feb 2025 | 159,218,000 | 158,310,000 | **−908,000** |
| Mar 2025 | 159,398,000 | 158,377,000 | **−1,021,000** |
| Apr 2025 | 159,517,000 | 158,485,000 | **−1,032,000** |

**About a million jobs of hindsight per event.** Backtesting on today's values would trade on numbers
**nobody had that morning.**

## Exp 31: The signal that nearly fooled us

| Hold | Correlation | p |
|---|---|---|
| **5 min** | **−0.322** | **0.021** ✅ |
| 15 min | −0.225 | 0.105 |
| 30 min | −0.204 | 0.142 |
| 60 min | −0.236 | 0.084 |

**2025 alone: −0.432.**

Significant. **And the sign made perfect economic sense** — negative means a *better*-than-expected
number makes the Nasdaq *fall*, the classic **"good news is bad news"** hawkish-Fed effect.

**Significant number + coherent economic story. This is exactly what people ship.**

## Exp 32: ⚰️ Out-of-sample — it evaporated

| Hold | **2025** | **2026** | Sign held? | 2026 P/L |
|---|---|---|---|---|
| 5 min | **−0.432** | −0.011 | yes | −2.8 bp |
| 15 min | **−0.377** | **+0.159** | ❌ **FLIPPED** | −3.1 bp |
| 30 min | **−0.362** | **+0.125** | ❌ **FLIPPED** | −4.5 bp |
| 60 min | **−0.252** | −0.021 | yes | −6.4 bp |

**It didn't weaken — it went to zero, and at two of four horizons it REVERSED.** Applying the 2025 rule
to 2026 **lost money at every horizon**, hit rate 32–41% — worse than a coin flip.

**"Good news is bad news" was a property of the 2025 Fed regime, not a law of markets.**

**Only the pre-declared kill criterion stopped this shipping.**

---

# PART 7 — ROBUSTNESS: 9 MARKETS (Experiments 33–38)

*(Prompted by the user: "you proved a single scenario of failure. take 20 samples and redo it.")*

## Exp 33: The result that forced a correction

| Market | Full-sample corr | 95% CI | Real? | 2025 | 2026 |
|---|---|---|---|---|---|
| **NQ** | −0.322 | [−0.538, −0.068] | **YES** | −0.432 | −0.011 |
| **ES** | −0.313 | [−0.541, −0.055] | **YES** | −0.415 | +0.037 |
| **SI (silver)** | **−0.360** | **[−0.584, −0.143]** | **YES** | −0.140 | **−0.500** |
| **RTY** | −0.304 | [−0.525, −0.047] | **YES** | −0.341 | −0.095 |
| **YM** | −0.275 | [−0.524, −0.007] | **YES** | −0.351 | −0.004 |
| GC | −0.232 | [−0.517, +0.060] | no | −0.113 | −0.366 |
| CL | −0.213 | [−0.428, +0.023] | no | −0.256 | −0.087 |
| HG | −0.144 | [−0.424, +0.165] | no | −0.087 | −0.149 |
| NG | −0.133 | [−0.344, +0.083] | no | −0.293 | −0.058 |

**All nine negative. Five of nine exclude zero. Silver STRENGTHENED out-of-sample.**
**"Dead" was too strong a word. The user was right to make me check.**

## Exp 34–35: But the nine markets are not nine tests

**Correlation of the 9 markets' release-window returns with each other:**

| | NQ | ES | GC | SI | HG | CL | NG | RTY | YM |
|---|---|---|---|---|---|---|---|---|---|
| **NQ** | 1.00 | **0.98** | 0.06 | 0.18 | 0.39 | 0.21 | 0.07 | **0.91** | **0.96** |
| **ES** | **0.98** | 1.00 | 0.08 | 0.19 | 0.42 | 0.23 | 0.05 | **0.93** | **0.98** |
| **GC** | 0.06 | 0.08 | 1.00 | **0.85** | 0.56 | −0.28 | 0.15 | 0.09 | 0.12 |
| **SI** | 0.18 | 0.19 | **0.85** | 1.00 | 0.63 | −0.09 | 0.18 | 0.18 | 0.22 |
| **HG** | 0.39 | 0.42 | 0.56 | 0.63 | 1.00 | 0.04 | 0.27 | 0.39 | 0.46 |
| **CL** | 0.21 | 0.23 | −0.28 | −0.09 | 0.04 | 1.00 | 0.22 | 0.17 | 0.17 |
| **NG** | 0.07 | 0.05 | 0.15 | 0.18 | 0.27 | 0.22 | 1.00 | −0.09 | 0.02 |
| **RTY** | **0.91** | **0.93** | 0.09 | 0.18 | 0.39 | 0.17 | −0.09 | 1.00 | **0.93** |
| **YM** | **0.96** | **0.98** | 0.12 | 0.22 | 0.46 | 0.17 | 0.02 | **0.93** | 1.00 |

| Measure | Value |
|---|---|
| Mean correlation **within** the equity bloc (NQ/ES/RTY/YM) | **0.95** |
| Mean correlation **equities vs everything else** | **0.18** |
| Gold ↔ Silver | **0.85** |
| First principal component | **47.5%** |
| **EFFECTIVE INDEPENDENT MARKETS** | **≈ 3.2 — not 9** |

**"5 of 9 significant" is really ONE equity bet counted four times, plus silver.**

## Exp 36–37: The proper null, and the Bonferroni trap

**36 tests (9 markets × 4 horizons), 3,000 shuffles each:**

| Market | h=5 | h=15 | h=30 | h=60 |
|---|---|---|---|---|
| **NQ** | −0.322 · **p=0.020** ✱ | −0.225 · 0.110 | −0.204 · 0.137 | −0.236 · 0.092 |
| **ES** | −0.313 · **p=0.024** ✱ | −0.229 · 0.096 | −0.200 · 0.149 | −0.255 · 0.068 |
| **GC** | −0.232 · 0.085 | −0.145 · 0.295 | −0.132 · 0.327 | −0.162 · 0.222 |
| **SI** | −0.360 · **p=0.007** ✱ | −0.282 · **p=0.032** ✱ | −0.203 · 0.124 | −0.167 · 0.212 |
| **HG** | −0.144 · 0.296 | −0.026 · 0.850 | −0.010 · 0.948 | −0.083 · 0.543 |
| **CL** | −0.213 · 0.124 | −0.021 · 0.874 | +0.020 · 0.871 | +0.079 · 0.545 |
| **NG** | −0.133 · 0.317 | +0.050 · 0.712 | +0.127 · 0.334 | −0.076 · 0.591 |
| **RTY** | −0.304 · **p=0.025** ✱ | −0.248 · 0.062 | −0.203 · 0.129 | −0.263 · **p=0.044** ✱ |
| **YM** | −0.275 · **p=0.039** ✱ | −0.223 · 0.091 | −0.158 · 0.226 | −0.237 · 0.069 |

**7 significant vs 1.8 expected by luck.** Bonferroni (p < 0.0014): **0 of 36 survive.**

⚠️ **THIS CONCLUSION WAS LATER RETRACTED.** See Exp 43.

## Exp 38: ⭐ SILVER — the one loose end

| | |
|---|---|
| Full-sample correlation | **−0.360** |
| p-value | **0.007** — the strongest of all 36 cells |
| 2025 (in-sample) | −0.140 (weak) |
| **2026 (out-of-sample)** | **−0.500 (STRONG)** |
| Also significant at h=15 | p = 0.032 |

**Silver is the ONLY thing that behaved unlike everything else.** Every other signal *decayed* out of
sample. Silver's **grew.**

**Logged as a pre-registered open question. Deliberately NOT chased** — being the best of 36 cells is
exactly what luck produces, because something has to come first.

---

# PART 8 — 🚨 THE POWER ANALYSIS (Experiments 42–45)

**THIS IS THE MOST IMPORTANT EXPERIMENT IN THE ENTIRE SESSION.**

## Exp 42: We had 12% power

| If the true effect is… | **Power we had (n=52)** | Events needed for 80% | We had |
|---|---|---|---|
| r = 0.05 | **5%** | 3,138 | 2% |
| r = 0.10 | **10%** | 783 | 7% |
| **r = 0.11 — what we MEASURED** | **12%** | **647** | **8%** |
| r = 0.15 | 18% | 347 | 15% |
| r = 0.20 | 29% | 194 | 27% |
| r = 0.30 | 58% | 85 | 61% |
| r = 0.40 | 84% | 47 | 111% |

> **Even if the effect is entirely real at r = 0.11, we would have MISSED IT 88 TIMES OUT OF 100.**

## Exp 43: 🔴 The Bonferroni correction made it WORSE

| Threshold | Power to clear it (n=52, r=0.11) |
|---|---|
| p < 0.05 (uncorrected) | **12%** |
| **p < 0.0014 (Bonferroni over 36)** | **≈ 0%** |

**"Zero of 36 survive Bonferroni" was guaranteed by the sample size before a single test ran.** It was
**not a finding about the market — it was arithmetic about my sample.** I dressed a foregone conclusion
up as rigour, and it was the most confident-sounding sentence in the report.

## Exp 44–45: The retraction

**RETRACTED:**
- ❌ "The surprise signal is dead" (28 out-of-sample events)
- ❌ **"Scheduled US macro is priced in"** — the headline conclusion
- ❌ "Do not buy vendor consensus data" (suspended)
- ❌ "Nothing survives Bonferroni"

**STILL STANDS** (these are **measurements**, not inferences): calendar validated (8.32×) · market calm
before (0.78×) · **lockup does not leak** · veto structurally useless (flat for 77%) · 4h bars can't see
08:30 · the $72k fade edge is NQ mean-reversion (fakes reproduce it) · equity bloc is 0.95 correlated.

**Corrections applied to:** the spec close-out, both seminar editions (EN + AR), the robustness report,
and memory.

---

# PART 9 — THE EXTENDED SAMPLE (Experiments 46–50)

**2024 was sitting unused on disk** — `data/2024_data/NQ_1m_2024.csv`, 355,014 bars, a complete year,
every release minute present.

| | Before | **With 2024** |
|---|---|---|
| Price frame | 486,969 bars | **841,983 bars** |
| Calendar | 103 events | **177 events** |
| **Usable surprises** | **52** | **117** |

⚠️ **Safety:** `extended_data.py` is a **STUDY-ONLY** loader. `optimize/data.py` is **untouched** — the
golden gate hashes the trade ledger from those exact paths, and silently lengthening the engine's history
would change every champion. **The engine is unchanged; golden 6/6 stay byte-identical.**

## Exp 46: ⭐ THE SIGNAL I DISMISSED COMES BACK

| Measure | **n=52 (before)** | **n=117 (with 2024)** | Power |
|---|---|---|---|
| \|move\| at +5 min | +0.105 · p=**0.455** | **+0.187 · p=0.044** ✅ | 52% |
| \|move\| at +30 min | +0.121 · p=**0.383** | **+0.206 · p=0.027** ✅ | 61% |
| Path range | +0.105 · p=**0.463** | +0.169 · p=0.070 | 44% |
| Path volatility | +0.107 · p=**0.435** | +0.180 · p=0.050 | 50% |

**It did not vanish when I added data. It GOT STRONGER and became significant.**

> **Noise shrinks toward zero as n grows. A real effect sharpens. This sharpened.**

## Exp 47–48: Persistence and shape — genuinely dead

| Question | Result | Verdict |
|---|---|---|
| Does the initial move persist to +30? | **49.6%** (58/117) · corr +0.050 | ❌ **Coin flip** |
| Does the surprise pick the SHAPE? | 4 clusters · **p = 0.131** | ❌ **No** |

## Exp 49: Out-of-sample — INCONCLUSIVE, and I will not spin it

| Measure | In-sample (n=94) | Out-of-sample (n=23) | **OOS power** |
|---|---|---|---|
| \|move\| +5m | **+0.222** (p=0.034) | +0.120 | **8%** |
| \|move\| +30m | **+0.230** (p=0.028) | +0.112 | **7%** |
| Path range | **+0.211** (p=0.040) | −0.001 | **3%** |
| Path volatility | **+0.229** (p=0.029) | +0.013 | **3%** |

**OOS power is 3–8%. With 23 events we could not detect this effect if it were certain.**
**That test proves nothing in either direction. 🔬 INCONCLUSIVE.**

**But the signs did NOT flip** — and a sign flip is exactly what killed the direction signal.

## Exp 50: ⭐ Is it a REGIME, like last time?

| Measure | **2024** | **2025** | **2026** | Verdict |
|---|---|---|---|---|
| **\|move\| +5m** | **+0.291** (n=41) | **+0.218** (n=52) | **+0.115** (n=23) | ✅ **positive EVERY year** |
| **\|move\| +30m** | **+0.278** | **+0.255** | **+0.100** | ✅ **positive EVERY year** |
| Path range | +0.147 | +0.294 | −0.014 | → collapses to ~0 |
| Path volatility | +0.132 | +0.318 | −0.001 | → collapses to ~0 |

**Compare with the DIRECTION signal that died:**
2025 = **−0.43** → 2026 = **−0.01 / +0.16 / +0.13** — it **FLIPPED SIGN at two of four horizons.**

**The magnitude signal never flips.** But it **declines** (0.29 → 0.22 → 0.12), and 2026 has 23 events at
**17% power** — so I **cannot distinguish real decay from noise.**

**Verdict: ⭐ PROMISING. NOT PROVEN. The first result today that survived contact with more data.**

## What it would mean if it holds

| Question | Answer |
|---|---|
| **Which way** will it move? | ❌ Cannot predict (direction dead, persistence a coin flip, shape null) |
| **How FAR** will it move? | ⭐ **Possibly yes** |

**A bigger surprise ⇒ a bigger move, in an unpredictable direction. That's a VOLATILITY signal, not a
directional one.**

**And efficient-market theory does not forbid it.** EMH says you cannot predict the **direction** of price
changes. It says **nothing** about the **variance** — volatility is famously forecastable. **The market
prices the expected value perfectly and still has no idea how big the shock will be.**

**Tradeable form:** *big surprise ⇒ expect a big move ⇒ widen stops/targets, or size differently.* That is
precisely the **policy head** the exogenous-signals workstream independently concluded was the right shape
for external data: **let it set RISK, not DIRECTION.** Two workstreams, same architecture.

---

# PART 10 — STOP-LOSS: THE TRACKER (Experiments 51–55)

## Exp 51–54: The speed engineering

| Stage | CPU cost | Note |
|---|---|---|
| Baseline (4h) | **32.8 ms/run** | 1,832 runs/min |
| Naive `hi[:ti+1].max()` per trade | **+19.8%** | Unacceptable |
| **Profile:** isolated max/min cost | **0.8 ms** | **The arithmetic was only 12% of the overhead** |
| **`np.maximum.reduceat` (batched)** | **+14.6%** | **0% when OFF** |

**The insight:** ~88% of the cost was **numpy dispatch overhead** — six tiny numpy calls × 265 trades ≈
1,600 calls. **We were paying the postage, not the parcel.** `reduceat` does every trade's excursions in
**one call**, using an interleave trick (`[start₀, end₀+1, start₁, end₁+1, …]`; the even results are the
trades, the odd ones are the gaps between them).

## Exp 55: 🔴 THE BENCHMARK THAT LIED BY 74%

**My first measurement reported +74% overhead. It was completely false.**

| Run | OFF (ms) | ON (ms) |
|---|---|---|
| 1 | 28.7 | 38.3 |
| 2 | 28.5 | 28.8 |
| 3 | **47.1** | 34.3 |
| 4 | **63.1** | 29.3 |

**The same code varied 2.2× (28.5 → 63.1 ms).** The cause:

```
load average: 49.11, 52.32, 53.00        (on a 32-thread box)
top CPU: 1602% python                     ← the other workstream's campaign
```

**A wall clock on a saturated machine measures how busy the machine is, not how fast your code is.**
Fix: `time.process_time()` — CPU time of *this* process only.

**I nearly rejected a perfectly good implementation because another program was busy.**

---

# PART 11 — STOP-LOSS: WHAT IT REVEALED (Experiments 56–59)

*Champion NQ 4h · 642 trades (269 winners, 373 losers)*

## Exp 56: The $145,640 giveback

| Losers that were EVER this far in profit | Count | % |
|---|---|---|
| ≥ +20 points | **158** | **42.4%** |
| ≥ +30 points | 97 | 26.0% |
| ≥ +40 points | 58 | 15.5% |
| ≥ +60 points | 0 | 0.0% |

- Median peak profit of a **losing** trade: **15.5 points ($310)**
- **Total profit reached and then handed back: $145,640**
- Hard-stopped trades that had **already been ≥ +30 up: 67 of 235 (28.5%)**

## Exp 57–59: Heat and separability

| | Heat taken (points against us) |
|---|---|
| **Winners** | median **11.2** · 90th 32.1 · 95th 34.8 · **99th 37.9** |
| **Losers** | median **41.5** · mean 47.0 |
| **The hard stop sits at** | **40.0** |

> **P(a random winner took more heat than a random loser) = 0.014**

**99% of winners reverse by 37.9 points. The stop is at 40.** It is **not** in the noise — it sits just
beyond where winners stop turning around.

⚠️ **MY ERROR:** I used this to argue the dynamic stop was pointless. **That conflated two claims:**
*"the fixed stop is well placed"* (TRUE) with *"no dynamic stop can beat it"* (**does not follow**).
**The user overruled me and was right.** Part 12 is the test I should have run first.

---

# PART 12 — STOP-LOSS: THE COUNTERFACTUAL (Experiments 60–65)

## Exp 60: It looked REAL

**Method:** for every hard-stopped trade, **replay it with the stop disabled** (take-profit kept,
disaster floor enforced, unresolved trades excluded).

| | |
|---|---|
| Hard-stopped trades | **235** |
| **RECOVERED all the way to take-profit** | **110 (46.8%)** |
| Fell through the disaster floor | 125 (53.2%) |
| Actual P/L (stop honoured) | **−$188,000** |
| Counterfactual (stop ignored) | **−$168,000** |
| **Difference** | **+$20,000** |

**Nearly HALF the stopped-out trades recovered to full take-profit. The user's intuition looked
vindicated.**

## Exp 61: ❌ THE SWEEP THAT DESTROYED IT

**The disaster floor was a number I invented. So I swept it.**

| Floor | Points | **Recovery %** | **Break-even %** | Margin | P/L |
|---|---|---|---|---|---|
| 1.5× | 60 | 15.7% | **16.7%** | **−1.0** | −$5,200 |
| 2.0× | 80 | 26.4% | **28.6%** | **−2.2** | −$14,400 |
| 2.5× | 100 | 35.3% | **37.5%** | **−2.2** | −$16,400 |
| **3.0×** | 120 | 46.8% | **44.4%** | **+2.4** | **+$20,000** |
| 3.5× | 140 | 51.9% | **50.0%** | **+1.9** | +$19,600 |
| 4.0× | 160 | 56.9% | **54.5%** | **+2.4** | +$26,400 |
| 5.0× | 200 | 62.6% | **61.5%** | **+1.1** | +$16,800 |
| | | | **MEAN DEVIATION** | **+0.34 pp** | |

**The recovery rate tracks the break-even rate at EVERY floor.**

**And the break-even formula `loss/(win+loss)` IS the gambler's-ruin probability** — the chance a
**driftless random walk** touches +a before −b.

> **From the moment the stop is hit, price is a FAIR COIN FLIP.**
>
> **The +$20,000 was never an edge. It was the ±2 pp of noise, and it was an artifact of the floor
> I happened to pick. At 2× it becomes −$14,400.**

**Doob's Optional Stopping Theorem:** under a martingale, `E[X_τ] = E[X₀]` for **any** stopping rule.
**No exit rule can change the expected value of a fair game.** Our data reproduces the theorem to within
0.34 percentage points.

## Exp 62: Post-stop drift — all seven horizons NEGATIVE

| Horizon | **Mean drift** | **Median drift** | t-stat |
|---|---|---|---|
| 5 min | **−2.11 pts** | +0.50 | −1.27 |
| 15 min | **−4.28** | −0.25 | −1.55 |
| 30 min | **−3.06** | +0.00 | −0.79 |
| 60 min | **−4.81** | −0.75 | −0.92 |
| 120 min | **−0.02** | **+2.75** | −0.00 |
| 240 min | **−0.95** | **+7.50** | −0.10 |
| 480 min | **−5.31** | −4.50 | −0.48 |

**All seven negative on the mean. The sign never flips. That is CONTINUATION, not reversion.**

## Exp 63: 🎯 THE TRAP — why the idea *feels* right

**Look at the two columns above. The MEDIAN is often POSITIVE while the MEAN is NEGATIVE.**

> **Most of the time, holding through the stop WORKS.** The median at 4 hours is **+7.50 points in your
> favour.**
>
> **But occasionally price collapses catastrophically, and those rare disasters swamp all the small wins.**
>
> **Win small, win often — lose huge, lose rarely.** That is the mathematical signature of **going broke.**
>
> **This is precisely why the intuition is so powerful. Every time you'd have held, you'd USUALLY have
> been proven right — and you'd remember those. The one time in ten it kept falling is the one nobody
> remembers, and it's the one that eats everything.**

## Exp 64: MFE as a predictor — no

| Peak profit before the stop | n | Recovered |
|---|---|---|
| 0–10 pts | 82 | 43.9% |
| 10–20 | 43 | 44.2% |
| 20–30 | 43 | 55.8% |
| 30+ | 67 | 46.3% |

**No monotone relationship. "Was it winning first?" does not predict recovery.**

## Exp 65: Prior art — every source points the same way

| Source | Finding |
|---|---|
| **Osler (2005)**, NY Fed / *JIMF* — 9,655 orders, $55bn, real FX order book | Once a stop cluster is **CROSSED**, price **CONTINUES** for 2+ hours. Reversal happens at *take-profit* clusters you were never stopped on. **The folklore is BACKWARDS.** |
| **Kaminski & Lo (2014)**, *J. Financial Markets* | Stops **ADD** value under momentum, **DESTROY** it under mean-reversion. **A veto is a bet on mean-reversion.** |
| **Liaudinskas (2019)**, millisecond data | The disposition effect (holding losers on a **belief in mean-reversion**) is **substantial in humans, ~zero in algorithms, and HARMS performance.** |
| **Odean (1998)**, *J. Finance* — 97,483 trades | Winners sold **outperformed** losers held by **3.4%/year**. Holding losers is *"on average, mistaken."* |
| **Locke & Mann (2005)**, *JFE* — ~300 **CME floor futures pros** | **The least profitable hold losers the longest.** |
| **Doob's theorem** | Under a martingale, **no** exit rule changes expected value. |
| Trailing/break-even stops | **Dai et al. (2021):** lower Sharpe. **Davey (567,000 backtests):** ranked poorly. **Mabe:** *"They ALL made the system perform worse."* |

**Five independent lines — two of our own measurements, our own skew finding, a theorem, and the two most
rigorous papers in the field — all converge. The stop veto is dead.**

---

# PART 13 — SELF-INFLICTED WOUNDS (the full list)

| # | What I did | Consequence | Lesson |
|---|---|---|---|
| 1 | **Skipped the power analysis entirely** | **Retracted an entire workstream conclusion** | **A null test says whether an effect you FOUND is real. POWER says whether you could have FOUND it. Both are mandatory.** |
| 2 | Applied Bonferroni to an underpowered study | Made a foregone conclusion **look like rigour** | Correcting for multiple comparisons on a blind study makes it **more confidently wrong** |
| 3 | Built the defensive head first | Wasted the first half of the FA workstream | **Build for the goal, not for safety** |
| 4 | Ran the veto test on 4h bars | 88% of releases **cannot coincide with a 4h bar** | **Verify the treatment applies to the test population.** `mask.sum()` = 11 of 2,119 |
| 5 | Trusted the name `veto_mask` | It **does not veto**. Feature would have silently done nothing | **Read the code, not the labels** |
| 6 | Assumed schedules can't be revised | **Government shutdowns rescheduled releases** | Prefer *"when it actually happened"* over *"when it was planned"* |
| 7 | Guessed a FRED release ID | Returned 0 dates | Look identifiers up; never guess |
| 8 | Assumed pre-release turbulence | **The market is QUIET (0.78×)** | Measure the premise before building on it |
| 9 | Invented the disaster floor silently | The first "+$20,000" was an artifact of my own choice | **Any number YOU invent must be swept** |
| 10 | Over-read the 1.4% heat overlap | Argued the idea was dead before testing it | *"X separates classes"* ≠ *"no better X exists"* |
| 11 | **Wall-clock benchmarked a saturated server** | Reported a **+74% regression that was fiction** | Use `time.process_time()` |
| 12 | First drift test used the wrong gate | Ran on **70 trades instead of 235** | **When the sample size looks wrong, STOP and find out why** |
| 13 | Over-aggressive `rsync` excludes | Broke the first golden run (`optimize/results/` holds the champions) | Know what your code reads at runtime |
| 14 | New SSH connection per command | **Tripped the server's `fail2ban`** | Multiplex |
| 15 | **Committed across an unnoticed branch switch** | Reports split across two branches — **looked deleted** | **Watch the branch** |

---

# PART 14 — WHAT ACTUALLY SURVIVED

## ✅ Confirmed measurements (unaffected by sample size)

| Finding | Value |
|---|---|
| The calendar validates itself | **8.32×** spike, **exactly** on the print |
| The market is CALM before a release | **0.78×** at −2 min |
| **The 08:30 lockup does NOT leak** | 07:45–08:28 = **0.81–0.89×** vs control |
| We're already flat for most releases | **77%.** Median hold **1.4 h** |
| 4h bars cannot see 08:30 | Bars at 02/06/10/14/18/22 |
| The "$72k fade edge" is NQ mean-reversion | **Fakes reproduce it** |
| Equity markets are one bet | NQ/ES/RTY/YM **0.95** correlated ⇒ **3.2 effective markets** |
| Payrolls get massively revised | **−801k to −1,032k jobs** |
| Post-stop price is a **martingale** | Recovery = gambler's ruin, dev **+0.34 pp** |
| Winners reverse before the stop | **99th pct heat = 37.9** (stop at 40) |
| We give back winners | **$145,640** |

## ⭐ The one promising signal

**MAGNITUDE:** bigger surprise ⇒ bigger move. **+0.187 (p=0.044)** and **+0.206 (p=0.027)** at n=117.
**Positive in all three years (+0.29 / +0.22 / +0.12). Never flips sign.** **Not proven** — needs ~650
events.

## ❌ Dead

The veto · trade-the-reaction · trade-the-direction · persistence · shape · the stop veto.

## ⚠️ Retracted

*"Scheduled US macro is priced in."* We **cannot tell** with 16 months of price data.

---

# PART 15 — THE SINGLE LESSON

> **I built an elaborate machine to stop myself claiming something that isn't there.**
>
> **It worked. It caught three real mirages.**
>
> **Not one part of it was designed to stop me MISSING something that is.**
>
> **And because it kept firing, it FELT like it was working. The more false positives it killed, the
> more confident I became in the false negatives it was producing.**

**A NULL TEST tells you whether an effect you FOUND is real.**
**A POWER ANALYSIS tells you whether you could have FOUND it at all.**
**Both are mandatory. Neither substitutes for the other.**

---

## Appendix — every script

| Script | What it runs |
|---|---|
| `fetch_calendar.py` | Build the calendar from FRED + the Fed |
| `release_calendar.py` | Load + validate (timezone guard) |
| `window.py` | Volatility envelope · masks · exit targets |
| `study_lockup.py` | **Exp 15** — does the news leak before 08:30? |
| `nulltest.py` · `run_nulltest.py` | **Exp 22–24** — the fake-calendar null test |
| `study_postrelease.py` | **Exp 28–29** — trade the reaction (the $72k mirage) |
| `alfred.py` | **Exp 30** — point-in-time first prints |
| `study_surprise.py` | **Exp 31–32** — trade the direction |
| `robustness.py` · `robustness2.py` | **Exp 33–38** — 9 markets |
| **`power_analysis.py`** | **Exp 42–43 — THE RETRACTION** |
| `extended_data.py` | **Exp 46** — fold in 2024 (study-only) |
| `study_pattern.py` | **Exp 39–41, 46–48** — magnitude · shape · persistence |
| `study_magnitude_oos.py` | **Exp 49** — the out-of-sample gate |
| `study_magnitude_regime.py` | **Exp 50** — is it a regime? |
| `study_excursions.py` | **Exp 56–59** — heat · giveback · separability |
| `study_stop_counterfactual.py` | **Exp 60–61** — the counterfactual + floor sweep |
| `test_excursions.py` | **Exp 51–55** — 9 tests incl. the CPU-time speed guard |
