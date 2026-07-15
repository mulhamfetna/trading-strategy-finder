#!/usr/bin/env python3
"""Walk-forward straight off the disk-cached forecasts (no model load): sweep the CHEAP threshold
grid + direction mode + vol gate for a given (instrument, tf, horizon) and print OOS vs benchmark.

Requires the full-series forecast for (ctx,horizon) to already be cached (run diagnose/run_diag or
precompute first). Instant.

    python wf_cache.py ES 1h 24
    python wf_cache.py NQ 1h 24
"""
from __future__ import annotations

import sys

from tfm.data import INSTRUMENTS, load_tf
from tfm.forecaster import get_forecaster
from tfm.metrics import fmt_stats
from tfm.strategy import StratParams
from tfm.walkforward import walk_forward

BENCHMARK = {
    "ES": dict(pnl=71800, n=264, max_dd=5272, ret_dd=13.62),
    "NQ": dict(pnl=173789, n=481, max_dd=18572, ret_dd=9.36),
}

GRID = dict(
    context_len=[512],
    horizon=[24],                              # must be cached
    direction_mode=["momentum", "skew"],
    edge_k=[0.2, 0.4, 0.7, 1.0],
    min_edge_ticks=[4.0, 8.0, 16.0],
    sl_mult=[0.8, 1.2, 1.8],
    tp_mult=[1.2, 2.0, 3.0],
    gate_spread_pct=[100.0, 70.0, 40.0],
)


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    inst_name = (sys.argv[1] if len(sys.argv) > 1 else "ES").upper()
    tf = sys.argv[2] if len(sys.argv) > 2 else "1h"
    horizon = int(sys.argv[3]) if len(sys.argv) > 3 else 24
    GRID["horizon"] = [horizon]

    inst = INSTRUMENTS[inst_name]
    df = load_tf(inst_name, tf)
    fc = get_forecaster("timesfm")  # only used on cache miss

    res = walk_forward(df, fc, inst, train_frac=0.70, base=StratParams(),
                       grid=GRID, min_trades=20, cache_prefix=f"{inst_name}_{tf}", top_k=10)

    print(f"=== {inst_name} {tf} h{horizon} — walk-forward off cached TimesFM forecasts ===")
    print(f"BEST (chosen on TRAIN): mode={res.best.direction_mode} edge_k={res.best.edge_k} "
          f"floor={res.best.min_edge_ticks} sl={res.best.sl_mult} tp={res.best.tp_mult} "
          f"gate={res.best.gate_spread_pct}\n")
    print("-- TRAIN (in-sample, tuned) --")
    print(fmt_stats(res.train_stats, inst.point_value))
    print("\n-- TEST (OUT-OF-SAMPLE) --")
    print(fmt_stats(res.test_stats, inst.point_value))
    b = BENCHMARK[inst_name]
    print(f"\n-- REFERENCE (full-period in-sample) --  pnl ${b['pnl']:,}  "
          f"maxDD ${b['max_dd']:,}  return/DD {b['ret_dd']}")

    print("\nTop TRAIN configs (params | TRAIN → TEST):")
    for p, tr in res.leaderboard:
        # recompute this config's test by re-running walk_forward would be wasteful; leaderboard
        # holds train stats only. Show train; the single best's TEST is above.
        rd = "inf" if tr.ret_dd == float("inf") else f"{tr.ret_dd:.2f}"
        print(f"  {p.direction_mode:8} edge_k={p.edge_k} floor={p.min_edge_ticks} "
              f"sl={p.sl_mult} tp={p.tp_mult} gate={p.gate_spread_pct} | "
              f"n={tr.n} pnl=${tr.pnl:,.0f} retDD={rd}")


if __name__ == "__main__":
    main()
