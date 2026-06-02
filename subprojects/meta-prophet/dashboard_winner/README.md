# Winning-Strategy Dashboard (`dashboard_winner/`) — interactive

An **interactive backtest dashboard** wired to the verified single-contract **clone** engine
(`../engine_clone/`). Edit the strategy parameters in the UI and press **Run backtest** to
re-run the full backtest live and redraw every panel. The main dashboard (`../dashboard/`) and
the live system are **never touched**.

## Run it (interactive — full backtests on demand)
```bash
python3 subprojects/meta-prophet/dashboard_winner/server.py        # default port 8137
# then open:
http://localhost:8137/
```
The server (Python stdlib only — no extra deps) loads the 4h/1m/box data + HAR-RV forecast once
(~1 s), then each backtest runs in ~1.5 s.

> Opened as a plain file (`file://…/index.html`) it still works **read-only**, showing the last
> saved run from `data.js`. The **Run** button needs the server.

## Editable parameters (control bar)
| Field | Meaning |
|---|---|
| Data window | `full` / `2025` / `2026` |
| SL soft / SL hard (pts) | stop-loss soft & hard distances (hard ≥ soft enforced) |
| TP (pts) | take-profit distance (soft = hard) |
| Vol gate pct | skip bars with HAR-RV above this percentile; **0 = gate off** |
| Breaker $ | drawdown circuit-breaker trigger; **0 = breaker off** |
| Cooldown (trades) | trades to stay locked after a breaker trip |
| Flip dir | `normal` / `flipped` entry direction |

**Winner preset** (↺ Reset to winner): SL 30/40 · TP 60 · gate 60 · breaker $2,500 / 30 →
+$24,720 P/L, $4,845 maxDD. (Verified live: winner params return exactly that; baseline
80/100/50 with gate+breaker off returns the known −$13,420 / $57,160.)

## What it shows (so the viewer knows what happened, when & why)
Header metrics (P/L, maxDD vs cap, win%, PF, exposure, breaker locks) · price + entry/exit
markers + **soft SL (amber) / hard SL (red) / TP (green)** lines · HAR-RV vol + gate threshold ·
engine **TRADING/LOCKED** state · equity · underwater drawdown (with breaker + $5k-cap lines) ·
a **verbose event log** (ENTRY/EXIT/LOCK/UNLOCK/SKIP with reasons) · a full **trade ledger**.

## Files
- `server.py` — stdlib HTTP server: serves the page + `POST /api/backtest`.
- `winner_backtest.py` — `build_payload(...)`: runs the clone + drawdown-breaker overlay → payload.
- `index.html` — the interactive UI (controls + charts + log + ledger).
- `data.js` — last static export (initial / file:// fallback); regenerate with
  `scripts/49_winning_dashboard_export.py`.

Engine = verified single-contract clone; the drawdown breaker is a **causal post-processing
overlay** (for live trading it must become an execution-layer equity-stop). P/L is **in-sample,
n=1** — see `../notes/44_winning_system_full_report.md`.
