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

## Can we scrape the times that no API supplies? — tested, mostly **no**

The honest answer, with evidence rather than assertion.

**What works.** A *recent* Apple newsroom page carries JSON-LD `dateModified` = `2026-07-30T20:30:21Z`
= **16:30:21 ET**, against our EDGAR value of **16:30:28** — **7 seconds apart.** Genuine independent
corroboration. Intel's IR listing exposes `<time datetime="2026-07-23T16:01:00">`.

**Why it does not generalise.**

1. **The timestamp decays.** `datePublished` on Apple's pages carries a **date only** (`2026-07-30Z`).
   The field that has a clock time is `dateModified` — a *modification* time. Re-fetching Apple's older
   earnings pages returns `2026-05-13`, a bulk CMS republish that overwrote the original. **The signal
   degrades with age, which is exactly backwards for a historical study.**
2. **Coverage is poor.** Of 8 IR listing pages probed: 2 usable (MSFT, AMZN), 3 with no timestamps at
   all (AAPL, NVDA, GOOGL, META), 2 refused the connection (AVGO, TSLA).
3. **URL discovery is bespoke.** Guessing Apple's own slug pattern failed on **9 of 11** events.
4. **It measures a third distinct moment** — website publication — which is neither the wire release nor
   the SEC acceptance.

**Conclusion:** scraping can corroborate *individual recent* events and is worth using opportunistically
if a specific row is disputed. It cannot produce a reliable independent minute-level series across
2024–2026. The C5 question is better answered by V3's aggregate offset (≈ −1 minute) and by the human
chart check.

---

## What this round does and does not establish

**Does:** the timestamps are internally consistent, reproduce from a second EDGAR endpoint, agree with
the filings' own prose, and are not grossly misaligned with the price tape. The classification is
auditable row by row.

**Does not:** prove any individual timestamp is the exact announcement minute. Every check here is
either structural, or aggregate, or from the same organisation. **Criterion C4 — the human TradingView
check — remains the only fully independent test of the minute, and Stage 1 does not pass without it.**
