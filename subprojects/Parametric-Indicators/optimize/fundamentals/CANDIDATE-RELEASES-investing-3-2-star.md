---
name: candidate-releases-investing-3-2-star
description: "Full US 3-star + 2-star release universe from investing.com (January 2026 sample, High+Medium filter), mapped against what the news study actually covered, with the reason for every gap."
type: reference
date: 2026-08-07
source: investing.com economic calendar, US, importance = High + Medium, January 2026
---

# Candidate release universe — investing.com High + Medium, US

**Source:** investing.com economic calendar, country = US, importance = **High + Medium**, January 2026,
supplied by the owner (curl gets 403; the page only ever renders "today", so a pasted month is the only
route to a full list).

⚠️ **The star icons do not survive a text paste** — the `Imp.` column is blank. Everything here is
therefore **3-star or 2-star**, but the split between them is not recoverable from this source. Where a
rating is stated below it was verified separately on that event's own investing.com page.

⚠️ **January 2026 is a partly atypical month.** The 2025/2026 appropriations lapses pushed several
releases off their normal slot — the sample shows October and November data being published in January,
some at 17:59/18:00 GMT+3 rather than the usual 16:30. Times marked ⚠️ below are catch-up releases and
should not be taken as that release's normal schedule.

**Times converted from the source display (GMT+3) to US Eastern: ET = listed − 8h (January = EST).**

---

## LEGEND

| mark | meaning |
|---|---|
| ✅ | **studied** — in `us_high_impact.csv`, 1,208 events, 2010→2026 |
| 🔵 | **already covered** — same physical print and same timestamp as a studied release |
| ❌ | **not studied** |

---

## 08:30 ET — the prime slot (the one the study is built around)

| release | studied | note |
|---|---|---|
| Nonfarm Payrolls | ✅ | n=197 |
| Unemployment Rate | 🔵 | same 08:30 Employment Situation print |
| Private Nonfarm Payrolls | 🔵 | same print |
| Average Hourly Earnings (MoM / YoY) | 🔵 | same print |
| Participation Rate | 🔵 | same print |
| U6 Unemployment Rate | 🔵 | same print |
| CPI (MoM / YoY) | ✅ | n=202 |
| Core CPI (MoM / YoY) | 🔵 | same CPI print |
| PPI (MoM) | ✅ | n=187 |
| Core PPI (MoM) | 🔵 | same PPI print |
| GDP (QoQ) | ✅ | n=200 |
| GDP Price Index (QoQ) | 🔵 | same GDP print |
| Core PCE Prices (QoQ) | 🔵 | same GDP print |
| Retail Sales (MoM) | ✅ | n=169 |
| Core Retail Sales (MoM) | 🔵 | same print |
| Retail Control (MoM) | 🔵 | same print |
| **Initial Jobless Claims** | ❌ | **weekly** — the highest-frequency 08:30 release that exists |
| **Continuing Jobless Claims** | ❌ | same 08:30 print as initial claims |
| **Durable Goods Orders (MoM)** | ❌ | |
| **Core Durable Goods Orders (MoM)** | ❌ | same print |
| **Trade Balance** | ❌ | |
| Exports / Imports | ❌ | same trade print |
| **Philadelphia Fed Manufacturing Index** | ❌ | |
| Philly Fed Employment | ❌ | same print |
| **NY Empire State Manufacturing Index** | ❌ | |
| **Housing Starts** / MoM | ❌ | |
| **Building Permits** | ❌ | same print |
| Nonfarm Productivity (QoQ) | ❌ | |
| Unit Labor Costs (QoQ) | ❌ | same print |
| Export / Import Price Index (MoM) | ❌ | |
| Current Account (QoQ) | ❌ | |

## 08:15 ET

| release | studied | note |
|---|---|---|
| **ADP Nonfarm Employment Change** | ❌ | private (ADP) — no free authoritative date source |
| ADP Employment Change **Weekly** | ❌ | private; new weekly series |

## 09:00 / 09:15 / 09:45 ET

| release | ET | studied | note |
|---|---|---|---|
| S&P/CS House Price Index Composite-20 | 09:00 | ❌ | |
| **Industrial Production** (MoM / YoY) | 09:15 | ❌ | |
| **S&P Global Manufacturing PMI** | 09:45 | ❌ | private (S&P Global) |
| **S&P Global Services PMI** | 09:45 | ❌ | private |
| S&P Global Composite PMI | 09:45 | ❌ | same print |
| **Chicago PMI** | 09:45 | ❌ | private |

## 10:00 ET — **the slot the study has ZERO coverage of**

| release | studied | note |
|---|---|---|
| **ISM Manufacturing PMI** | ❌ | **documented exclusion** — see below |
| ISM Manufacturing Prices / Employment | ❌ | same print |
| **ISM Non-Manufacturing (Services) PMI** | ❌ | **documented exclusion** |
| ISM Non-Manufacturing Prices / Employment | ❌ | same print |
| **JOLTS Job Openings** | ❌ | |
| **CB Consumer Confidence** | ❌ | private (Conference Board) |
| **Michigan Consumer Sentiment** | ❌ | private (Univ. of Michigan) |
| Michigan Consumer Expectations | ❌ | same print |
| Michigan 1-Year / 5-Year Inflation Expectations | ❌ | same print |
| **Existing Home Sales** / MoM | ❌ | |
| **New Home Sales** / MoM | ❌ | |
| Pending Home Sales (MoM) | ❌ | |
| Factory Orders (MoM) | ❌ | |
| Construction Spending (MoM) | ❌ | |
| Business Inventories (MoM) | ❌ | |
| Retail Inventories Ex Auto | ❌ | |
| US Leading Index (MoM) | ❌ | private (Conference Board) |
| PCE price index (MoM / YoY) | ✅ | n=190 ⚠️ normally 08:30; the Jan sample shows catch-up releases at 10:00 |
| Core PCE Price Index (MoM / YoY) | 🔵 | same PCE print |
| Personal Spending (MoM) | 🔵 | same PCE print |

## 10:30 ET — energy

| release | studied | note |
|---|---|---|
| **Crude Oil Inventories (EIA)** | ❌ | high impact for **CL**, not NQ. CL is onboarded but was never in the news study |
| Cushing Crude Oil Inventories | ❌ | same print |

## 11:00 ET

| release | studied | note |
|---|---|---|
| NY Fed 1-Year Consumer Inflation Expectations | ❌ | |

## 12:30 / 13:00 ET — Treasury auctions

| release | studied | note |
|---|---|---|
| 2 / 3 / 5 / 7-Year Note Auction | ❌ | |
| 10-Year Note Auction · 20-Year Bond · 30-Year Bond · 10-Year TIPS | ❌ | |

## 14:00 ET — Fed

| release | studied | note |
|---|---|---|
| **Fed Interest Rate Decision** | ✅ | n=63 |
| FOMC Statement | 🔵 | same instant as the decision |
| **FOMC Press Conference (14:30)** | ❌ | ⚠️ **a SEPARATE event 30 minutes later** — not covered by the 14:00 timestamp |
| **Beige Book** | ❌ | 14:00, eight times a year |
| Federal Budget Balance | ❌ | |

## 15:00 / 15:30 ET

| release | studied | note |
|---|---|---|
| Consumer Credit | ❌ | 15:00 |
| CFTC speculative net positions — S&P 500 · **Nasdaq 100** · Gold · Crude | ❌ | 15:30 Friday. **Positioning data, not a surprise release** |

## Unscheduled / speaker events

| event | studied | note |
|---|---|---|
| FOMC Member Speaks (Kashkari, Bowman, Bostic, Williams, Barr…) | ❌ | many per month, no forecast value to surprise against |
| U.S. President Speaks | ❌ | |
| Fed's Balance Sheet (weekly) | ❌ | |
| API Weekly Crude Oil Stock | ❌ | private (American Petroleum Institute) |
| Baker Hughes Rig Count | ❌ | private |
| OPEC Meeting · IEA Monthly Report | ❌ | |
| Atlanta Fed GDPNow | ❌ | **a nowcast, not a release** — updated continuously, no fixed surprise |

---

# WHY EACH GAP EXISTS

## 1. Documented exclusion — ISM (both PMIs)

From `fetch_calendar.py`, verbatim:

> FRED does **NOT** carry ISM. It is a private organization and its PMI data is proprietary, so the
> St. Louis Fed does not host the series. There is therefore **NO authoritative recorded-date source**
> for ISM in our free stack.
>
> We deliberately do **NOT** rule-derive the dates (1st / 3rd business day of the month). Rule-derived
> dates are exactly the class of unverified, assumed data this design exists to avoid — the whole reason
> we use FRED instead of a schedule is that **the 2025/2026 shutdowns proved schedules lie**.
>
> Consequence: the calendar contains **no 10:00 events**, so the veto never fires at 10:00.

**This is the single largest structural gap: the entire 10:00 ET slot is unstudied**, and it contains
ISM ×2, JOLTS, Consumer Confidence, Michigan Sentiment and both home-sales series.

## 2. Same reason as ISM — private source, no free authoritative date feed

ADP · S&P Global PMIs · Chicago PMI · CB Consumer Confidence · Michigan Sentiment · US Leading Index ·
API Crude Stock · Baker Hughes.

## 3. Obtainable on FRED, never included, **no documented reason**

**This is the genuinely unexamined ground.** Nothing in the code or reports explains their absence — it
looks like scope that was never revisited, not a decision:

- **Initial / Continuing Jobless Claims** (weekly, 08:30)
- **Durable Goods Orders** (08:30)
- **Trade Balance** (08:30)
- **Housing Starts / Building Permits** (08:30)
- **Philadelphia Fed** and **NY Empire State** manufacturing indexes (08:30)
- **Industrial Production** (09:15)
- **JOLTS** (10:00)
- Existing / New / Pending Home Sales · Factory Orders · Construction Spending (10:00)

## 4. Not a surprise release at all

Atlanta Fed GDPNow (continuous nowcast) · CFTC positioning (a report on positions, not a data surprise) ·
Fed's Balance Sheet · speaker events (no consensus forecast to surprise against).

## 5. Different instrument

EIA Crude Oil Inventories — the highest-impact scheduled event for **CL**, which is onboarded. Never
included because the news study was built on NQ and replicated on GC.

## 6. ⚠️ A real omission inside something we DID study

**The FOMC press conference (14:30 ET) is a separate event 30 minutes after the 14:00 decision.** Our
calendar records only the 14:00 timestamp. If the market's reaction to Fed communication is concentrated
in the press conference rather than the statement, our FOMC arm measured the wrong minute — the same
class of error as Intel's 7-minute filing lag in the earnings study.

---

# THE SHORTLIST WORTH STUDYING

Ranked by what is both obtainable and genuinely untested.

| rank | candidate | why | frequency |
|---|---|---|---|
| **1** | **Initial Jobless Claims** | 08:30, **weekly** ⇒ ~830 events over 16 years from a single release — more than the entire existing study. On FRED. No documented reason for exclusion. | weekly |
| **2** | **The 10:00 ET slot as a block** | The study has **zero** coverage of 10:00. ISM needs a paid feed, but **JOLTS, home sales, factory orders and construction spending are all on FRED**. | monthly |
| **3** | **FOMC press conference (14:30)** | Fixes a possible mis-timed measurement inside a release we already studied. Cheap. | 8×/yr |
| **4** | **Crude Oil Inventories → CL** | Tests whether the "priced in" verdict holds on a third instrument with a different driver. CL already onboarded. | weekly |
| **5** | ISM ×2 | Highest impact of all the gaps, but needs a **paid** date feed — rule-derived dates were deliberately rejected. | monthly |
