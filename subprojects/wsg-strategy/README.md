# WS-G Drawdown-Capped Strategy — standalone app

A **self-contained** full-stack app for one trading strategy: the WS-G drawdown-capped NQ
strategy (git tag `v4.2-wsg-drawdown-capped-winner`). Backend + frontend + engine + docs all
live in **this folder** — you do **not** need the rest of the repo to read, run, or understand it.
(The only external inputs are the large market-data CSVs, whose location is configurable; see
[Data](#data).)

> **For an outsider studying only this strategy:** read `docs/STRATEGY.md` (what it does and why)
> then `docs/ARCHITECTURE.md` (how the code fits together). This README is the 5-minute version.

> **WS-H multi-timeframe engine (pinned):** the multi-timeframe parameter search built on top of
> this strategy is the engine
> **`WSH-HAR_RV-Drowdown_Breaker-Cooldown_Couner-Vectorized_NASGII`** — pinned at branch
> `wsh-engine` / tag of the same name. See `optimize/reports/WS-H_RESULTS.md` §0 for the
> component decoding and results.

---

## What the strategy is (30 seconds)
On **NQ 4-hour** candles, take the box Stage-1 buy/sell signal **only when volatility is calm**
(HAR-RV forecast in the lower 60%), with a **tight stop** (hard 40 pts ≈ $800 max loss) and a
bigger **take-profit** (60 pts ≈ $1,200), and a **drawdown circuit-breaker** that halts trading
after a $2,500 bleed. One contract. The point is **small, capped drawdown** (≤ $5,000) while
staying profitable.

**Backtest (2025–2026 NQ, in-sample / n=1):** +$24,720 P/L · max drawdown $4,845 · both years
positive · win 48.3% · profit factor 1.55. **⚠ tuned on one regime — not yet validated
out-of-sample. Do not trade live without the steps in `docs/STRATEGY.md` §"Going live".**

---

## Run it
```bash
python3 subprojects/wsg-strategy/server.py            # default http://localhost:8200/
# (Python stdlib only — no pip installs. ~3 s to load data, ~1.5 s per backtest.)
```
Open the URL, edit parameters in the left **Settings** panel, press **Run Backtest** — it runs the
full backtest live and redraws the charts, the verbose event log, and the trade ledger.

If you only want to *look* (no live runs), open `frontend/index.html` directly — it shows the last
saved run from `frontend/data.js` read-only.

## Data
Set where the market CSVs live (defaults to the repo's `data/`):
```bash
export WSG_DATA_ROOT=/path/to/data     # expects <year>_data/NQ_{4h,1m,full_data}_<year>.csv
```
See `config.py`. Realized volatility is **computed here** from the 1-min data (nothing precomputed
is imported) — verified to reproduce the winner exactly.

## Layout (everything is local)
```
wsg-strategy/
├── README.md            ← you are here
├── config.py            data paths + the winning preset + constants
├── loader.py            CSV loader (copied; pure pandas)
├── box_lookup.py        box level constants + candle→box-date mapping (copied; self-contained)
├── engine.py            the verified single-contract backtest engine (copied clone)
├── volatility.py        realized-vol (from 1-min) + causal HAR forecast
├── strategy.py          load data · gate · run engine · drawdown breaker · build payload
├── server.py            stdlib HTTP backend: serves frontend + POST /api/backtest
├── frontend/
│   ├── index.html       interactive dashboard (TradingView-style)
│   └── data.js          last saved run (static fallback)
└── docs/
    ├── STRATEGY.md      verbose: the rules, the why, results, going-live (for outsiders)
    └── ARCHITECTURE.md  verbose: how the code/system works, module by module
```

## Provenance & honesty
- Engine = a **parity-tested clone** of the repo's verified single-contract engine; it adds only a
  per-bar SL/TP multiplier + an entry gate. The original production engine is untouched.
- The drawdown breaker is a **causal post-processing overlay**; for live trading it must become an
  execution-layer equity-stop.
- Results are **in-sample, single regime (n=1)** — illustrative of the mechanism, not a promise.
- This app is a self-contained extraction; the research history that produced it lives in
  `../meta-prophet/notes/` (kept in place) — see `docs/STRATEGY.md` for the trail.
