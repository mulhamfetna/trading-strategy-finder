---
name: source-evaluation-consensus
description: "WS-NEWS2 (#114) — every consensus-data source probed, what each returned, and why the Nasdaq economic-events API was selected. Includes the two data conventions that must be corrected for, both verified against known releases."
type: reference
date: 2026-08-07
issue: 114
---

# Consensus data — source evaluation

**Requirement:** historical **actual · forecast(consensus) · previous** for US releases, back to ~2010,
reachable from this environment.

## Sources probed

| source | reachable | historical date range? | verdict |
|---|---|---|---|
| **investing.com** | ❌ 403 to `curl` (event page, AJAX `more-history`, and the homepage, even with a cookie jar — the block is TLS-fingerprint level). WebFetch renders. | WebFetch shows **today only**; date params ignored | ❌ unusable at depth |
| **ForexFactory** | ⚠️ 200 for **3 requests**, then **403 to everything including the homepage and WebFetch** | had per-month URLs back to 2010 — access lost | ❌ blocked after ~4 requests |
| **Trading Economics** (site) | ✅ 200 | ❌ date params **ignored** — ranged URL returns a byte-identical page (1,345,578 b) | ❌ |
| **Trading Economics** (API) | ❌ **410** — *"the guest account has been discontinued"* | — | ❌ paid |
| **FXStreet** calendar API | ❌ **401** | — | ❌ auth required |
| **Econoday** | ✅ 200 | ❌ date params ignored — returned the current week for a 2010 request | ❌ |
| **DailyFX** | ❌ 403 | — | ❌ |
| **✅ Nasdaq economic-events API** | ✅ **200, no rate limiting** | ✅ **per-day, back to 2007** | ✅ **SELECTED** |

## The selected source

```
https://api.nasdaq.com/api/calendar/economicevents?date=YYYY-MM-DD
```

Returns JSON: `gmt · country · eventName · actual · consensus · previous · description`.

⭐ **The event descriptions link to `investing.com/academy/...` — this API is investing.com's data.** It
is therefore the owner's preferred source, reached through an endpoint that is not blocked.

| property | verified value |
|---|---|
| rate limiting | **none observed** — 15/15 requests at 0.3 s intervals returned 200 (this pattern got us blocked from ForexFactory after 4) |
| depth | NFP present from **2007**; **consensus populated from 2009** (2007–2008 have actual + previous only) |
| coverage | all countries; filter `country == "United States"` |

## ⚠️ TWO CONVENTIONS THAT MUST BE CORRECTED FOR

Both verified against releases whose date and value are independently known. **Neither is documented by
the API.**

### 1. The date parameter is OFF BY ONE — request `D` returns the events of `D−1`

| requested | returned | independently known |
|---|---|---|
| `2010-01-09` | NFP **A=−85K, C=0K, P=4K** | Dec-2009 payrolls, released **Fri 8 Jan 2010**, actual **−85,000** ✓ |
| `2010-07-03` | NFP A=−125K | Jun-2010 payrolls, released **Fri 2 Jul 2010** ✓ |
| `2026-01-10` | NFP **A=50K, C=66K, P=56K** | released **Fri 9 Jan 2026** — matches the owner's investing.com paste `50.00K \| 66.00K \| 56.00K` ✓ |

### 2. ⚠️⚠️ The `gmt` field is FIXED AT UTC−4 YEAR-ROUND — it is one hour fast every winter

Verified on Nonfarm Payrolls, which is **08:30 US-Eastern year-round**:

| season | field shows | true ET | offset |
|---|---|---|---|
| **summer** (Jul 2010, 2012, 2013, 2017, 2018, 2019) | `08:30` | 08:30 | **0** — field equals ET |
| **winter** (Jan 2011, 2012, 2013, 2017, 2018, 2019) | `09:30` | 08:30 | **+1 h** |

**Correction rule:** interpret the field as **UTC−4**, then convert to `America/New_York`.

> Taking this field at face value would place **every winter event one hour late** — roughly half the
> sample. That is the same class of defect that displaced 22 earnings events by 4–5 hours in #110, and
> it is invisible without checking a release whose true time is known independently.

⚠️ **Pre-2009 is inconsistent**: 2007-01-05 and 2008-01-04 show `08:30` in *January*, breaking the rule
above. Outside our 2010→2026 price frame, so not corrected — but **do not extend this source before
2009 without re-deriving the convention.**

## Three-way agreement on a single release

| source | 2026-01-09 Nonfarm Payrolls |
|---|---|
| investing.com (owner's paste) | `50.00K \| 66.00K \| 56.00K` |
| ForexFactory (scraped before the block) | A=50K F=66K P=56K |
| Nasdaq API | A=50K C=66K P=56K |

One release is not a validation, but the three sources concur where they overlap.

## ⚠️ STILL UNVERIFIED — the revision question

Whether `actual` is the **first print** or a **later revision** is **not established for any source**.
If revised, using it is **look-ahead contamination** — the defect round 1 avoided by pulling ALFRED
point-in-time vintages. Payrolls alone were revised **−801k to −1,032k jobs** in 2025.

**No study may use this data until `actual` is cross-checked against ALFRED vintages on a sample.**
