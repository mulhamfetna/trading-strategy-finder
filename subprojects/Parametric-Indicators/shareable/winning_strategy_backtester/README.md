# Winning Strategy Backtester (standalone, shareable)

A self-contained backtester for the NQ **box + 1-minute-indicator** strategy. It bundles the **exact
parity-locked research engine**, so its results match the canonical system (the 4h champion reproduces at
**$142,203** — see `PLAYBOOK.md`). Zip this folder and share it; it has no dependency on the parent repo.

## Quick start
```bash
pip install -r requirements.txt        # numpy, pandas only

python3 backtest.py \
  --decision NQ_4h.csv \               # decision-frame candles  (Date,Open,High,Low,Close)
  --minute   NQ_1m.csv \               # 1-minute candles        (Date,Open,High,Low,Close)
  --box      NQ_full_data.csv \        # per-day box levels      (weekly/monthly level columns)
  --champion champions/4h.json \       # the tuned strategy (4h is the headline)
  --out      trades_4h.csv
```
Output: a printed summary (net P/L, max drawdown, win%, profit factor, …) and a per-trade CSV.

## Champions included
`champions/{4h,2h,1h,15m,5m,2m}.json` — each is a full machine-readable spec (box risk knobs + the 7–8
tuned indicators + the K-of-N confirm rule). Swap `--decision` to the matching timeframe's candles.

## CSV formats
- **decision / minute candles:** header `Date,Open,High,Low,Close` (tz-naive timestamps).
- **box:** `Date` + the weekly/monthly box-level columns (the `NQ_full_data.csv` format from research).

## Notes
- `--insample-year` (default 2025) sets which calendar year seeds the volatility-gate percentile.
- Indicators are computed on the **1-minute frame** (the "1-min-trained" regime) — this is intrinsic to
  the engine here and to how the champions were tuned.
- **Read `PLAYBOOK.md` §9 (caveats) before trading:** these are in-sample-optimised, single-period
  (n=1), single-contract, cost-free results — a research artifact, not a deployment-ready edge.

## What's inside
The real engine modules (`strategy.py`, `engine.py`, `box_lookup.py`, `volatility.py`, `loader.py`,
`config.py`, `indicators/`, `optimize/` helpers) + the thin CLI (`backtest.py`). See `PLAYBOOK.md` §10.
