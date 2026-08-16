# WS-NEWS3 M1 — the complete experiment log: every run, every gate, every number

**Date:** 2026-08-16 · **Issues:** #125 (closed), #124 (tracking) · **Companion:** the stage report
`WS-NEWS3-REPORT-P1-the-ride-and-the-premium.md` carries the verdicts; **this report carries the
full record** — designs, formulas, every verification round including the two failures, the
complete result tables, the distribution anatomy of the premium, and the exact claims that pin it.
**Everything here re-derives from committed files** (`p1_events_*.csv`, `p1_ride_*.csv`,
`p1_drift_*.csv`, `p1_result_*.json`; ledger `optimize/verify/claims_news3.py`, 21/21; selftest 5/5).

---

## Part 0 — The experiment inventory (what was actually run, in order)

| # | run | purpose | outcome |
|---|---|---|---|
| 1 | `--v1` replay, NQ | prove this pipeline's conventions == H1-A's | **PASS**, exact to 1e-12 |
| 2 | `--v1` replay, ES/GC/CL | same, other instruments | **PASS ×3**, exact |
| 3 | main run #1, NQ/ES/GC/CL | first full measurement | V2 PASS 4/4 · **V3 FAIL 4/4** → results quarantined |
| 4 | main run #2, NQ/ES/GC/CL | controls re-drawn vs FULL calendar | V3 still 1.20–1.64× → CL passes, 3 fail |
| 5 | main run #3, NQ/ES/GC/CL/**RTY** | quiet-minute falsifier added; per-event dumps; RTY holdout | **ALL GATES PASS 5/5** — these are the results of record |
| 6 | local analysis | pre-registered confirmatory test + pre-committed splits | RTY **CONFIRMED**; era/series/decomposition below |
| 7 | ledger | 3 claims added, full ledger + selftest | 21/21 · 5/5 |

No result was published from runs 3–4. The only numbers of record come from run 5, whose release
cells are identical to run 3's (same events, same code — only the *controls* were wrong earlier).

---

## Part 1 — Design, in full detail

### 1.1 Events

- Source: TradingView US calendar (verified provenance: `actual` = first print #119, `previous` =
  point-in-time #120), floor 2016 (2019 for RTY), through **2026-07** — current data.
- Series: the 4 verified (**Non Farm Payrolls, Inflation Rate MoM, Retail Sales MoM, Durable Goods
  Orders MoM**) + **Fed Interest Rate Decision** on all instruments; + **EIA/API crude** on CL only
  (⚠️ UNVERIFIED provenance, #123, marked in every output row).
- Same-minute duplicates dropped (two series at the same 8:30 minute = ONE position, not two).
- Matched events: NQ/ES 574 · GC 571 · CL 1,405 · RTY 418.

### 1.2 The trade being priced (exact mechanics)

```
entry   = OPEN of the bar at (release − T)          ← H1-A's convention, proven identical by V1
stop    = entry ± entry·S%                          ← S in percent of price, H1-A's units
walk    every 1-minute bar from the entry bar THROUGH the release bar to (release + 15m)
        long stopped  if bar Low  ≤ stop; fill = min(bar Open, stop)   ← GAP-01: worse of line/open
        short stopped if bar High ≥ stop; fill = max(bar Open, stop)
exit    = CLOSE of the bar at (release + 15m) if never stopped
P&L($)  = signed points × point value; both directions simulated for every event, always
```

Grid: T ∈ {5, 15, 30} min × S ∈ {0.10, 0.20, 0.40}% × 2 directions = 18 cells/instrument/set.
Point values: NQ $20 · ES $50 · GC $100 · CL $1,000 · RTY $50 per point.

### 1.3 Costs (round trip, 1 contract) — deliberately harsher than WS-EARN's ladder

| scenario | formula | NQ | ES | GC | CL | RTY |
|---|---|---|---|---|---|---|
| optimistic | $2.50 + 1 tick | $7.50 | $15.00 | $12.50 | $12.50 | $7.50 |
| realistic | $2.50 + 2 ticks | $12.50 | $27.50 | $22.50 | $22.50 | $12.50 |
| stressed | $2.50 + 4 ticks | $22.50 | $52.50 | $42.50 | $42.50 | $22.50 |

Gross is reported beside net everywhere, so no cost assumption is load-bearing for the science.

### 1.4 Controls (the part that failed twice — full mechanics)

- **Same-minute control**: for each event, the same clock minute on a weekday 3–500 days away
  (seeded RNG, 60 attempts) that sits **≥60 minutes from ANY of the 39,221 scheduled events in the
  full calendar** — not merely days without a *tracked* release. This distinction is the whole
  Part-2 story.
- **Quiet-minute control**: same days, clock minute drawn uniformly from 11:00–13:59 ET, same
  full-calendar cleaning. Exists solely as the V3 falsifier.
- Counts (run 5): NQ/ES 576+574 · GC 576+574 · CL 1,412+1,410 · RTY (proportional).

---

## Part 2 — The verification log (two failures, both kept)

### 2.1 V1 — replay H1-A's own inputs through an independent implementation

H1-A decides a stop-out via *max adverse excursion ≥ stop distance*; this pipeline decides it via a
*boolean scan of the window* (`(Low ≤ entry − dist).any()`). Mathematically equivalent, computationally
different — a mismatch in entry bar, window boundary, stop arithmetic, or event matching would break
equality. Replaying H1-A's own calendar (`us_high_impact.csv`) through this pipeline:

> **All 16 RELEASES cells × {long, short, either} reproduce `h1a_stopout_{NQ,ES,GC,CL}.json`
> exactly (|Δ| < 1e-12), 4/4 instruments.** Consequence: H1-A's survival grid and this study's
> ride cells compose — same entry, same windows, same units.

### 2.2 V2 — the known release-minute effect must be present

Release-bar |open→close| vs the same event's own prior hour (bars −60…−6), mean of per-event ratios:

| | NQ | ES | GC | CL | RTY |
|---|---|---|---|---|---|
| events | **11.76×** [10.30, 13.21] | **11.89×** [10.44, 13.35] | **12.28×** [11.15, 13.40] | **5.14×** [4.82, 5.46] | **15.03×** [12.78, 17.27] |

### 2.3 V3 — the falsifier that failed twice, and what each failure taught

**Round 1 — FAIL 4/4.** Controls drawn H1-A-style ("no *tracked* release that day") showed a
"jump" of **2.38× (NQ), 2.30× (ES), 2.52× (GC), 1.37× (CL)** at minutes where nothing was supposed
to happen. Standing rule applied — *read a failing gate as evidence about the gate/inputs first* —
and the inputs were guilty: 8:30 ET on an ordinary Thursday carries **Initial Jobless Claims, PPI,
GDP, trade balance…** — releases outside the tracked set. The phantom jump was other people's news.
⭐⭐ **Corollary filed for the whole programme: every control ever drawn against only the tracked
series shares this contamination — including H1-A's own, whose danger ratios are therefore
UNDERSTATED (its control was noisier than a true quiet window). Biased against our effects, so no
closed verdict flips — but the rule stands: clean controls against the FULL calendar.**

**Round 2 — still failing at 1.46× / 1.38× / 1.64× (CL 1.20×, passing).** Full-calendar cleaning
removed half the phantom. The residual could be (a) the pipeline inventing jumps, or (b) the 8:30
minute being genuinely special even without US releases — deterministic time-of-day volatility plus
**non-US events the US-only calendar cannot exclude (ECB lands 8:15/8:45 ET)**. Asserting (b)
without a test would have been tuning the gate to pass — the exact sin the S2 probe saga forbids.

**Round 3 — the discriminator.** A second control set at genuinely quiet clock minutes
(11:00–13:59 ET, identical cleaning). If the pipeline invents jumps, it invents them at noon too;
if the 8:30 minute is special, noon comes back ≈1:

| | NQ | ES | GC | CL | RTY |
|---|---|---|---|---|---|
| quiet minutes (V3, must be <1.2) | **0.89×** | **0.93×** | **0.92×** | **0.94×** | **0.92×** — **PASS 5/5** |
| same-minute floor (declared, not hidden) | 1.46× | 1.38× | 1.64× | 1.20× | — |
| ⇒ events over their own floor | **8.0×** | **8.6×** | **7.5×** | **4.3×** | — |

The V3 *threshold* was never touched across all three rounds. The inputs were fixed once, the
hypothesis was split once, and the falsifier stayed capable of failing throughout.

---

## Part 3 — Finding A: the pre-release drift predicts NOTHING (goal row 4, final)

Test: sign(close(rel−1m) − close(rel−60m)) vs sign(close(rel+15m) − close(rel−1m)) — "does the last
hour's lean tell you which way the release resolves?" — Wilson 95% CIs, break-even 71% (#111):

| instrument | releases ALL | control ALL | FOMC subset | verdict |
|---|---|---|---|---|
| NQ | 0.484 [0.443, 0.525] | 0.461 | **0.390 [0.292, 0.498]** | null |
| ES | 0.488 [0.446, 0.530] | 0.456 | 0.434 | null |
| GC | 0.487 [0.446, 0.529] | 0.484 | 0.463 | null |
| CL | 0.506 [0.479, 0.532] | 0.474 | 0.476 | null |
| RTY | 0.500 [0.452, 0.549] | 0.487 | 0.443 | null |

- **Powered, and provably so** (ledger claim `P1-DRIFT-DEAD`'s V3): every upper bound < 0.71
  (max 0.549) — the test could reject tradeability and did. No low-power null smuggled in.
- Release accuracy ≈ its own control everywhere (max gap 0.045): whatever continuation exists is
  the market's ordinary base rate, not news information.
- The Lucca–Moench pre-FOMC prior did not become a direction signal; FOMC leans *inverse* (0.39,
  n=82 — a lean, CI touches 0.50).

**With H1-B/C (consensus inputs, both anchors) this closes EVERY directional input of the owner's
Phase 1: measured, powered, null.**

---

## Part 4 — Finding B: the announcement premium (full anatomy)

### 4.1 The exploratory grid (run 5, release cells; controls in parentheses)

NQ — gross $/event, 95% CI, net at realistic costs; * = CI excludes 0:

| cell | LONG | SHORT |
|---|---|---|
| T=5 S=0.10% | **+83.10 [+19.28, +146.92]\*** net +70.60 (ctl +4.67) | −37.51 [−85.73, +10.71] (ctl −15.27) |
| T=5 S=0.20% | **+84.24 [+11.20, +157.29]\*** net +71.74 (ctl +4.53) | −29.66 [−97.15, +37.83] (ctl −12.24) |
| T=5 S=0.40% | **+103.28 [+21.02, +185.54]\*** net +90.78 (ctl +5.10) | −85.44 [−168.26, −2.63]\* (ctl −8.75) |
| T=15 S=0.20% | **+99.80 [+25.93, +173.67]\*** net +87.30 (ctl −3.72) | −59.33 [−126.20, +7.53] (ctl −0.24) |
| T=30 S=0.40% | **+136.77 [+50.18, +223.36]\*** net +124.27 (ctl +0.00) | −118.55 [−200.51, −36.59]\* (ctl +5.07) |

(18 NQ cells total in `p1_ride_NQ.csv`; every long cell positive, every short cell negative.)
ES: same shape, smaller (long +37 to +90, 8/9 long cells CI>0). GC: long positive but CIs straddle
0 at most cells. **CL: long ≈ 0 everywhere, short significantly negative — no premium in oil.**

The long/short mirror around a positive mean + null controls = an **unconditional mean drift
upward during release windows on release days only**. Given Part 3 (direction unpredictable per
event), this is not forecasting — it is the **Savor–Wilson announcement premium**: compensation
for holding equity risk through scheduled macro resolution. It appears exactly where the theory
puts it: equity indices strongly, gold weakly, oil not at all.

### 4.2 The confirmatory test (the step that turns a table into a finding)

Pre-registered on #125 **before RTY's price file was ever loaded by this workstream**: RTY, LONG,
T=5, S=0.20%, gross mean > 0, one-sided t, α=0.05 — one test, no alternates, no peeking.

> **RESULT: +$69.54/event, 95% CI [+27.21, +111.86], t = 3.22, one-sided p = 0.0007, n = 418 —
> CONFIRMED.** Net +$57.04 realistic. All 9 RTY long cells positive with CIs clear of zero
> (+$44.74 → +$101.65); all control cells within [−$13.67, +$2.94]. Stopped before the release at
> the primary cell: 4.8% — the premium is captured, not stopped away.

### 4.3 Where it lives — the pre-committed splits

**By series (primary cell, gross $/event):**

| series | NQ | ES | RTY | GC |
|---|---|---|---|---|
| **CPI (Inflation Rate MoM)** | **+424.22 [+168.97, +679.48]** | **+195.19 [+50.26, +340.11]** | **+262.40 [+122.75, +402.05]** | **+258.73 [+84.12, +433.34]** |
| Non Farm Payrolls | +112.92 ns | +53.58 ns | +56.25 ns | +61.83 ns |
| Durable Goods | +11.54 | +19.45 | +3.25 | −25.91 |
| Retail Sales MoM | **−79.20** | −36.65 | −22.09 | −32.60 |
| FOMC | −85.20 ns | −45.35 ns | +43.03 ns | +93.86 ns |

⭐ **CPI is the engine** — significant at 20-way Bonferroni on NQ (5 series × 4 instruments were
examined; p ≈ 1e-3, ×20 < 0.05), replicated on RTY and on GC (non-equity), while **Retail Sales at
the identical clock minute is negative**. That contrast is the registered V3: this is not "any
8:30 release in a bull era."

**By era (primary cell):** NQ 2016–19 +26.53 [−7.68, +60.75] · 2020–21 +46.02 (wide) · 2022+
+149.47 [−3.80, +302.75]. RTY 2019 flat, then positive **every year 2021→2026**.

**CPI by year (gross $/event, n≈12/yr):**

| year | NQ | ES | RTY |
|---|---|---|---|
| 2016–20 | ≈ 0 (−133…+186, all ns) | ≈ 0 | ≈ 0 |
| 2021 | +537 | +173 | +166 |
| 2022 | **+1,220** | +550 | +310 |
| 2023 | −133 | +8 | +74 |
| 2024 | +311 | +175 | +554 |
| 2025 | **+1,279** | +635 | +654 |
| 2026 (7 ev.) | **+1,796** | +694 | +501 |

⚠️ **Era-concentrated and currently at its strongest.** Nothing in-sample can distinguish
"permanent premium, amplified when macro uncertainty is high" from "inflation-era regime that will
fade." The claim (`P1-CPI-ENGINE`) pins the sample mean and carries this in its blind-spot field.

**Decomposition (NQ, T=5, stop-free signed components):** pre-print +$30.64 [+7.04, +54.23] — a
small, real pre-drift; print + 15m +$23.39 [−87.05, +133.83] — the resolution side holds the
variance. Both contribute; neither dominates cleanly.

### 4.4 ⭐ The distribution anatomy — what kind of edge this actually is

Per-event P&L at the primary long cell:

| | NQ | ES | RTY | GC | CL |
|---|---|---|---|---|---|
| win rate | **44.6%** | 44.9% | 39.7% | 41.3% | 33.5% |
| median | **−$50** | −$25 | −$136 | −$233 | −$95 |
| 5th percentile | −$806 | −$523 | −$233 | −$606 | −$188 |
| 95th percentile | **+$1,835** | +$1,079 | +$946 | +$1,420 | +$448 |
| best event | **+$7,310** — CPI 2022-12-13 | +$4,125 — same day | +$2,930 — CPI 2025-01-15 | +$6,670 — CPI 2026-07-14 | +$1,750 |
| worst event | −$1,218 — FOMC 2026-06-17 | −$758 — same day | −$300 — same day | −$1,040 | −$249 |

> ⭐⭐ **The premium loses more often than it wins.** Median negative, win rate 40–45% — the entire
> positive mean lives in the right tail (p95 ≈ 20× |median|). NQ CPI subset: win 51.7%, median
> +$25, p95 +$2,952. **This is a long-volatility payoff: lose small often, get paid rarely and
> hugely** — the profile of a long option, harvested with a futures position and a stop.
>
> ⭐ This is precisely the shape of the owner's Phase-3 intuition (*"small stop loss and big take
> profit, so any way we profit from the craziness"*) — realized on the LONG side only. The data
> says the intuition was half right: the convexity is there, but it is not symmetric. **The short
> leg does not have a premium to harvest — it pays one.** M3's straddle must be long-tilted.

⚠️ Consequence for expectations: at 1 contract this is ~54 events/yr and net ~+$3,893/yr (NQ),
+$3,141 (RTY) at the primary cell — with single events swinging ±$1,500+. It will feel like
losing most weeks and being rescued by a handful of CPI days. That is what the distribution says
it is supposed to feel like.

### 4.5 Worked example (concrete, one contract, NQ, CPI days only)

12 CPI events/year × mean +$424 gross = **+$5,088/yr**; costs 12 × $12.50 = $150; net ≈ **+$4,938**.
A typical year contains ~6 losing CPI days near −$100…−$800 and 2–3 days paying +$1,000…+$7,000.
Miss the single best day and the year can go flat — tail-driven, as the distribution table warns.

---

## Part 5 — The claims that pin this (ledger 21/21, selftest 5/5)

| claim | pins | V1 | V2 | V3 (falsifier) |
|---|---|---|---|---|
| `P1-RIDE-PREMIUM-RTY-CONFIRMED` | +69.54 | aggregate file == per-event mean (two artefacts, two code paths) | premium present on independent NQ/ES price files | **absent on RTY controls AND on CL** |
| `P1-DRIFT-DEAD` | 0 groups beat 0.5/0.71 | accuracy⊂CI + width ~ 1/√n | release accuracy == its own control | **every upper bound < 0.71** — the null is powered |
| `P1-CPI-ENGINE` | +424.22 | t-test at 20-way Bonferroni | replicates on RTY and GC (non-equity) | **Retail Sales at the same minute shows NO premium** |

Blind spots declared in code: all cells share one calendar and one control-draw implementation (a
defect there hits everything identically); era concentration is pinned only indirectly; n=116 CPI
events cannot separate permanent premium from regime.

## Part 6 — Threats that remain (so a later reader cannot say they were hidden)

1. **Regime risk** — the premium was ≈0 before 2020. If the macro-uncertainty era ends, it may too.
   Monitoring rule for any deployment: a rolling 24-event CPI mean below $0 is the alarm.
2. **Correlated instruments** — NQ/ES/RTY confirm the same macro exposure three ways; GC is the
   only semi-independent replication. This is 2 independent confirmations, not 4.
3. **Exploratory multiplicity** — only the RTY primary test and the three ledger claims carry
   confirmatory weight; the 36-cell tables are description, not inference.
4. **1-minute bars** — intrabar path within the release minute is invisible here; M3's 1-second
   work will see it (and the 94%-of-stop-outs-are-1s-sweeps threat lives exactly there).
5. **No quantity term in the engine** — deployment of anything here waits on the sizing decision.

## Part 7 — What went well / what went wrong

**Well:** the pre-registration turned an exploratory pattern into a confirmed claim in a single
shot; V3 failed loudly *before* any number existed and both failures produced durable rules
("clean controls against the FULL calendar"; "split the hypothesis, don't loosen the threshold");
per-event dumps mean every split in this report reproduces from committed CSVs with no re-run.

**Wrong, kept visible:** round-1 V3 blamed the pipeline for contaminated inputs; the stage's own
launching audit misclaimed H1-A was never run (corrected same-day in the audit report and #125);
and the first version of this stage's plan had survival scheduled for re-measurement that H1-A had
already done — caught before compute was spent, which is the cheapest kind of wrong.
