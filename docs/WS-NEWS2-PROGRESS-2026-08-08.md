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
*safer* (round 1: "the market goes quiet, 0.78×"). Measured against the time-of-day-matched control, the
5-minute pre-release window is **never safer and up to 4.27× more dangerous**, on **both instruments**.
The two facts differ in what they measure — average move size vs worst excursion — but the protection I
implied does not exist.

⚠️ **Figure corrected 2026-08-08**: this paragraph previously read "1.31–2.92×". That range appears
nowhere in `h1a_stopout_{NQ,GC}.json` — neither either-side nor per-side — and was a mis-transcription.
The measured either-side stop-out ratio at a 5-minute wait, release vs control:

| stop | NQ | GC |
|---|---|---|
| 0.05% | 1.18× | 1.01× |
| 0.10% | 1.47× | 1.10× |
| 0.20% | **2.92×** | 1.15× |
| 0.40% | **4.27×** | **2.05×** |

⭐ **The danger rises with the width of the stop.** A tight stop is hit at the pre-release window about
as often as at any other time; a *wide* stop is hit 3–4× more often. That is the signature of a
**rare large excursion**, not of generally choppier trading — which is why an average-move statistic
(round 1's 0.78×) and a worst-excursion statistic point in opposite directions on the same window.

⚠️ **A units flaw was caught before publication**: the first run used absolute point stops, making a
40-point stop 0.13% of NQ but 1.3% of GC. That produced a fake "gold is calmer" result. Discarded;
stops are now percent of price.

**H1-B / H1-C (does `forecast − previous` carry direction?) — now UNBLOCKED by today's data.**

## Phase 2 (#116) — specified, not started

Surprise → **POWER** and **DIRECTION**, per release × per instrument.
⚠️ **CORRECTED with real data: 103 release series (2016+, ≥40 releases) × 9 instruments = 927 pairs**,
not the ~270 the issue assumes. Bonferroni over 927 ⇒ |t| > 4.05, against a measured ceiling of 2.20 —
the full matrix is futile, so a theory-first shortlist is now the only decidable option, not merely the
recommended one. The correction must be fixed in writing before running.

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

⭐ **The decisive property: a real UTC timestamp with DST correctly encoded** — *from 2016 onward*. NFP is
`13:30Z` in winter and `12:30Z` in summer, both **08:30 ET**, **164 of 164 rows**. That is precisely what
the Nasdaq API lacked and what cost 22 events in #110.

## ⚠️⚠️ CORRECTION (same day, commit `35b66e7`): the pre-2016 rows are DST-BROKEN

I verified the timestamps **on NFP alone**, declared DST correct, and wired the file in on that basis.
True of NFP; **false of most of the file before 2016.**

A release sits at the same US-Eastern wall-clock time in January and July, so a series whose winter modal
ET time disagrees with its summer modal time was stored with a fixed offset. Audited per year over every
series:

| year | series inconsistent | | year | series inconsistent |
|---|---|---|---|---|
| **2013** | **6/8 — 75%** | | 2016 | 7/105 — 7% |
| **2014** | **65/72 — 90%** | | 2017 | 2/103 — 2% |
| **2015** | **79/87 — 91%** | | 2018–2025 | 0–3% |

**87 pre-2016 series are one hour late in summer**, including `Initial Jobless Claims` (08:30→09:30),
`EIA Crude Oil Stocks Change` (10:30→11:30), `Retail Sales MoM`, `PPI MoM`, `ISM Manufacturing PMI` and
`Fed Interest Rate Decision`. An event window built on them is centred an hour from the release and
returns a **manufactured null** — indistinguishable from a real one.

**NFP is clean pre-2016 (36/36).** I picked the one series that happens to be right and generalised.
Same defect class as #110's EDGAR `Z`-on-Eastern trap, caught there by a stability check and missed here
by inspection. `tv_calendar.py` now sets `MIN_YEAR = 2016` and `--verify` **fails** if any year ≥
`MIN_YEAR` breaks the audit — it can no longer pass on a single-series look.

## Cross-validated against our authoritative FRED dates

Re-scored on the usable era. Most of what I had written up as "coverage by era" was this defect:

| event | as first reported (2013+) | **actual (2016+)** |
|---|---|---|
| NFP | 98% | **98%** |
| FOMC | 95% | **95%** |
| retail sales | 81% | **95%** |
| CPI | 81% | **94%** |
| PPI | 84% | **94%** |
| PCE | 79% | **93%** |
| GDP | 77% | **90%** |

**The source is better than I first said — on the era where it is usable at all.** ⇒ **use 2016+.**

Cost of the constraint: 15,273 → **13,291** triple-value rows (−13%); 106 → **103** testable series; the
10 high-impact series are all retained. Cheap, and not optional.

## ⭐⭐ It closes the documented ISM gap

`fetch_calendar.py` records that FRED **cannot** supply ISM (proprietary; rule-derived dates were
deliberately rejected). TradingView carries **ISM Manufacturing PMI, JOLTs, Michigan Sentiment, Building
Permits, Durable Goods** and the separate **Fed Press Conference** — the entire 10:00 ET slot our study
had zero coverage of, plus the mis-timed press-conference event flagged in the release-universe review.

## Data-structure traps found today

1. **The file is named 2010 but starts 2013-01-04** — TradingView returns `no_data` before 2013.
2. ⚠️⚠️ **Pre-2016 summer rows are one hour late** (above). `MIN_YEAR = 2016`.
3. **`indicator` is a category; `title` is the event.** "Interest Rate" holds 3,653 rows including
   `Fed Williams Speech` (295) and `Fed Bostic Speech` (256) alongside `Fed Interest Rate Decision`
   (109). Joining on `indicator` mixes speeches into rate decisions.
4. **Titles fragment**: `Fed Press Conference` (68) / `Fed Monetary Policy Statement and press
   conference` (5) / `Fed press conference` (1). Read title maps off the value counts, never from the
   obvious spelling.
   ⚠️ **RETRACTED**: I first published this trap as *"`Inflation Rate MoM` (1) vs `Inflation Rate Mom`
   (157)"*. **There is no lower-case variant.** `Inflation Rate MoM` has 161 rows; the 1-row neighbour
   is `Inflation Rate MoM Final`, a different release. The rule is right; my example was invented rather
   than measured, and the phantom title has been removed from `FRED_TO_TV`.
5. **GDP publishes three times per quarter** (Advance / 2nd / Final). Mapping one matched 27% and looked
   like a source failure; it was my misunderstanding.
6. **⚠️ Timestamps are the SCHEDULED MINUTE, not the observed instant** — 0 of 39,221 rows carry a
   non-zero seconds field. Fine for Phases 1–2; **not** what Phase 3 needs. See #117.

## ⚠️ The study universe is 3.5× bigger than #116 assumed

#116 was written before we had a calendar and states *"~30 releases × 9 instruments = ~270 pairs"*.
Measured, on 2016+ with ≥40 releases: **103 series ⇒ 927 pairs.** Bonferroni over 927 ⇒ **|t| > 4.05**,
against a measured ceiling of |t_gross| = 2.20 anywhere in WS-EARN. The full matrix is not merely
strict — it is already known to be futile. **A theory-first shortlist is now the only decidable option.**

⚠️ TradingView's HIGH bucket is narrow: only **10** series are high-impact with ≥40 releases. **CPI MoM,
PPI MoM, ISM Manufacturing PMI and the Unemployment Rate are all filed MEDIUM.** A "3★ only" filter drops
them. The impact flag is a vendor opinion, not a fact about the tape.

## ⭐ The highest-n pair available, and it is the owner's own premise

| title | releases 2016+ | impact |
|---|---|---|
| **`EIA Crude Oil Stocks Change`** | **~510** | medium |
| `Initial Jobless Claims` | ~545 | medium |
| `EIA Gasoline Stocks Change` | ~490 | medium |
| `API Crude Oil Stock Change` | ~288 | medium |

*"A release may move oil a lot but not Nasdaq — so we trade oil"* — that release exists, it is weekly,
CL is already onboarded, and it has **never** been in our study set (round 1: 7 events, none energy).
⚠️ Weekly n is ~4× any monthly series, so an EIA/CL pair has materially more power than NFP/NQ; when
results are compared the n difference must be stated, or a power difference reads as an edge difference.

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
| 6 | Phase 2 design — the **927**-pair correction (P2-C3 is wrong as written) | WS-NEWS2 #116 | decision |
| 7 | Phase 3 — latency test | WS-NEWS2 #117 | Phases 1–2 |
| 7b | **Phase 3 step 0 — derive the release SECOND from the tape** (the calendar gives only the scheduled minute) | WS-NEWS2 #117 | nothing |
| 8 | Sizing layer — the one positive result in the whole programme cannot be expressed | cross-cutting | **owner's call** |

## Also carried forward from the meta-study

`docs/HIGH-VOLATILITY-META-STUDY.md` — both prior programmes failed on **scheduled** events, while the
deployed strategy is **volatility-seeking** and earns in **unscheduled** turbulence. The proposed test —
strategy edge on announcement days vs matched high-volatility non-announcement days — remains unrun.

---

# PART 5 — SUGGESTED NEXT STEPS, RANKED

### 1. ✅ DONE — ALFRED revision check: `actual` is the FIRST PRINT (#119, closed)
4 series, 503 releases. On the discriminating subset — releases where the first print and today's value
differ enough to tell the hypotheses apart — TradingView matches **the first print** and never the
revision:

| series | n discriminating | median revision | matches first | matches revised | verdict |
|---|---|---|---|---|---|
| Non Farm Payrolls | 116 | 66k jobs | **100%** | 0% | FIRST PRINT |
| Retail Sales MoM | 88 | 0.44pp | **100%** | 0% | FIRST PRINT |
| Durable Goods Orders MoM | 111 | 0.95pp | **99%** | 0% | FIRST PRINT |
| Inflation Rate MoM | 4 | 0.22pp | — | — | ⚠️ CANNOT TELL |

March 2020 payrolls were revised from −701k to **−1,398k** — doubled. TradingView carries −701k.

⭐ **CPI's CANNOT TELL is the decision rule working, not a disagreement.** CPI is revised by less than
the 0.1pp it is reported to, so 121 of 125 releases cannot distinguish the hypotheses at all. That is an
absence of power — and it is why two further series were run instead of calling V2 done.

⚠️ **Only half the surprise formula is cleared.** `actual` is verified; **`forecast` is not**. A
back-filled late consensus would contaminate `actual − forecast` just as badly.

### 1b. ✅ DONE — `previous` is POINT-IN-TIME; `forecast` cannot be verified (#120, closed)

| field | status |
|---|---|
| `actual` | ✅ **FIRST PRINT** (#119) |
| `previous` | ✅ **POINT-IN-TIME** — 119/103/92 discriminating releases → **99% / 98% / 99%** match to the value that stood that morning, **0%** to today's |
| `forecast` | ⚠️ **not verifiable** — no consensus archive exists. No evidence of contamination |

⭐⭐ **A back-fill cannot produce a point-in-time `previous`**: reproducing the prior month's value *as
of a past morning* needs a per-series vintage archive, which calendar vendors do not keep. **The row was
captured live** — which is the strongest (indirect) evidence for `forecast` as well.

⭐ **Test C, unexpected:** `previous` equals the prior `actual` only **3%** of the time for NFP but
**95%** for CPI. So `actual − previous` **means different things across series** — the revised-basis
change for payrolls, first-print-to-first-print for CPI. #116 defines it as the former for all series;
that must be fixed before Phase 2 pools them.

⚠️⚠️ **A pre-registered test of mine was confounded and I caught it before publishing.** B2 asked
whether the consensus error correlates with the later revision, on the logic that a forecast made before
the release cannot know a revision published months after. It fired (CPI Spearman +0.38, p<0.001) and
the conclusion would have been **wrong**: an informed consensus predicts revisions too, so the innocent
and contaminated hypotheses give the **same sign**. Splitting by horizon and controlling for `actual`
did not rescue it. **Lesson: design the falsifier so the innocent and claimed explanations predict
DIFFERENT signs**, or the test cannot decide anything however cleanly it runs.

### 2. ✅ DONE — H1-B / H1-C are NEGATIVE (#115)

**411 events, 2016–2026, 4 verified series, NQ and GC. 0 of 7 pre-registered cells clear Bonferroni
α = 0.00179 on either instrument.**

⭐⭐⭐ **The null is worth something only because of the planted-effect probe.** A null from a broken
pipeline is indistinguishable from a null from an absent edge — and this workstream produced a
*manufactured* null the same week (the DST defect). A synthetic feature equal to the outcome plus noise
was planted across r ∈ {0.05 … 0.40}: **study MDE r ≈ 0.195; smallest detected NQ r=0.15, GC r=0.20.**
The pipeline finds effects at and below its own resolution.

⭐ **GC H1-B 15m is a textbook case for P1-C2 in the OPPOSITE direction from round 1**: Pearson +0.154
(p=0.002) with Spearman +0.051 (p=0.31) and permutation p=0.308 — a fat-tail artefact Pearson alone
would have published. Round 1's gold result was the mirror image. Requiring both catches it either way.

⚠️⚠️ **This is "no effect of THIS SIZE", not "no effect".** A real anticipation edge below r≈0.195 is
plausible and invisible here. But #111 put the accuracy needed to pay costs at ~71%, well above what
r=0.195 implies — so an effect *large enough to trade* is absent, while a small one cannot be ruled out.

⭐ **P1-C5 GO/NO-GO resolves: survival is fine, direction is absent.** A pre-positioned trade is a coin
flip paying a full round trip (~$9.50) plus an elevated tail risk during the wait — negative expectancy
by construction. **Phase 1 produces no tradeable entry**, and sharpens Phase 2's question to whether the
*surprise* does better than the *anticipated change*.

### 3. ✅ DONE — #116 amended, and my own 927-pair figure was WRONG (#116, #121)

⚠️⚠️ **I published 927 pairs this morning. It is wrong.** "103 series × 9 instruments" silently assumed
all nine instruments had the 2016+ era. Verified exhaustively on the server:

| instruments | span |
|---|---|
| **NQ, GC** | 2010-06-06 → 2026-07 |
| **ES, CL, NG, HG, SI, RTY, YM** | **2025-01-01 → 2026-07 — EIGHTEEN MONTHS** |

**I counted the event side and never checked the price side.** Same comment, same error: I headlined
`EIA Crude Oil Stocks Change → CL` at "~510 releases". The calendar has ~510; the **CL price frame
reaches 79**. Wrong by ~6×. ⭐ And `EIA → NQ` reaches **545** — the oil release is best tested on the
*index*, the opposite of what I recommended.

⭐⭐ **The amended rule is not "big enough sample" but "can this pair DECIDE the question?"** #111 puts
break-even at ~71% accuracy ⇒ r = 0.613. A pair qualifies iff its MDE at the Bonferroni α is below that.
A pair whose MDE exceeds the tradeable threshold can only return a null that is **uninformative by
construction**, while consuming correction budget and weakening the pairs that could decide something.

| candidates | **decidable** | excluded |
|---|---|---|
| 1,327 | **221** (α = 0.000226) | 1,106 (83%), incl. 896 monthly-release pairs on 18-month instruments |

Committed as `phase2_pairs.csv` and ledger-checked, so the pre-registration is machine-verifiable.

⚠️ **The cross-instrument premise of this round is currently untestable for every monthly release** —
opened as **#121**, an owner decision (acquire history, or run the 221 and say what it cannot answer).

### 4. Phase 2 itself  ← **NEXT**
Does `forecast − previous` predict direction? This is the first thing the new data makes possible, and
it is the only route by which pre-positioning is not a coin flip.

### 4. Your C4 check on the earnings worksheet
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
