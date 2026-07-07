#!/usr/bin/env python3
"""Standalone MULTI-TIMEFRAME layer-fusion backtester — primary tf + secondary tf, one instrument.

Self-contained: bundles the EXACT parity-locked research engine (the causal log-first stack under
optimize/l2/ + the fusion core optimize/l2/mtf.py), so results match the canonical system byte-for-byte —
this is NOT a re-implementation.

WHAT IT DOES
  Trades two timeframes of ONE instrument at once, each with its OWN profile:
    • PRIMARY  (e.g. 1h) runs its full box+indicator strategy and has priority.
    • SECONDARY (e.g. 4h) runs its full strategy too, but may ENTER ONLY WHILE THE PRIMARY IS FLAT
      (it fills the primary's idle windows). A primary entry strictly inside a secondary trade
      FORCE-CLOSES the secondary at that bar (reason "L1-entry"); P/L is recomputed honestly.
  ONE shared account, 1 contract — the two layers compete for the single position, so the combined
  result is NOT the sum of the two standalone P/Ls.

  Implementation: run each layer as a standalone L1 pass (optimize.l2.payload.run_l1_cached on its own
  timeframe), then fuse on the MASTER GRID (the finer timeframe) with primary-priority + force-close
  (optimize.l2.mtf.run_dual_tf), driven by optimize.l2.logbook.run_causal(..., l2_mode="independent").

CANONICAL RESULTS (full research period, 1 contract)
  ES : primary 1h + secondary 4h  →  combined $71,800  (264 trades; L1 $52,185 + L2 $19,615)
  NQ : primary 1h + secondary 4h  →  combined $173,789 (481 trades; L1 $99,172 + L2 $74,617)
  (Each layer is profitable alone; fusion beats the best single layer but is far below the naive sum,
   because the single shared position lets the primary preempt / crowd out the secondary.)

CONSTRAINT
  The PRIMARY timeframe must be finer-or-equal to the secondary (make your higher-frequency layer the
  primary). The master grid is the finer of the two.

DATA YOU PROVIDE (the bundle ships code + champions, NOT the multi-year candle CSVs)
  NQ: reads from the original research layout; point the loader at your tree:
      export WSH_DATA_BASE=/path/to/trading        # <RAW_DIR>/NQ_<tf>.csv + NQ_1m.csv
      export WSG_DATA_ROOT=/path/to/trading/data   # full_data/NQ_full_data.csv (per-day box levels)
  ES: resolved through the all-stocks registry under WSH_DATA_BASE
      (subprojects/all-stocks-signals/instruments.py + its ALL_STOCKS candle/box data).

USAGE
  python3 backtest_mtf.py                                   # ES, 1h primary + 4h secondary  → $71,800
  python3 backtest_mtf.py --instrument NQ                   # NQ                              → $173,789
  python3 backtest_mtf.py --instrument ES --primary-tf 1h --secondary-tf 4h --out-prefix run
  # writes <prefix>_mtf_log.csv (the full per-candle log — the single source of truth)

REQUIREMENTS: python3, numpy, pandas  (pip install -r requirements.txt)
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from optimize.l2 import logbook, aggregate, payload   # noqa: E402
from optimize import instruments as _inst             # noqa: E402
from optimize import timeframes as TF                 # noqa: E402

_TFS = ("4h", "2h", "1h", "15m", "5m", "2m")


def _summary(log, owner):
    rows = [r for r in log if r.decision == "entry" and (owner is None or r.position_owner == owner)]
    pnl = sum(r.pnl for r in rows)
    wins = sum(1 for r in rows if r.pnl > 0)
    gross_w = sum(r.pnl for r in rows if r.pnl > 0)
    gross_l = -sum(r.pnl for r in rows if r.pnl < 0)
    pf = (gross_w / gross_l) if gross_l else float("inf")
    win = (100.0 * wins / len(rows)) if rows else 0.0
    return pnl, len(rows), win, pf


def _write_log_csv(res, path):
    header, rows = aggregate.log_to_csv(res.log)
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(header); w.writerows(rows)
    return len(rows)


def main():
    ap = argparse.ArgumentParser(description="Multi-timeframe layer fusion (primary + secondary, one instrument)")
    ap.add_argument("--instrument", default="ES", choices=list(_inst.TOKENS))
    ap.add_argument("--primary-tf", default="1h", choices=_TFS, help="primary (priority) timeframe — finer-or-equal")
    ap.add_argument("--secondary-tf", default="4h", choices=_TFS, help="secondary (gap-fill) timeframe — coarser-or-equal")
    ap.add_argument("--out-prefix", default="mtf")
    a = ap.parse_args()

    if TF.get(a.primary_tf).bar_td > TF.get(a.secondary_tf).bar_td:
        ap.error(f"primary ({a.primary_tf}) must be finer-or-equal to secondary ({a.secondary_tf}); "
                 f"make the higher-frequency timeframe the primary")

    inst = a.instrument
    l1 = payload.instrument_l1_default(inst, a.primary_tf)     # primary champion (this tf)
    l2 = payload.instrument_l1_default(inst, a.secondary_tf)   # secondary champion (its own tf)
    pv = _inst.point_value(inst)

    res = logbook.run_causal(l1, l2, tf=a.primary_tf, instrument=inst,
                             l2_mode="independent", l2_tf=a.secondary_tf)

    c_pnl, c_n, c_win, c_pf = _summary(res.log, None)
    a_pnl, a_n, a_win, a_pf = _summary(res.log, "L1")
    b_pnl, b_n, b_win, b_pf = _summary(res.log, "L2")
    print(f"\nMulti-timeframe fusion — {inst}  (primary {a.primary_tf} + secondary {a.secondary_tf}, "
          f"${pv:.0f}/pt, 1 contract)")
    print(f"  {'layer':<26}{'P/L':>12}{'trades':>9}{'win%':>8}{'PF':>8}")
    print(f"  {'PRIMARY  ('+a.primary_tf+', priority)':<26}{a_pnl:>12,.0f}{a_n:>9}{a_win:>7.1f}%{a_pf:>8.2f}")
    print(f"  {'SECONDARY('+a.secondary_tf+', gap-fill)':<26}{b_pnl:>12,.0f}{b_n:>9}{b_win:>7.1f}%{b_pf:>8.2f}")
    print(f"  {'COMBINED (one account)':<26}{c_pnl:>12,.0f}{c_n:>9}{c_win:>7.1f}%{c_pf:>8.2f}")

    out = Path(f"{a.out_prefix}_mtf_log.csv")
    n = _write_log_csv(res, out)
    print(f"\n  per-candle log ({n} rows, master grid = {a.primary_tf}) → {out}")


if __name__ == "__main__":
    main()
