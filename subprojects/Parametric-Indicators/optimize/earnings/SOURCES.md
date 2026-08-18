---
name: ws-earn-stage1-sources
description: "WS-EARN Stage 1 (#110) — every source, retrieval rule and known limitation behind the earnings announcement timestamp table. Written so the table can be reproduced and audited rather than trusted."
type: provenance
date: 2026-08-04
issue: 110
workstream: earnings
---

# WS-EARN Stage 1 — sources and provenance

Everything the timestamp table is built from, how it was retrieved, and — the part that matters most —
**what it cannot tell you.**

---

## 1. Company universe

| | |
|---|---|
| source | `https://www.slickcharts.com/nasdaq100` |
| retrieved | 2026-08-04 14:02:53 UTC |
| frozen to | `data/ndx_weights_2026-08-04.csv` |
| sanity gate | 103 index lines, weights sum to **100.00%** — the script refuses to write a snapshot outside 95–105% |

**Why frozen rather than live.** Index weights move every day. A collector that fetched them live would
silently produce a different company set on every run and nobody would know which table came from which
universe. That is "a default you did not choose is a condition of your experiment", applied to the
universe. The snapshot is the experiment's condition, written down.

**Share classes are not companies.** GOOGL and GOOG are two index lines and one issuer filing one
earnings release. Deduplication is by **SEC CIK** — the only identifier that means "company". Weights
are summed across classes, which **reorders the ranking**: Alphabet's combined 11.08% moves it from
5th line to **2nd company**, ahead of Apple. Printed explicitly at run time so the reordering is visible.

⚠️ **Known bias, recorded not fixed.** This is *today's* top 20 applied to all of 2024–2026. A company
that was smaller in 2024 is still included, and one that has since dropped out is not. For a 2.6-year
span this is mild; over a 16-year span it would be severe. The wider top-20 collection exists so a
point-in-time universe can be reconstructed later without re-collecting anything.

---

## 2. Announcement timestamps — SEC EDGAR

| | |
|---|---|
| submissions | `https://data.sec.gov/submissions/CIK##########.json` |
| older shards | `filings.files[]`, fetched whenever a shard overlaps the span |
| document lists | `https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/index.json` |
| document text | `https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{document}` |
| **field used** | **`ACCEPTANCE-DATETIME` from `{accession}-index-headers.html`** — second precision, Eastern |
| field **NOT** used | `acceptanceDateTime` from the submissions JSON — see §2b, it is not internally consistent |
| rate limit | 0.15 s between requests (~6.7/s), inside SEC's 10/s fair-access policy |
| User-Agent | `MulhamFetna-Research contact@mulhamfetna.com` (SEC requires identification) |

**Older shards are not optional.** EDGAR's `recent` block holds only the latest ~1,000 filings. Mega-caps
file hundreds of Form 4s, so `recent` can cover well under two years. Missing the shards is how a company
silently loses its early quarters.

---

## 2b. ⚠️ EDGAR's JSON API is not internally consistent — the worst defect found in Stage 1

`data.sec.gov/submissions/CIK*.json` publishes `acceptanceDateTime` with a trailing **`Z`**, which means
UTC. For most filings it genuinely is UTC. **For some it is Eastern wall-clock with a spurious `Z`.**
Two filings from the same week, checked against EDGAR's own SGML header:

| | submissions JSON | SGML `ACCEPTANCE-DATETIME` | JSON is |
|---|---|---|---|
| MSFT `0001193125-26-323632` | `2026-07-29T16:04:53Z` | `20260729`**`160453`** | **Eastern** (identical digits) |
| AAPL `0000320193-26-000018` | `2026-07-30T20:30:28Z` | `20260730`**`163028`** | **UTC** (differs by 4 h) |

Both companies release just after the 16:00 ET close and the SGML header puts both there. Converting the
JSON field as UTC therefore lands Microsoft's earnings at **12:04 ET — four hours before it happened,
in the middle of the trading session instead of after the close.**

**Why this matters more than it looks.** For an event study a four-hour error is not a small
inaccuracy — it moves the event into a different trading session. The "reaction" measured would be
ordinary midday trading, and the real reaction would fall outside the observation window entirely. The
timestamp itself looks completely plausible; nothing errors.

**How it was caught.** Not by inspection — by the C3b time-of-day stability check. Microsoft's median
release time came out as **12:03 with a ±60 minute spread**, which is not what a scheduled corporate
process looks like. Apple's was 16:30:28 with ±0. The instrument built to flag anomalous *events*
flagged an anomalous *pipeline* instead.

**The fix.** The SGML header is used for **every** event — no special-casing of Microsoft, the
unreliable field is simply not used anywhere. `resolve_authoritative_times.py` records every
disagreement rather than quietly correcting it.

> **Rule for anyone extending this work: never take a timestamp from the submissions JSON.** Use
> `{accession}-index-headers.html`.

### ⚠️ The other weakness of this source

`acceptanceDateTime` is when **the SEC accepted the filing** — not when the press release crossed the
wire. For Apple the two coincide (16:30:2x–4x ET, eleven consecutive quarters). For other issuers the
8-K can lag the release. **This is the entire risk of Stage 1**, and it is why criteria C4 (human
TradingView check) and C5 (per-company systematic offset) exist.

---

## 3. Classification — read the documents, do not trust the metadata

Filtering on EDGAR's `items == "2.02"` field is **not sufficient**, and this is not hypothetical. Three
distinct metadata failures were found inside our own 20 companies:

**1. Applied Materials mis-tagged a whole quarter.** Its Q2-FY2024 earnings 8-K
(`0000006951-24-000017`, 2024-05-16 16:03:55 ET) is tagged **Item 2.01** — "Completion of Acquisition or
Disposition of Assets" — instead of 2.02. The filing plainly contains `exhibit991q22024earningsre.htm`
("Q2 2024 earnings release", 478 KB), and the timestamp sits exactly in AMAT's 16:03–16:05 quarterly
slot, filling a 182-day hole. Item-code filtering dropped it **silently**.

**2. Tesla files Item 2.02 for things that are not earnings.** Eleven earnings releases and eleven
**quarterly production/delivery reports**, all tagged 2.02. Both move the stock; only one is an earnings
release. Two Tesla filings three weeks apart:

```
delivery : "published the press release which is attached hereto as Exhibit 99.1"
           exhibit -> "Tesla Fourth Quarter 2025 Production, Deliveries & Deployments"
earnings : "released its FINANCIAL RESULTS for the fiscal quarter and year ended December 31, 2025"
```

**3. Foreign private issuers have no item codes at all.** ASML files Form 6-K, which carries none.

**The fix:** every 8-K and 6-K in span was harvested *regardless of item code*, and classification is
done by matching the text of the filing body and the EX-99.1 press release. Every row records the
**literal phrase that decided it** (`evidence`, `evidence_source`), so any row can be audited without
re-running anything.

A cross-check of document evidence against item codes across all 541 harvested filings found **exactly
one** 8-K mis-tag (AMAT) and confirmed 11 of ASML's 18 6-Ks as quarterly results.

---

## 4. Independent cross-check — and the limit we hit

| | |
|---|---|
| source | `https://api.nasdaq.com/api/calendar/earnings?date=YYYY-MM-DD` |
| gives | reporting **date**, EPS actual, surprise % |
| does **not** give | the time |

Criterion C3 in #110 asked for a second source agreeing to within 60 seconds. **That is not obtainable
at scale from free sources.** The direct evidence, Apple's 2026-07-30 report as Nasdaq itself publishes it:

```
{'symbol': 'AAPL', 'eps': '$1.91', 'surprise': '1.6', 'time': 'time-not-supplied'}
```

This is now **measured, not asserted.** Across the 18,786 vendor rows returned for our 145 announcement
dates:

| Nasdaq `time` value | rows | share |
|---|---:|---:|
| `time-not-supplied` | 18,657 | **99.3%** |
| `time-pre-market` | 68 | 0.4% |
| `time-after-hours` | 61 | 0.3% |

**99.3% carry no time at all, and the remaining 0.7% give only a session flag — never a minute.**
**EDGAR's acceptance timestamp is effectively the only free second-precision source that exists.**

### C3a result — independent DATE agreement

| | |
|---|---|
| exact date match | **200 / 201 (99.5%)** |
| no match | 1 — `WMT 2026-02-19 06:59:55` (`0000104169-26-000032`), recorded, not hidden |

That is genuine external corroboration that these 201 filings are the earnings announcements they are
claimed to be, on the days claimed. It says nothing about the minute — which is C4's job.

Reporting "C3 passed" on a check that could not be run would be worse than reporting the limit, so C3
was split into what is genuinely verifiable:

| | check | independent? | what it proves |
|---|---|---|---|
| **C3a** | Nasdaq calendar **date** agreement | ✅ yes — different organisation, different pipeline | the day, not the minute |
| **C3b** | per-company time-of-day stability | ❌ no — same source | a scheduled process has a stable clock time; genuine anomalies stand out |
| **C4** | owner's TradingView check | ✅ yes — human, price tape | **the only fully independent test of the minute** |

That is why C4 was made mandatory in #110 rather than optional.

---

## 5. Price frame — used for one thing only

`optimize/fundamentals/extended_data.load_1m_extended("NQ")` — the research-only 2024+2025+2026 stitch,
**841,983 one-minute bars, 2024-01-01 18:00 → 2026-05-19 19:59**, tz-naive US-Eastern wall-clock.

⚠️ This loader must never be used by the engine; lengthening the engine's history would change every
champion and break the golden tests. It is research-only by construction.

**Verified session coverage** (bars present per clock-minute across the whole frame):

| clock (ET) | bars | matters because |
|---|---:|---|
| 06:00 | 614 | ASML releases at ~06:0x — **covered** |
| 09:30 | 613 | RTH open |
| 16:00 | 591 | equity close |
| **16:30** | **591** | the main AMC earnings slot — **covered** |
| 17:00–17:59 | **0** | CME maintenance halt — the only dead window |

1,380 of 1,440 clock-minutes are present. **This is why the study uses NQ futures and not QQQ:** every
observed release time falls inside NQ trading hours, whereas QQQ regular-hours data would miss every
after-market earnings release entirely.

### 🚫 Anti-circularity (binding on all later stages)

The price frame is read **only** to flag whether a 1-minute bar exists at the event minute. **No
timestamp is ever adjusted toward an observed volatility spike.** Doing so would make the Stage 4
finding a tautology — "discovering" a spike exactly where we had defined it to be. The repo's standing
rule is *a finding equal to its own input is a tautology alarm*; this applies it in advance.

---

## 6. Reproducing the table

```bash
cd subprojects/Parametric-Indicators
python3 optimize/earnings/fetch_ndx_weights.py            # 1. freeze the universe (network)
python3 optimize/earnings/harvest_filing_documents.py     # 2. all 8-K/6-K + document lists (network, ~15 min)
python3 optimize/earnings/classify_earnings_events.py     # 3. classify from document TEXT (network, ~35 min)
python3 optimize/earnings/resolve_authoritative_times.py  # 4. ⚠️ SGML timestamps — see §2b (network, ~7 min)
python3 optimize/earnings/crosscheck_nasdaq_calendar.py   # 5. C3a independent date check (network)
python3 optimize/earnings/build_final_table.py            # 6. final table + TradingView worksheet (offline)
```

**Step 4 is not optional.** Skipping it leaves 10.9% of events (all of MSFT and LRCX) displaced by
4–5 hours into the wrong trading session, with no error and a perfectly plausible-looking timestamp.

Steps 2–5 cache to `data/`, so re-runs are cheap and resume after an interruption. Step 6 is fully
offline and deterministic — the classification rules can be revised and the table rebuilt without
touching the network.

⚠️ **A first-pass script `collect_earnings_timestamps.py` and its output `earnings_timestamps.csv` were
deliberately DELETED, not kept for reference.** They filtered on item codes (losing AMAT's quarter) and
used the JSON timestamp field (displacing MSFT and LRCX by 4–5 hours). A superseded script that still
runs and still produces a plausible-looking table is a trap, not history — the history is in git.
