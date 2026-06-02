---
name: research-data-sources-and-models
description: Deep-research harvest (cited, adversarially verified) — ranked historical intraday futures/crypto DATA SOURCES for adding instruments beyond NQ, plus a practical advanced-MODELS shortlist (volatility / regime-flip / Kalman) with Python libraries. Feeds Workstream F (instruments) and A/D/E.
type: reference
---

# Research: data sources for more instruments + advanced model shortlist

Produced by the deep-research harness (6 search angles → 26 sources fetched → 124 claims →
**23 verified / 2 refuted** by 3-vote adversarial check). Data-source findings are
high-confidence (vendor primary pages). **Part 2 (models) was NOT in the verified claim set —
treat it as a practitioner shortlist to confirm, not evidence.** Pricing is 2025–2026 and
time-sensitive.

---

## Part 1 — Data sources (ranked for "I already export NinjaTrader datetime,OHLCV CSV")

| Rank | Source | Instruments / coverage | History depth | Finest res | CSV/OHLCV? | Cost | Paid? |
|---|---|---|---|---|---|---|---|
| 1 | **Kinetick / IQFeed** (feeds NinjaTrader directly) | equities, **futures (+opts), FX, indexes** | IQFeed 1-min: E-minis Sep-2005, US futures May-2007; **180 days tick** | **tick** | native to NT8 (your current workflow) | Kinetick EOD **free**; tick/min **paid** | mostly |
| 2 | **FirstRate Data** | index futures (NQ, ES, …), continuous + per-contract | NQ 1-min **back to 2008 (~18 yr)** | **1-min** (no futures tick) | clean CSV, 1m/5m/30m/1h/1d | cheap one-off | **paid** |
| 3 | **PortaraCQG** | **hundreds** of contracts: CME/GLOBEX, CBOT, NYMEX, COMEX, ICE, EUREX, TSE — ES/CL/GC/6E/ZN | **1-min to 1987**, daily to 1899 | **tick** (trades + L1) + sub-min bars | CSV/ASCII | not quantified | **paid** |
| 4 | **Databento** (GLBX.MDP3) | **all** CME/CBOT/NYMEX/COMEX futures+opts (+ICE/Eurex) | (CME Globex MDP3) | **nanosecond tick / MBO L3** | CSV/JSON/DBN + OHLCV schema | usage **~$0.50/GB**, **$125 free credits** | paid (free credits) |
| 5 | **Polygon.io / "Massive"** | CME group (ES/YM/RTY/NQ/CL/GC/6E/ZN) | **only from May-2017** ⚠️ | nanosecond tick + 1-min OHLCV | API (ns Unix ints → convert) | paid plan | **paid** |
| 6 | **Tardis.dev** (crypto/BTC) | 50–60+ exchanges, 200k+ instruments | **7+ yr** | tick L2/L3 | API/flat files | **$300 min**; academic ~$350–650/mo | **paid** |

**Other options noted:** Interactive Brokers TWS API (has historical-bar *limitations*),
Dukascopy (FX/CFD historical), Norgate Data (futures packages, continuous-contract focus),
and for crypto the free **Binance public data** (github.com/binance/binance-public-data),
crypto-lake, CoinAPI, Kaiko.

### Recommendation for this project
- **Easiest drop-in:** **Kinetick/IQFeed** — they feed NinjaTrader directly, so adding ES,
  YM, RTY, CL, GC, 6E, ZN means exporting them the *exact same way* you already export NQ
  (zero format work). Use **IQFeed** if you want tick + 2005–2007 1-min depth.
- **Cheapest clean deep history (no tick needed):** **FirstRate Data** — research-licensed
  CSVs, ~18 yr of 1-min index futures. Great for backtesting/validation across instruments.
- **Deepest/broadest or microstructure:** **PortaraCQG** (multi-decade, widest set) or
  **Databento** (programmatic nanosecond tick, $125 free credits to start).
- **Crypto/BTC:** **Tardis.dev** (paid) or **free Binance public data** to start.

### Verified caveats / corrections
- Two claims were **refuted** by the adversarial check — do not rely on them: (a) "IQFeed
  futures daily history goes back to 1959 / no crypto" (1-2), (b) "FirstRate is CSV-only with
  no API" (0-3, so FirstRate *may* offer an API). 
- Continuous-contract stitching (roll method) is a known data-quality pitfall — verify how
  any vendor builds continuous series before backtesting.
- **Boxes:** no source provides our weekly/monthly support/resistance "box" levels — those
  stay **derived in-house** from OHLCV (open question confirmed).

---

## Part 2 — Advanced model shortlist (practitioner framing — confirm before trusting)

> Flagged **low confidence**: not covered by the verified claims. Use as a starting list.

- **(a) HF volatility (beyond plain GARCH):** **HAR-RV** and variants, **realized-GARCH**,
  **HEAVY** — they exploit realized-variance regressors and tend to beat plain
  GARCH/GJR/EGARCH/FIGARCH on high-frequency futures. Python: **`arch`** (+ `statsmodels` for
  HAR regressions). → Workstream A.
- **(b) Regime / strategy-flip detection (robust with little data):** **CUSUM**,
  **Page-Hinkley**, **Bayesian Online Change-Point Detection (BOCPD)**, **ADWIN**, **PELT**.
  Python: **`ruptures`** (PELT/Binseg/Window), **`river`** (ADWIN, Page-Hinkley),
  **`bayesian_changepoint_detection`** (BOCPD). → Workstream D.
- **(c) Kalman family (denoising / state estimation):** linear **KF**, **UKF**, **particle
  filter**, **adaptive KF**. Python: **`filterpy`** (KF/UKF/particle), **`pykalman`** (KF/EM).
  → Workstream E.

---

## Open questions this raises (for you)
1. **Which instruments first?** Correlated index futures (ES/YM/RTY) are best for
   cross-instrument vol (DCC-GARCH); diverse assets (CL/GC/6E/BTC) give more regime variety
   to validate the flip models. Pick a starter basket.
2. **Tick or 1-min?** Our pipeline is 1-min-and-up; tick only matters if we go to
   microstructure. For now 1-min (FirstRate/IQFeed) is enough.
3. **Budget?** Everything except Kinetick-EOD-free and Binance-crypto-free is paid. If you
   want, I can do a focused cost-out for a specific basket + vendor.

---

## One-paragraph summary (baby)
To add more instruments the **lowest-effort path is Kinetick/IQFeed**, because they plug
straight into the NinjaTrader you already use — you'd export ES, CL, GC, etc. exactly like NQ.
For cheap, clean, deep history without tick data, **FirstRate Data**; for the deepest/broadest
or for nanosecond tick, **PortaraCQG** or **Databento** (which gives $125 free credits to try);
for **crypto/BTC**, **Tardis** (paid) or **Binance's free public data**. Almost everything else
costs money. None of them give us the "box" levels — we keep computing those ourselves. On the
modeling side, the libraries to reach for are **`arch`** (volatility: HAR-RV/realized-GARCH/
HEAVY), **`ruptures`/`river`** (regime/flip: PELT/BOCPD/ADWIN/Page-Hinkley), and
**`filterpy`/`pykalman`** (Kalman/UKF/particle) — a shortlist to confirm as we build
Workstreams A, D, and E.
