---
name: ws-news2-progress-2026-08-08
description: "Complete progress report: every workstream, issue, experiment, result, defect and open item since round two of the news research began. Written so nothing is dropped."
type: report
date: 2026-08-08
issues: [109, 110, 111, 112, 113, 114, 115, 116, 117]
---

# Progress report — everything since round two

**Two programmes are live in this worktree.** Both were opened after the original news study (round 1)
closed. Nothing below is a plan; every number is from a completed run whose report exists in this repo.

---

# PART 0 — WHERE WE ARE IN ONE PAGE

| programme | issues | status |
|---|---|---|
| **WS-EARN** — earnings announcements → Nasdaq | #109–#113 | **Stage 4 complete, H1 REJECTED.** One approach of 2–6 spent. #113 closed. |
| **WS-NEWS2** — per-release × per-instrument news, on real consensus | #114–#117 | **Consensus data SOLVED today.** Phase 1 H1-A done. H1-B/H1-C now unblocked. |

**The single biggest change today: the consensus-data problem is solved.** Seven sources failed; the
owner supplied TradingView, which works, carries a correct UTC timestamp, and reaches back to 2013.

---

# PART 1 — WS-EARN (earnings): #109–#113

## What was asked

Does an earnings announcement by a top Nasdaq-100 company move the Nasdaq price predictably?

## Stage 1 — the timestamp table (#110) — ⏳ awaiting your check

**201 earnings events, 19 companies, 2024→2026, timestamped to the second.** Later extended to
**783 events over 16 years (2010→2026)** for Stage 4.

**Eleven silent data defects were found and fixed.** Every one produced plausible output with no error:

| # | defect |
|---|---|
| 1 | **EDGAR's JSON timestamps are inconsistent** — UTC for some filers, Eastern-mislabelled-as-`Z` for others. **22 events 4–5 h wrong** |
| 2 | Applied Materials filed a quarter under **Item 2.01**, not 2.02 — item-code filtering deleted it silently |
| 3 | **Tesla files Item 2.02 for delivery reports too** — 11 earnings + 11 deliveries, identical codes |
| 4 | Foreign issuers file **Form 6-K** with no item codes at all |
| 5 | I read EDGAR's **index pages** as filings — **silently zeroed Lam Research 11 → 0** |
| 6 | **SPCX has no earnings history** despite 3.73% index weight — recently public |
| 7 | **Corporate reorganisations change the CIK** — GOOGL lost 2010–2015, AVGO lost 2010–2018 (~52 events) |
| 8 | **Intel files the same earnings twice**, the duplicate dated the next morning — a *wrong time*, not just a double count |
| 9 | Two Tesla misclassifications (threshold too strict; delivery markers outranking earnings) |
| 10 | A single socket timeout killed a multi-hour job |
| 11 | **`-index-headers.html` 404s before ~2013** — 26% of the 16-year set fell back to the untrusted timestamp |

Defects **7 and 11 could not appear** in the 2.4-year pilot; they exist only once history is extended.
Both were caught by the **time-of-day stability check**, not by inspection.

**Five verification checks, all passed:** 0 duplicates and regular cadence 19/19 companies; **43/43**
filings' own prose agrees with our timestamp; **3.05×** volatility at the announcement minute vs ~1.00×
at ±1h/±4h/±5h; random classification audit clean; **60/60** timestamps identical from a second EDGAR
endpoint.

> ⏳ **OPEN: criterion C4 — your 36-row TradingView check has never returned.** Stage 1 does not formally
> pass without it. Worksheet: `optimize/earnings/TRADINGVIEW-VERIFICATION.md`.

## Stage 2 — power analysis (#111) — ✅ complete

Run **before** searching, deliberately.

| finding | value |
|---|---|
| effective independent n (60-min horizon) | **83** — two methods agreed exactly |
| minimum detectable effect | $138 (1 min) → $575 (60 min) per contract |
| **share of the move a rule must capture** | **41%** ⇒ **~71% directional accuracy required** |
| multiple-testing budget at 55–60% accuracy | **2–6 approaches**, not 2,000 |
| volatility at the announcement minute | **4.98×** a matched normal minute |

⚠️ I made a framing error here and corrected it: I first compared MDE against *cost* and called it good
news. The right comparison is MDE against a *plausible* edge.

## Stage 3 — prior art (#112) — ✅ complete, and it changed the plan

**Christensen, Timmermann & Veliyev (2025), *JFE* 167** — 89+ billion after-hours quotes:

- Earnings **do** raise co-jump probability in the market index → **our 4.98× is independently confirmed**
- Price discovery completes in **milliseconds to seconds**
- The tradeable edge **closed after 2016**: 2.30%/trade frictionless in 2008–2015 → insignificant with
  spreads or a **5-second** delay
- Also confirms our BMO weakness finding

⇒ redirected Stage 4 from 1-minute bars to the **1-second archive**.

## Stage 4 — the pre-registered test (#113) — ✅ **H1 REJECTED**, issue closed

**783 events, 1-second bars, 8 cells, prediction filed before the run.**

| arm | passing |
|---|---|
| A — all events (headline) | **0 of 8** |
| B — outliers excluded | **0 of 8** |
| dumb control | **0 of 8** |
| era 2010–2015 / 2016–2026 | 0 of 8 each |

Win rates **45–51%**. ⭐ **The negative t-statistics are cost drag, not a reversal edge** — max
|t_gross| anywhere is **2.20**; the control shows gross t of −0.58 with net t of −3.68, entirely the
$9.50 round trip on a near-zero gross. **Without the dumb control this was publishable as a t = −3.68
discovery.**

## WS-EARN open items

| item | state |
|---|---|
| **C4 human verification** | ⏳ **never returned** |
| INTC's ~7-minute filing lag | ⏳ measured, **not corrected** |
| 5 of 6 approaches | unspent |
| pre-market announcements | out of scope since the universe narrowed |

---

# PART 2 — WS-NEWS2 (news round 2): #114–#117

## The design

Study **each individual release** against **each individual instrument**, separately, using the market's
**real consensus** — three numbers per event: `previous`, `forecast`, `actual`.

⚠️ **Why round 1 does not already answer this:** round 1's `expected` was
`mean of the previous LOOKBACK changes` — a **statistical proxy**, not the market's consensus. Round 1
said so itself (report 06, Part 10) and advised against buying consensus data *because it cost money*.
That advice is now moot: **the data is free.**

Round 1 also **never used `previous` at all**, so it could not distinguish "in line with consensus but a
huge change from last month" from "missed consensus but the level barely moved".

## Phase 1 (#115) — H1-A ✅ complete

**Can we survive the wait to the release?** 1,185 releases, 16 years, NQ and GC.

| instrument | wait | stop | **survive** | vs ordinary window |
|---|---|---|---|---|
| NQ | 5 min | 0.40% (~$573) | **98.2%** | **4.27×** |
| NQ | 15 min | 0.40% | 97.6% | 0.95× |
| NQ | 60 min | 0.40% | 90.0% | 0.90× |
| GC | 5 min | 0.40% (~$634) | **98.1%** | **2.05×** |
| GC | 60 min | 0.40% | 82.2% | 0.77× |

**Survival is not the blocker** — short wait + wide stop works.

⚠️ **My framing was wrong and the control caught it.** I predicted the pre-release window would be
*safer* (round 1: "the market goes quiet, 0.78×"). It is **1.31–2.92× MORE dangerous** at 5 minutes, on
**both instruments**. The two facts differ in what they measure — average move size vs worst excursion —
but the protection I implied does not exist.

⚠️ **A units flaw was caught before publication**: the first run used absolute point stops, making a
40-point stop 0.13% of NQ but 1.3% of GC. That produced a fake "gold is calmer" result. Discarded;
stops are now percent of price.

**H1-B / H1-C (does `forecast − previous` carry direction?) — now UNBLOCKED by today's data.**

## Phase 2 (#116) — specified, not started

Surprise → **POWER** and **DIRECTION**, per release × per instrument.
⚠️ ~30 releases × 9 instruments = **~270 pairs**; the multiple-testing correction must be fixed before
running. A theory-first shortlist (~20 pairs) is the recommended option.

## Phase 3 (#117) — specified, not started

Execution at the release second. ⚠️ Expected to fail on latency: gold's own decomposition says
**$132 of $137 is consumed inside the release minute**, and no sizing layer exists to express the
proposed multi-contract straddle.

---

# PART 3 — TODAY: the consensus-data problem, solved

## Sources probed — 7 failed, 1 worked

| source | outcome |
|---|---|
| investing.com | 403 to curl everywhere; WebFetch renders **today only** |
| ForexFactory | 200 ×3, then **403 to everything** including WebFetch |
| Trading Economics (site / API) | date params ignored / **410 guest discontinued** |
| FXStreet | **401** |
| Econoday | date params ignored — current week for a 2010 request |
| DailyFX | **403** |
| Nasdaq API | reachable, values correct, but **no date field** and an unreliable date param |
| **✅ TradingView** | **works, unauthenticated, correct UTC timestamps, 2013→2026** |

## What the TradingView data gives us

| | |
|---|---|
| rows | **39,221** US events |
| span | **2013-01-04 → 2026-08-31** |
| distinct **titles** (events) | **649** |
| rows with actual + forecast + previous | **16,011 (40.8%)** — plus 16,000 with parsed numeric triples |
| importance | high 2,118 · medium 16,474 · low 20,629 |

⭐ **The decisive property: a real UTC timestamp with DST correctly encoded.** NFP is `13:30Z` in winter
and `12:30Z` in summer — both **08:30 ET**. **164 of 164 rows exactly 08:30.** That is precisely what
the Nasdaq API lacked and what cost 22 events in #110.

## Cross-validated against our authoritative FRED dates

| event | exact-ET match | | era | match |
|---|---|---|---|---|
| NFP | **98%** | | 2013 | 18–44% |
| FOMC | **95%** | | 2014–2019 | 73–100% |
| PPI | 84% | | **2020–2026** | **92–97%** |
| CPI / retail | 81% | | | |
| PCE | 79% | | | |
| GDP | 77% | | | |

**The residual gap is coverage by era, not misalignment.** ⇒ **use 2014+**.

## ⭐⭐ It closes the documented ISM gap

`fetch_calendar.py` records that FRED **cannot** supply ISM (proprietary; rule-derived dates were
deliberately rejected). TradingView carries **ISM Manufacturing PMI, JOLTs, Michigan Sentiment, Building
Permits, Durable Goods** and the separate **Fed Press Conference** — the entire 10:00 ET slot our study
had zero coverage of, plus the mis-timed press-conference event flagged in the release-universe review.

## Four data-structure traps found today

1. **The file is named 2010 but starts 2013-01-04** — TradingView returns `no_data` before 2013.
2. **`indicator` is a category; `title` is the event.** "Interest Rate" holds 3,653 rows including Fed
   speeches. Joining on `indicator` mixes speeches into rate decisions.
3. **TradingView has a casing inconsistency in its own data**: `Inflation Rate MoM` (1) vs
   `Inflation Rate Mom` (157).
4. **GDP publishes three times per quarter** (Advance / 2nd / Final). Mapping one matched 27% and looked
   like a source failure; it was my misunderstanding.

## Why I missed TradingView

Full post-mortem: `docs/POSTMORTEM-why-i-missed-tradingview.md`. **I could have run it; I never tried.**
I searched *who publishes calendars* (news vendors) instead of *who needs calendars* (charting
platforms), ignored that TradingView was already named in our own verification workflow, and stopped
searching once I had a workaround — without treating the workaround's growing complexity as evidence
about the input.

---

# PART 4 — EVERYTHING STILL OPEN

| # | item | programme | blocked by |
|---|---|---|---|
| 1 | **C4 — your 36-row TradingView earnings check** | WS-EARN #110 | **you** |
| 2 | INTC ~7-minute filing lag correction | WS-EARN #110 | nothing |
| 3 | **ALFRED revision check** — is TradingView's `actual` a first print or a revision? | WS-NEWS2 #114 | nothing |
| 4 | H1-B / H1-C — does `forecast − previous` carry direction? | WS-NEWS2 #115 | **now unblocked** |
| 5 | H1-A on the other 7 instruments | WS-NEWS2 #115 | shorter price history |
| 6 | Phase 2 design — the ~270-pair multiple-testing correction | WS-NEWS2 #116 | decision |
| 7 | Phase 3 — latency test | WS-NEWS2 #117 | Phases 1–2 |
| 8 | Sizing layer — the one positive result in the whole programme cannot be expressed | cross-cutting | **owner's call** |

## Also carried forward from the meta-study

`docs/HIGH-VOLATILITY-META-STUDY.md` — both prior programmes failed on **scheduled** events, while the
deployed strategy is **volatility-seeking** and earns in **unscheduled** turbulence. The proposed test —
strategy edge on announcement days vs matched high-volatility non-announcement days — remains unrun.

---

# PART 5 — SUGGESTED NEXT STEPS, RANKED

### 1. ⭐ ALFRED revision check — before anything consumes the new data
If TradingView's `actual` is a **revision** rather than the first print, every consensus result would be
look-ahead contaminated. Payrolls alone were revised **−801k to −1,032k** in 2025. Cheap, and it gates
everything.

### 2. ⭐ H1-B / H1-C — the question Phase 1 now rests on
Does `forecast − previous` predict direction? This is the first thing the new data makes possible, and
it is the only route by which pre-positioning is not a coin flip.

### 3. Your C4 check on the earnings worksheet
36 rows. Still the only fully independent test of those timestamps.

### 4. Fix the pre-registration in #116 before Phase 2 runs
270 pairs must not be tested freely. My recommendation: a theory-first shortlist (~20 pairs), fixed in
writing.

### 5. Re-run H1-A per instrument
Your premise is that a release may move oil and not the Nasdaq. Only NQ and GC have 16-year frames; the
other seven need coverage measured first.

### 6. Decide on the sizing layer
Not research — an architecture decision, and yours. Until it exists, every volatility finding is
unmonetisable by construction.
