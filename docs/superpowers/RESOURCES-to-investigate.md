# RESOURCES — assessment of external data / signal sources (task #16, DONE)

**Assessed 2026-07-15 via a targeted research pass (105 agents, 24/25 claims verified). The user supplied 8
sites + 2 X threads; the question was strictly: does each provide FREE, PROGRAMMATICALLY-PULLABLE data with
POINT-IN-TIME / historical-intraday / release-timestamp value — or is it just a dashboard? Bottom line:
none of the 8 solves our scarce need, and the real point-in-time leads are OFF the list.**

> **⚠️ CORRECTION (2026-07-18).** An earlier version of this doc named **Barchart** as the candidate source
> for the long **GC** history that unfreezes the GC news/distribution work. **That framing was wrong and is
> retracted.** The server already has the Databento source that produced the 17 GB `NQ.csv` **and** a
> *generic* assembler (`/home/dev/Mulham/data_2010_1s/main_futures_seconds.py`) that builds 1-second
> continuous candles for **any** market. Long GC history is therefore a **download-from-Databento +
> assemble**, using tooling we already own — **not** a paid Barchart acquisition. Barchart remains a
> theoretically valid *alternative* intraday source, but it is not needed and is no longer the recommended
> path. (Verified: no GC 2010 file exists on the server or in the local zips; every non-NQ market starts
> 2025-01-01.)

---

## ⚡ THE 60-SECOND VERSION

| | |
|---|---|
| **The scarce thing (ALFRED-style point-in-time macro)** | **None of the 8 listed sites has it.** FRED/ALFRED remains our best free source, unchallenged. |
| **Long GC history (the real bottleneck)** | **Already solvable in-house** — pull GC 2010 raw from the same Databento source that produced `NQ.csv`, run the existing generic assembler. No purchase. *(corrected 2026-07-18; supersedes the Barchart lead below)* |
| **Barchart (listed site)** | Its OnDemand `getHistory` API gives historical **intraday minute/tick OHLCV for NQ *and GC*** + a historical macro calendar. **PAID, sales-gated.** A valid alternative, but **not needed** given the in-house Databento pipeline. |
| **The real point-in-time leads (OFF the user's list)** | **Trading Economics** (paid, documented PIT calendar — the ALFRED-equivalent) and **FXMacroData** (free-ish, unproven — validate against ALFRED). |

---

## Per-site verdicts

| Site | What it offers | Access | Verdict |
|---|---|---|---|
| **barchart.com** | Historical **intraday minute/tick/EOD OHLCV + open interest for NQ/GC**; `getCmdtyCalendar` = historical *revised/actual* US econ calendar | `getHistory` OnDemand API — **PAID, key-gated, no published free tier**; legacy free endpoint discontinued | ⚠️ **NOT NEEDED for GC history** *(corrected 2026-07-18 — the in-house Databento pipeline supplies it)*. Valid paid alternative only. Not ALFRED-vintage. Caveats: 1000-record cap; interval mode omits settlement price. |
| **koyfin.com** | Macro + market analytics dashboards | **No API** ("we're in the analytics business"); UI table/chart exports only | ❌ **UI-only, redundant with FRED.** Drop for a pipeline. |
| **finviz.com** | Screener/heatmap/news; **no** econ calendar / intraday / historical | Free = unofficial scraper (**ToS risk**); Elite (paid) = CSV/JSON export API but **equities-screener only** | ❌ **Not aligned** with NQ/GC-intraday + macro-vintage need. |
| **etfdb.com** | ETF screener snapshots + holdings weightings | Unofficial scraper only; **no price-history time series** | ❌ **Useless as QQQ/GLD proxy history** (no OHLCV). (API Ninjas ETF likewise.) |
| **companiesmarketcap.com** | Market-cap rankings | — | ❌ **Drop** (prior; irrelevant to NQ/GC futures/macro). *Not formally verified.* |
| **en.macromicro.me** | Macro charts/dashboards | — | ⚠️ **UNASSESSED** (no verified claims). Prior: likely UI-only / FRED-redundant. |
| **seekingalpha.com** | News/analysis/sentiment | — | ⚠️ **UNASSESSED.** Prior: article/paywall, no structured historical-sentiment API. |
| **stockanalysis.com** | Fundamentals/quotes | — | ⚠️ **UNASSESSED** (genuine open question — has a free API; intraday/macro relevance unknown). |

**The 2 X threads** (antpalkin, ruujss): not fetched (X is auth-walled for research agents). They appear to
concern **regime detection (HMM / Jump Model)** — which a *parallel agent is already working on another
branch* (`research-regime-hmm`, per the shared memory). **No action here** — do not duplicate that work;
treat the threads as that workstream's input, not this one's.

---

## Off-list leads for the POINT-IN-TIME need (the valuable surprise)

| Source | Point-in-time? | Access | Note |
|---|---|---|---|
| **Trading Economics** | ✅ **Documented PIT calendar** — events "exactly as they appeared on a specific date, before revisions" (`calendar/.../{initDate}/{endDate}`) | **Paid** Developer tier, no confirmed free tier; JSON/CSV | **The strongest lead for a true ALFRED-equivalent** with release timestamps. Vendor self-described (no independent vintage audit). |
| **FXMacroData** | ⚠️ Markets ALFRED-like `known_at` PIT store; **free USD macro** (no key, ~100 req/day, last 365 days), full history paid | Documented REST/Python/WebSocket/GraphQL | **Unproven** — validate against ALFRED before trusting; sub-second-timestamp claim was **refuted**. |
| **FMP** | ❌ release-timestamped calendar but **no vintage** | Free ~250 calls/day | Useful for *timing*, redundant-ish for *values* vs FRED; does **not** solve PIT. |

---

## Recommendation (and the link to the GC decision)

1. **Keep FRED/ALFRED as the point-in-time backbone.** Nothing on the list beats it for free; it's why the
   17-year NQ study was possible.
2. **The actionable item is the long-GC-history bottleneck.** Two of our workstreams are frozen or
   OOS-blocked purely for lack of long GC 1-minute data (the GC news/distribution studies; Z3's vol-targeting
   OOS). **The fix is in-house, not a purchase** *(corrected 2026-07-18)*: pull GC 2010 raw from the same
   Databento source that produced `NQ.csv` and run the existing generic assembler
   (`main_futures_seconds.py`) — identical treatment to how NQ got its 17-year 1-second frame. Barchart
   `getHistory` is only a fallback if that source is unavailable.
3. **If you later want a paid PIT macro calendar** (to replace our hand-built FRED-`release/dates` +
   hardcoded-times calendar with vendor timestamps), **Trading Economics** is the lead — but our current free
   calendar already validated itself (the 8.3× spike on the exact minute), so this is a nice-to-have, not a
   need.
4. **Drop:** koyfin, finviz, etfdb, companiesmarketcap for our purposes. **Optional follow-up:**
   stockanalysis.com (free API — worth a 10-minute check) and macromicro.me, if you specifically want them
   assessed; low priority.

**Net for the project:** the assessment doesn't hand us a free new data source, but it **names Barchart as a
paid path to the long GC history** — the single unlock for the largest block of remaining work — and
identifies Trading Economics as the paid ALFRED-equivalent if ever needed. The point-in-time discipline that
made this project rigorous (FRED/ALFRED) has no free peer among the sites listed.
