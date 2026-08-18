"""Standalone configuration for the WS-G drawdown-capped strategy subproject.

This subproject is SELF-CONTAINED in code (it copies the engine, box-lookup and loader in,
and computes realized volatility itself — it does NOT import from the wider repo's `src/` or the
meta-prophet scripts). The only external inputs are the market DATA files, which are large and
shared, so their location is configurable here (and via the WSG_DATA_ROOT env var).

For an outsider studying ONLY this strategy: everything you need is in this folder. See README.md
and docs/STRATEGY.md (what it does) and docs/ARCHITECTURE.md (how the code fits together).
"""
from __future__ import annotations

import os
from pathlib import Path

import roots                                 # the ONE resolver for repo/data roots (#94)

# --- DATA (external inputs; configurable) -------------------------------------------------
# Default points at the repo's data directory. Override with: export WSG_DATA_ROOT=/path/to/data
# NEVER a hardcoded absolute path (#94): the literal was one machine's layout, so on any other
# machine this resolved to a directory that does not exist and the failure looked like broken code.
DATA_ROOT = Path(os.environ.get("WSG_DATA_ROOT") or (roots.REPO_ROOT / "data"))

# Per-year files inside DATA_ROOT/<year>_data/ :
#   NQ_4h_<year>.csv        4-hour OHLCV candles      (datetime,open,high,low,close,volume)
#   NQ_1m_<year>.csv        1-minute OHLCV candles    (for sub-bar exits + realized vol)
#   NQ_full_data_<year>.csv unified weekly/monthly box levels (one row per market date)
YEARS = (2025, 2026)

NQ_POINT_VALUE = 20.0      # USD per index point per contract

# --- THE WINNING PRESET (tag v4.2-wsg-drawdown-capped-winner) ------------------------------
WINNER = dict(
    sl_soft=30.0,          # soft stop distance (pts) — 2 consecutive 1-min closes confirm
    sl_hard=40.0,          # hard stop distance (pts) — touch fill; caps loss ≈ $800
    tp=60.0,               # take-profit distance (pts) — touch fill; ≈ $1,200
    gate_pct=60.0,         # skip bars with HAR-RV forecast above this percentile (0 = gate off)
    dd_limit=2000.0,       # drawdown circuit-breaker trigger ($); 0 = breaker off  (re-tuned after the
                           # global-HWM breaker fix — see notes/46; OLD buggy default was 2500)
    cooldown=20,           # trades to stay locked after a breaker trip  (was 30)
    flip=False,            # entry direction: False = normal, True = flipped
    window="full",         # full | 2025 | 2026
)
DD_CAP = 5000.0            # hard max-drawdown goal (manual kill-switch level)

# NOTIONAL BACKTEST ACCOUNT (2026-07-29). Purely a REPORTING baseline: the engine trades exactly one
# contract and never consults an account balance, so this changes no decision, no trade and no P&L.
# It exists so a raw dollar figure can be read as a proportion of capital — e.g. the worst single CL
# trade (-$7,710) is 7.7% of a $100k account rather than a number that looks catastrophic in isolation.
#
# ⚠️ It is deliberately NOT added to the equity curve. `equity` is a column in the golden trade ledger
# (perf/golden/<tf>_trades.csv), so rebasing that series would change all six golden hashes and force a
# full re-capture. Percentages are derived at report time instead; the ledger stays byte-identical.
#
# In a real-money stage this is where a genuine account size and any per-trade cap would live.
ACCOUNT_SIZE = float(os.environ.get("WSH_ACCOUNT_SIZE", 100_000.0))

# Robust alternative (more cushion): sl 35/40, tp 40 -> +$21,100 @ $3,130 maxDD, 58% win.
ROBUST_ALT = dict(WINNER, sl_soft=35.0, sl_hard=40.0, tp=40.0)
