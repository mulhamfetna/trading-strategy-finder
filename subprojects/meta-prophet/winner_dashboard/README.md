# Winning-Strategy Dashboard — main-dashboard reskin (`winner_dashboard/`)

An **interactive backtester styled to match the real main dashboard** (`../../../frontend/`):
the same TradingView dark theme, header + left **Settings** sidebar + **Run Backtest** button,
metric cards, chart, and trade ledger — but wired to the **WS-G winning-strategy clone engine**
(vol-gate + drawdown-breaker) instead of the master strategy. The main app and its backend are
**never touched**; this is a separate, self-contained reskin.

> Sibling of `../dashboard_winner/` (the plain standalone). Same engine + API; this one matches
> the production dashboard's look & layout. Both are kept.

## Run
```bash
python3 subprojects/meta-prophet/winner_dashboard/server.py --port 8137
# open http://localhost:8137/
```
Stdlib-only backend; loads 4h/1m/box + HAR-RV once (~1 s), each backtest ~1.5 s. Opened as a
plain file it shows the last saved run (`data.js`) read-only; the **Run Backtest** button needs
the server.

## Layout (mirrors the main dashboard)
- **Header:** title + "Run Backtest" button + a "Settings changed — Run Backtest to apply" hint.
- **Left Settings sidebar:** grouped controls — *Data* (window), *Entry/exit* (SL soft, SL hard,
  TP, direction), *Volatility gate* (percentile; 0 = off), *Drawdown circuit-breaker* (trigger $,
  cooldown; 0 = off) + a "Reset to winning preset" link.
- **Right column:** metric cards (P/L, max DD, win%, profit factor, trades/exposure, breaker
  locks) → price chart (candles + entry/exit markers + soft SL / hard SL / TP lines) → HAR-RV vol
  + gate threshold → engine TRADING/LOCKED state → equity → underwater drawdown (breaker + $5k cap
  lines) → **verbose event log** (entry/exit/LOCK/UNLOCK/SKIP with reasons) → **trade ledger**.

## Files
`server.py` (stdlib HTTP + `POST /api/backtest`) · `winner_backtest.py` (`build_payload` runs the
verified clone + drawdown-breaker overlay) · `index.html` (reskinned UI) · `data.js` (static
fallback / initial view). The proprietary candle/box-grid graphic is intentionally **not**
reproduced (project rule); the price chart shows candles + trade overlays only.

Engine = verified single-contract clone (`../engine_clone/`); breaker is a causal overlay (live
use needs an execution-layer equity-stop). P/L is in-sample / n=1 — see `../notes/44`.
