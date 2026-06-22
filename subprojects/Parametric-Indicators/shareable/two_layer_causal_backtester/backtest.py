#!/usr/bin/env python3
"""Standalone TWO-LAYER causal backtester — Layer 1 + Layer 2 + combined (the NQ box system).

Self-contained: it bundles the EXACT parity-locked research engine (the causal log-first two-layer
stack under optimize/l2/), so results match the canonical system — this is NOT a re-implementation.

WHAT IT DOES
  Runs ONE causal pass (optimize.l2.logbook.run_causal) that projects the oracle —
  Layer 1 (run_l1) + Layer 2 (run_l2, with L1-priority and L2 force-close on an L1 entry) —
  into ONE per-candle log (the single source of truth). Every box/metric below is derived FROM
  that log (optimize.l2.aggregate). It then prints the L1, L2 and combined summaries and writes
  the full per-candle log to CSV.

THE TWO LAYERS
  L1 = the frozen lean 4h champion (box + 1-minute-indicator strategy).  ~ $149,989 / 255 trades.
  L2 = manages the signals L1 DROPS (veto + vol-gate) while L1 is flat; an L1 entry force-closes L2.
       ~ $78,391 / 80 trades.  Combined ~ $228,380.

DATA YOU PROVIDE (the bundle ships code + champions, NOT the multi-year candle CSVs)
  The bundled loader (optimize/data.py) reads NQ data from a base directory. Point it at your data:
     export WSH_DATA_BASE=/path/to/trading          # tree with Full_Canldes_Data/<RAW_DIR>/NQ_<tf>.csv + NQ_1m.csv
     export WSG_DATA_ROOT=/path/to/trading/data     # holds full_data/NQ_full_data.csv (per-day box levels)
  (Defaults target the original research layout under /mnt/data/projects/trading.)

CHAMPIONS (bundled in champions/)
  --l1-champion  the frozen lean L1 (default champions/wsh_lean_4h_champion.json — also auto-loaded
                 from optimize/results/ by the frozen-oracle path).
  --l2-champion  the L2 extend champion (default champions/l2v2_4h_champion.json).

USAGE
  python3 backtest.py --view all --tf 4h
  python3 backtest.py --view combined --out-prefix run
  # writes <prefix>_<view>_log.csv  (per-candle, single source of truth)

REQUIREMENTS: python3, numpy, pandas  (pip install -r requirements.txt)
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from optimize.l2 import logbook, aggregate, payload   # noqa: E402
from optimize import timeframes as TF                 # noqa: E402


def _fmt_money(x) -> str:
    try:
        return f"${x:,.0f}"
    except (TypeError, ValueError):
        return str(x)


def _print_layer(title: str, b: dict) -> None:
    """Print an L1- or L2-style box dict (flat values from aggregate.boxes_for_layer)."""
    print(f"\n=== {title} ===")
    print(f"  P/L              {_fmt_money(b['pnl'])}")
    print(f"  max drawdown     {_fmt_money(b['max_dd'])}")
    print(f"  win rate         {b['win']}%")
    print(f"  profit factor    {b['pf'] if b['pf'] is not None else '—'}")
    print(f"  trades           {b['n_taken']} / {b['n_candidates']} candidates ({b['exposure']}%)")
    print(f"  breaker locks    {b['n_locks']}")
    print(f"  warmup           {b['warmup']['bars']} candles")
    print(f"  indicator req    {b['indicator_req']['bars']} candles")


def _print_combined(b: dict) -> None:
    """Print the combined box dict (each value is {'value':..., 'layer':...} under the combine rules)."""
    V = lambda k: b[k]["value"]
    L = lambda k: b[k].get("layer", "")
    print("\n=== COMBINED (L1 + L2) ===")
    print(f"  P/L              {_fmt_money(V('pnl'))}        [Σ sum]")
    print(f"  max drawdown     {_fmt_money(V('max_dd'))}        [recomputed, merged book]")
    print(f"  win rate         {V('win')}%        [recomputed]")
    print(f"  profit factor    {V('pf') if V('pf') is not None else '—'}        [recomputed]")
    print(f"  trades           {V('n_taken')} / {V('n_candidates')} ({V('exposure')}%)        [Σ sum]")
    print(f"  breaker locks    {V('n_locks')}        [Σ sum]")
    print(f"  warmup           {V('warmup')['bars']} candles   (from {L('warmup')})   [max(L1,L2)]")
    print(f"  uplift vs L1     {_fmt_money(V('uplift'))}        [L2's contribution]")
    print(f"  L1-only DD       {_fmt_money(V('l1_only_dd'))}")
    print(f"  DD not worse?    {'OK' if V('dd_not_worse') else '+DD vs L1-alone'}")


def _write_log_csv(res, path: Path) -> int:
    header, rows = aggregate.log_to_csv(res.log)
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
    return len(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description="Two-layer (L1+L2+combined) causal backtester")
    ap.add_argument("--view", choices=["l1", "l2", "combined", "all"], default="all")
    ap.add_argument("--tf", default="4h", help="decision timeframe (default 4h)")
    ap.add_argument("--l1-champion", default=str(_HERE / "champions" / "wsh_lean_4h_champion.json"),
                    help="frozen lean L1 champion JSON (default champions/wsh_lean_4h_champion.json)")
    ap.add_argument("--l2-champion", default=str(_HERE / "champions" / "l2v2_4h_champion.json"),
                    help="L2 extend champion JSON (default champions/l2v2_4h_champion.json)")
    ap.add_argument("--out-prefix", default="out", help="prefix for the per-candle log CSV (default out)")
    args = ap.parse_args()

    # L1 = the frozen lean champion. run_causal hits the cached oracle when l1_params == the lean default,
    # so we pass exactly that (the bundled wsh_lean_4h_champion.json drives l1_default_params under the hood).
    l1_params = payload.l1_default_params(args.tf)

    # L2 = the extend champion's tuned parameter block.
    l2_doc = json.loads(Path(args.l2_champion).read_text())
    l2_params = l2_doc.get("params", l2_doc)

    print(f"Two-layer causal backtest · tf={args.tf} · view={args.view}")
    print(f"  L1: frozen lean champion ({Path(args.l1_champion).name})")
    print(f"  L2: extend champion      ({Path(args.l2_champion).name})")

    res = logbook.run_causal(l1_params, l2_params, args.tf)
    bar_secs = int(TF.get(args.tf).bar_td.total_seconds())
    print(f"  causal log: {res.n} candles")

    if args.view in ("l1", "all"):
        _print_layer("LAYER 1 (frozen lean champion)", aggregate.boxes_for_layer(res, "L1", bar_secs))
    if args.view in ("l2", "all"):
        _print_layer("LAYER 2 (manages L1's dropped signals)", aggregate.boxes_for_layer(res, "L2", bar_secs))
    if args.view in ("combined", "all"):
        _print_combined(aggregate.combined_boxes(res, bar_secs))

    out = Path(f"{args.out_prefix}_{args.view}_log.csv")
    n = _write_log_csv(res, out)
    print(f"\nwrote per-candle log → {out}  ({n} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
