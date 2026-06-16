#!/usr/bin/env python3
"""Standalone backtester for the NQ box + 1-minute-indicator strategy (the WS-I "1-min-trained"
champions). Self-contained: it bundles the EXACT parity-locked engine used in research, so results
match the canonical system — this is not a re-implementation.

It loads your candle/box CSVs, computes the HAR-RV volatility forecast, runs the engine with a
champion's tuned parameters, applies the drawdown circuit-breaker, and prints the summary + writes a
per-trade CSV.

DATA YOU PROVIDE (CSV, one header row)
  --decision   decision-frame candles: Date,Open,High,Low,Close   (e.g. 4h bars)
  --minute     1-minute candles:        Date,Open,High,Low,Close   (shared exit + indicator frame)
  --box        per-day box levels:      Date,<weekly/monthly level columns>  (NQ_full_data.csv format)
  Dates are parsed by pandas; use a tz-naive 'YYYY-MM-DD HH:MM:SS' style.

CHAMPION (--champion champions/<tf>.json) carries the timeframe + every tuned parameter (box risk
knobs + the 8/7 enabled indicators + their internals + the K-of-N confirm rule). 4h is the headline
($142k full-period / 9.9% DD / 71% win in research). Pick the file matching your --decision timeframe.

USAGE
  python3 backtest.py --decision NQ_4h.csv --minute NQ_1m.csv --box NQ_full_data.csv \
                      --champion champions/4h.json --out trades_4h.csv

REQUIREMENTS: python3, numpy, pandas  (pip install -r requirements.txt)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

import strategy                      # the real engine wiring (build_payload)  # noqa: E402
from loader import load_data         # noqa: E402
from volatility import vol_forecast  # noqa: E402
from optimize import timeframes as TF  # noqa: E402


def _load_box(path: str) -> pd.DataFrame:
    """Per-day box levels → Date-indexed frame (midnight-normalised, de-duped), exactly as the
    research loader builds it."""
    box = pd.read_csv(path)
    box["Date"] = pd.to_datetime(box["Date"]).dt.normalize()
    return box.drop_duplicates(subset=["Date"]).set_index("Date", drop=False)


def main() -> int:
    ap = argparse.ArgumentParser(description="Standalone NQ box + 1-min-indicator backtester")
    ap.add_argument("--decision", required=True, help="decision-frame candle CSV (Date,O,H,L,C)")
    ap.add_argument("--minute", required=True, help="1-minute candle CSV (Date,O,H,L,C)")
    ap.add_argument("--box", required=True, help="per-day box-levels CSV (NQ_full_data.csv format)")
    ap.add_argument("--champion", default=str(_HERE / "champions" / "4h.json"),
                    help="champion preset JSON (default: champions/4h.json)")
    ap.add_argument("--insample-year", type=int, default=2025,
                    help="calendar year whose bars seed the volatility-gate percentile (default 2025); "
                         "set to the first/in-sample year of your data")
    ap.add_argument("--out", default="trades.csv", help="output per-trade CSV path")
    a = ap.parse_args()

    champ = json.loads(Path(a.champion).read_text())
    preset = dict(champ["preset"]); preset["window"] = "full"     # full-history run
    tf = preset["timeframe"]
    bar_min = int(TF.get(tf).bar_td.total_seconds() // 60)

    print(f"loading data + computing HAR-RV (timeframe {tf}, bar {bar_min}m) ...", flush=True)
    df4 = load_data(a.decision)
    df1 = load_data(a.minute)
    box = _load_box(a.box)
    vf = vol_forecast(df4, df1, bar_minutes=bar_min)

    # in-sample length for the vol-gate percentile (research used the count of first-year bars).
    n_ins = int((df4["Date"].dt.year == a.insample_year).sum()) or len(df4)

    payload = strategy.build_payload(df4, df1, box, vf, n_ins, preset)
    s = payload["meta"]["summary"]
    trades = payload["trades"]

    print("\n" + "=" * 64)
    print(f"  {champ.get('label', a.champion)}")
    print("=" * 64)
    print(f"  net P/L         : ${s['pnl']:,.0f}")
    print(f"  max drawdown    : ${s['max_dd']:,.0f}   ({100*s['max_dd']/s['pnl']:.1f}% of P/L)"
          if s["pnl"] else f"  max drawdown    : ${s['max_dd']:,.0f}")
    print(f"  trades taken    : {s['n_taken']}  (of {s['n_candidates']} candidates, "
          f"{s['exposure']}% exposure)")
    print(f"  win rate        : {s['win']}%   profit factor: {s['pf']}")
    print(f"  avg win / loss  : ${s['avg_win']:,.0f} / ${s['avg_loss']:,.0f}")
    print(f"  breaker locks   : {s['n_locks']}   skipped-by-breaker: {s['n_skipped_breaker']}")
    print(f"  longest no-entry: {s['noentry_streak_n']} signals / "
          f"{s['noentry_streak_days']}d (from {s['noentry_streak_start']})")
    print("=" * 64)

    if trades:
        cols = ["entry_time", "exit_time", "direction", "entry_price", "exit_price",
                "exit_reason", "pnl", "equity", "dd", "veto_flip"]
        rows = []
        for t in trades:
            r = dict(t)
            r["entry_time"] = pd.Timestamp(r["entry_time"], unit="s")
            r["exit_time"] = pd.Timestamp(r["exit_time"], unit="s")
            rows.append({c: r.get(c) for c in cols})
        pd.DataFrame(rows)[cols].to_csv(a.out, index=False)
        print(f"  wrote {len(trades)} trades -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
