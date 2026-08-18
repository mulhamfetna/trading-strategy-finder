---
name: postmortem-why-i-missed-tradingview
description: "Why I probed seven sources and never tried TradingView — whose public API works from this environment, solves the date problem outright, and was already named in our own verification workflow."
type: postmortem
date: 2026-08-08
issue: 114
---

# Why I missed TradingView

**The short answer: I could have run it. I never tried.**

The endpoint works from this environment, unauthenticated, first attempt:

```
GET https://economic-calendar.tradingview.com/events?from=2015-06-01T00:00:00Z&to=2015-06-30T23:59:59Z&countries=US
→ HTTP 200, status=ok, 182 rows
```

No block, no 403, no rate limit, no auth. It was not a capability problem.

---

## What I actually did

Seven sources, in this order:

| # | source | outcome |
|---|---|---|
| 1 | investing.com | 403 (curl); WebFetch renders today only |
| 2 | ForexFactory | 200 ×3, then 403 to everything incl. WebFetch |
| 3 | Trading Economics (site) | date params ignored |
| 4 | Trading Economics (API) | 410 — guest discontinued |
| 5 | FXStreet | 401 |
| 6 | Econoday | date params ignored |
| 7 | DailyFX | 403 |
| 8 | Nasdaq API | reachable, but **no date field** |

I then spent considerable effort building an elaborate workaround for #8 — taking dates from FRED and
consensus from Nasdaq via a ±2-day window search, with ambiguity guards — because I had concluded no
source carried both.

**That conclusion was false, and one request would have shown it.**

---

## The three failures behind it

### 1. I searched a category, not a capability

Every candidate was "a site that publishes an economic calendar" — news and data vendors. TradingView
is a **charting platform**, so it never entered the candidate set.

But the requirement was never "a calendar website". It was *"anything that will serve me actual /
forecast / previous with a timestamp."* Charting platforms need exactly that data to annotate charts,
and they expose it to their own front-ends over public endpoints.

**Searching by who-publishes-X rather than by who-needs-X excluded the whole class that had it.**

### 2. It was already in front of me, repeatedly

TradingView appears **throughout this project's own workflow**:

- `TRADINGVIEW-VERIFICATION.md` — the 36-row worksheet I wrote, instructing *"Open TradingView, symbol
  NQ1!"*
- The C4 criterion in #110 is literally called the TradingView check
- The owner named it in conversation as the verification tool

I wrote a file with TradingView in its name, and did not ask whether the tool I was sending the owner to
might also serve the data programmatically.

### 3. I stopped searching once I had a workaround

After the Nasdaq API proved reachable, I switched from *finding a source* to *engineering around a
deficient one*. The workaround was clever — and cleverness on a bad input is the most expensive kind of
work, because it produces something that looks like progress.

The signal I ignored: **the workaround was elaborate.** A ±2-day window search with ambiguity guards, a
disambiguation rule, and an "actual" cross-check is a lot of machinery to compensate for a missing
column. Difficulty of workaround is evidence about the input, and I treated it as a puzzle instead.

---

## What it cost

| | |
|---|---|
| built and thrown away | ForexFactory scraper (blocked after 3 requests) |
| built and superseded | Nasdaq join — 2,145 of 3,985 days fetched before it was abandoned |
| wrong claim published | "the date parameter is off by one", verified 3× on three dates whose neighbours I never checked; retracted in `SOURCE-EVALUATION-consensus.md` and #114 |
| what the right source gave, immediately | a real UTC timestamp, DST correct, **164/164 NFP rows at exactly 08:30 ET** |

---

## What changes

1. **Before concluding "no source has X", enumerate who NEEDS X, not who publishes it.** Charting
   platforms, brokers, backtesting libraries and trading apps all consume economic calendars and expose
   them to their own clients.
2. **Check the tools already named in the project's own workflow.** If the owner uses a tool to verify
   something by hand, ask whether it can be queried directly.
3. **Treat an elaborate workaround as a signal about the input.** When compensating machinery starts
   growing guards and windows, stop and re-examine whether the input is the right one.
4. **Test a candidate before excluding it.** TradingView was excluded without a single request. Cost of
   the test: one `curl`.
