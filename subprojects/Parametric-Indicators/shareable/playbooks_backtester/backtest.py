#!/usr/bin/env python3
"""Shareable backtester for the box + indicator champions (all 6 markets × 6 timeframes + the GC 4h
4-hour-indicator variant). Self-contained: it bundles the EXACT causal research engine the dashboard runs,
so a champion's numbers match the playbook to the dollar (this is NOT a re-implementation).

WHAT IT DOES
  Loads your candle + box CSVs for the champion's instrument, runs the causal L1 engine with the champion's
  tuned parameters (box risk knobs + the K-of-N indicator gate + the max-hold time cap + the drawdown
  breaker), and prints the summary + writes a per-trade CSV.

DATA YOU PROVIDE  (CSV, one header row; put them all in one folder — default ./data)
  <INST>_<tf>.csv   decision-frame candles   Date,Open,High,Low,Close      (e.g. GC_4h.csv)
  <INST>_1m.csv     1-minute candles         Date,Open,High,Low,Close      (shared exit + indicator frame)
  <INST>_box.csv    per-day box levels       Date,<weekly/monthly level columns>
  INST ∈ {NQ,ES,GC,SI,HG,CL,NG,RTY,YM}. Non-NQ box files are the −1-workday-shifted boxes (as onboarded).
  Dates are tz-naive 'YYYY-MM-DD HH:MM:SS'.

CHAMPION  (--champion champions/<INST>_<TF>.json) carries the instrument + timeframe + every tuned
parameter. See MANIFEST / README for the 37 champions and their headline numbers.

USAGE
  pip install -r requirements.txt                      # numpy, pandas
  python3 backtest.py --champion champions/GC_4h.json --data ./data --out trades.csv
  python3 backtest.py --champion champions/GC_4h_ind4h.json --data ./data      # the 4h-indicator variant

REQUIREMENTS: python3, numpy, pandas.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))


def main() -> int:
    ap = argparse.ArgumentParser(description="Shareable box + indicator causal backtester (matches the playbooks)")
    ap.add_argument("--champion", required=True, help="champion preset JSON (e.g. champions/GC_4h.json)")
    ap.add_argument("--data", default=str(_HERE / "data"),
                    help="folder holding <INST>_<tf>.csv / <INST>_1m.csv / <INST>_box.csv (default ./data)")
    ap.add_argument("--out", default="trades.csv", help="output per-trade CSV path")
    a = ap.parse_args()

    # point the portable loader at the data folder BEFORE importing the engine (read at import time)
    os.environ["WSH_BUNDLE_DATA"] = str(Path(a.data).resolve())

    champ = json.loads(Path(a.champion).read_text())
    preset = dict(champ["preset"]); preset["window"] = "full"
    tf = preset["timeframe"]
    inst = champ.get("instrument") or Path(a.champion).stem.split("_")[0]

    import pandas as pd
    from optimize.l2 import payload as L2

    print(f"loading {inst} data + running the causal L1 engine (timeframe {tf}) ...", flush=True)
    out = L2.build_view_payload(preset, {}, tf, "l1", instrument=inst, l1_engine=preset)
    b = out["meta"]["boxes"]            # on-screen dashboard figures (== the playbook headline)
    s = out["meta"]["summary"]          # engine accounting (avg win/loss, 2025/2026 split)
    trades = out.get("trades", [])

    # 2026 out-of-sample, on the SAME basis as the playbook: the 4h-indicator variant uses the full-run
    # 2026 attribution (its long warmup cripples a standalone-2026 run); every other champion uses a fresh
    # window=2026 run (the dashboard's "2026 (OOS)" view). The heavy L1 pass is memoised, so this is cheap.
    is_variant = preset.get("ind_1min") is False
    if is_variant:
        oos_pnl = s.get("pnl_2026")
    else:
        p26 = dict(preset); p26["window"] = "2026"
        oos_pnl = L2.build_view_payload(p26, {}, tf, "l1", instrument=inst, l1_engine=p26)["meta"]["boxes"]["pnl"]

    print("\n" + "=" * 70)
    print(f"  {champ.get('label', a.champion)}")
    print("=" * 70)
    print(f"  net P/L         : ${b['pnl']:,.0f}   (matches the playbook headline)")
    print(f"  max drawdown    : ${b['max_dd']:,.0f}   ({100*b['max_dd']/b['pnl']:.1f}% of P/L)"
          if b["pnl"] else f"  max drawdown    : ${b['max_dd']:,.0f}")
    print(f"  win rate        : {b['win']}%   profit factor: {b['pf']}   payoff: {b.get('payoff','—')}")
    print(f"  trades taken    : {b['n_taken']}  (of {b['n_candidates']} candidates, {b['exposure']}% exposure)")
    print(f"  avg win / loss  : ${s['avg_win']:,.0f} / ${s['avg_loss']:,.0f}")
    print(f"  2026 out-of-sample: ${oos_pnl:,.0f}   (matches the playbook OOS)")
    print(f"  breaker locks   : {b['n_locks']}")
    print("=" * 70)

    if trades:
        cols = ["entry_time", "exit_time", "direction", "entry_price", "exit_price", "exit_reason",
                "pnl", "equity", "dd"]
        rows = []
        for t in trades:
            r = dict(t)
            for c in ("entry_time", "exit_time"):
                if c in r:
                    try: r[c] = pd.Timestamp(r[c], unit="s")
                    except Exception: pass
            rows.append({c: r.get(c) for c in cols})
        pd.DataFrame(rows)[cols].to_csv(a.out, index=False)
        print(f"  wrote {len(trades)} trades -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
