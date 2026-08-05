---
name: ws-earn-verification-round-2
description: "WS-EARN Stage 1 second verification round (#110) — five independent checks on the 201-event table, all passed, plus a tested answer to whether announcement times can be scraped where no API supplies them."
type: verification
date: 2026-08-04
issue: 110
workstream: earnings
---

# WS-EARN Stage 1 — second verification round

Independent audit of `earnings_timestamps_FINAL.csv` (201 events, 19 companies), run **after**
collection. Reproduce with `python3 optimize/earnings/verify_round2.py`.

**Result: all five checks passed.** Two of the checks were wrong on their first run and had to be fixed
before they measured anything — both fixes are recorded below, because a check that passes only after
being adjusted deserves more scrutiny than one that passed first time.

---

## V1 — structural integrity ✅

| | |
|---|---|
| duplicate accession numbers | **0** |
| duplicate (ticker, timestamp) | **0** |
| companies with irregular quarterly cadence | **0 of 19** (all gaps 76–118 days) |
| filings whose stated period is *after* the announcement | **0** |

---

## V2 — the filing's own text vs our timestamp ✅

Many 8-K bodies state the date in prose: *"On January 28, 2026, Tesla, Inc. released its financial
results…"*. That is a claim made **inside the document**, independent of the acceptance metadata.

| | |
|---|---|
| filings stating an announcement date in their text | 43 of 201 |
| **agree with our timestamp (±1 day)** | **43 (100.0%)** |
| disagree | **0** |
| no such sentence present | 158 |

### ⚠️ This check was wrong on its first run

The first version matched any `On <Month> <day>, <year>` and reported **62 disagreements**, including
every Apple filing as exactly 14 days off. It was matching Apple's *dividend payable* sentence
("…payable on February 15, 2024…"), which sits 14 days after the announcement.

A wrong check that fails loudly is recoverable. The dangerous version is the one that had produced a
confident 67% "agreement" rate — a plausible-looking number that was measuring the wrong sentence. The
fix requires a results verb (`released|announced|issued|reported|published`) within the same sentence.

---

## V3 — price-tape alignment ✅ (falsification only)

> 🚫 **This is not a timestamp source.** It can only say *the set of timestamps is grossly misaligned*
> or *it is not*. **No timestamp may be moved because of what it shows** — doing so would make the
> Stage 4 finding a tautology. Same use `optimize/fundamentals/verify_timezone.py` makes of it for
> macro releases.

Mean |1-minute return| at offsets from the announcement, each bar compared against **a normal bar at
the same clock time**:

| offset | vs same time-of-day | flat-baseline view |
|---|---:|---:|
| −5 h | **1.02×** | 1.61× |
| −4 h | **1.07×** | 1.52× |
| −1 h | **1.00×** | 1.34× |
| **0 (announcement)** | **3.05×** | 3.18× |
| +1 h | **1.03×** | 1.09× |
| +4 h | **0.92×** | 0.75× |
| +5 h | **1.12×** | 0.78× |

Every distant offset sits at essentially **1.00×** while the announcement minute is **3×**. Had the
JSON-timezone defect survived, the 22 affected events (MSFT, LRCX) would have put energy at −240/−300.
They do not.

**Peak is at offset −1, not 0** (3.37×). That is expected and useful: **the press release crosses the
wire slightly before the SEC accepts the 8-K.** This is the first population-level estimate of the
wire-vs-acceptance gap that criterion C5 asks about — **on the order of one minute, not tens of
minutes.** It is an aggregate, not a per-company correction, and it is *not* applied to any timestamp.

### ⚠️ This check was also wrong on its first run

The first version compared every event to a flat all-hours average. That made the **BMO** events
(WMT 06:59, ASML 06:0x) look like a **1.06× non-event** — because a 06:00 pre-market bar was being
measured against 09:30–16:00 activity. With a time-of-day-matched baseline the same events read
**1.36×**.

**Lesson worth carrying into Stage 4: the baseline must be time-of-day matched.** A flat baseline will
systematically understate every pre-market event and overstate nothing.

BMO remains weak (1.36× at offset 0, n=18) even after the fix. That is *not* a timestamp problem — the
AMC events share the identical pipeline and show 3×. It is a candidate finding for Stage 2: pre-market
releases from mid-weight companies (WMT 2.11%, ASML 1.58%) may simply not move NQ much. **n=18 is far
too small to conclude anything and it is recorded as a question, not a result.**

---

## V4 — classification audit ✅

Random sample of 12 (fixed seed, reproducible), each shown with the evidence that decided it. Spot
checks confirmed: `NVDA q1fy27pr.htm` + `q1fy27cfocommentary.htm`, `GOOGL googexhibit991q32024.htm`
→ *"Alphabet Announces Third Quarter 2024 Results"*.

---

## V5 — timestamp re-fetch from a different endpoint ✅

Our timestamps come from `{accession}-index-headers.html`. This check reads the **raw submission
`.txt` header** — a different file — for a random 60-event sample.

| | |
|---|---|
| confirmed identical | **60** |
| mismatch | **0** |
| unreachable | **0** |

---

## Can we scrape the times that no API supplies? — yes, and it found a **material defect**

### ⚠️ Correction to an earlier version of this document

An earlier revision reported *"2 of 8 IR listings usable"* and concluded scraping was **"mostly no"**.
That figure came from a **partially-completed probe** whose output I read before it finished — the exact
"never conclude from truncated output" mistake this project has a standing rule about. The complete
probe of all 19 companies:

| verdict | n | companies |
|---|---:|---|
| **usable — clock times present** | **4** | MSFT, AMZN, **AMD**, **INTC** |
| dates only | 1 | WMT |
| no timestamps | 10 | AAPL, NVDA, GOOGL, META, ASML, CSCO, COST, LRCX, PLTR, NFLX |
| connection refused | 4 | AVGO, TSLA, MU, AMAT |

More importantly, **AMD and INTC expose 10–12 clock-stamped releases from a single page fetch** — 60 and
77 timestamps respectively, reaching back into 2024. That is a usable independent series, not a one-off.

### 🔴 What it found: the acceptance timestamp is NOT the announcement time for every company

| company | its own IR site | our EDGAR acceptance | measured gap |
|---|---|---|---|
| **AMD** | 16:15:00, every quarter | 16:16–16:17 | **+91 s** (median, 6 events) |
| **INTC** | 16:01:00, every quarter | 16:04–16:13 | **+404 s ≈ 7 min** (median, 9 events) |

### The triangulation — three unconnected sources agree

The price tape has no relationship to either EDGAR or a corporate CMS. Volatility peak offset relative
to **our** timestamps, each bar measured against a normal bar at the same clock time:

| company | IR-site gap | **tape peak** | ratio at our timestamp |
|---|---|---|---|
| **AAPL** | (publishes no times) | **+0 min** | 6.95× |
| **AMD** | +91 s (~1.5 min) | **−1 min** | 2.99× |
| **INTC** | +404 s (~7 min) | **−7 min** ✓✓ | **1.32×** |
| MSFT | — | −1 min | 3.69× |
| NVDA | — | −1 min | 14.01× |
| META | — | −3 min | 4.54× |

**Intel's tape peak sits at exactly −7 minutes, matching the ~7-minute gap measured from Intel's own
website.** Two independent sources, one corporate and one market, agree.

The consequence is concrete: at our current Intel timestamps, Stage 4 would sample a nearly quiet minute
(**1.32×**) and **miss the real event at 3.22×**.

### What this does and does not license

**Does:** the table remains a *correct record of 8-K acceptance times* — that is verified five ways
above. But for C5 purposes, **acceptance ≠ announcement**, and the gap is company-specific and material.
AMD and INTC now have **documentary** offsets from an independent source.

**Does NOT:** licence shifting any timestamp using the tape. The tape is corroboration, never a source —
shifting timestamps to fit observed volatility is precisely the circularity this workstream is
pre-committed against. For the 15 companies with no published times the gap is **unmeasured**; the tape
*hints* at −1 to −3 minutes but that hint may not be used as a correction.

### Revised conclusion

Scraping is **not** a way to replace EDGAR timestamps — coverage is too patchy and Apple-style
`dateModified` fields decay (older Apple pages now return a `2026-05-13` bulk republish, so that route
degrades with age, backwards from what a historical study needs).

But it **is the only documentary route to the C5 per-company offset**, and it has already found a
7-minute error that would have silently degraded Stage 4 for Intel. **Recommendation: extend the scrape
to every company that publishes times, and treat companies with an unmeasured offset as carrying a known
uncertainty rather than a known timestamp.**

---

## What this round does and does not establish

**Does:** the timestamps are internally consistent, reproduce from a second EDGAR endpoint, agree with
the filings' own prose, and are not grossly misaligned with the price tape. The classification is
auditable row by row.

**Does not:** prove any individual timestamp is the exact announcement minute. Every check here is
either structural, or aggregate, or from the same organisation. **Criterion C4 — the human TradingView
check — remains the only fully independent test of the minute, and Stage 1 does not pass without it.**
