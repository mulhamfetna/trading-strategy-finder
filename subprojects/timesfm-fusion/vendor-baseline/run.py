#!/usr/bin/env python3
"""Entry point: walk-forward backtest of the TimesFM standalone strategy on NQ / ES.

    python run.py                     # ES 1h, mock forecaster, walk-forward
    python run.py --instrument NQ
    python run.py --forecaster timesfm --instrument ES --tf 1h
    python run.py --instrument NQ --tf 4h --train-frac 0.7

Prints TRAIN (tuned) vs TEST (out-of-sample) stats and the reference benchmark for context.
"""
from __future__ import annotations

import argparse
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from tfm.data import INSTRUMENTS, load_tf, split_walk_forward, summarize_split
from tfm.forecaster import get_forecaster
from tfm.metrics import fmt_stats
from tfm.strategy import StratParams
from tfm.walkforward import walk_forward

# Reference MTF fusion benchmark (full-period, in-sample) for context.
BENCHMARK = {
    "ES": dict(pnl=71800, n=264, win=43.6, pf=1.83, max_dd=5272, ret_dd=13.62),
    "NQ": dict(pnl=173789, n=481, win=54.7, pf=1.51, max_dd=18572, ret_dd=9.36),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--instrument", default="ES", choices=["ES", "NQ"])
    ap.add_argument("--tf", default="1h")
    ap.add_argument("--forecaster", default="mock")
    ap.add_argument("--train-frac", type=float, default=0.70)
    ap.add_argument("--context-len", type=int, default=256)
    args = ap.parse_args()

    inst = INSTRUMENTS[args.instrument]
    df = load_tf(args.instrument, args.tf)
    train, test = split_walk_forward(df, args.train_frac)

    print("!" * 78)
    print("!  run.py = the STANDALONE experiment (TimesFM picks direction) — it FAILS.")
    print("!  This is NOT the winning strategy. The winner is:  python deploy_gate.py NQ")
    if args.forecaster == "mock":
        print("!  You are running the MOCK (fake placeholder) model — not real TimesFM.")
        print("!  For real TimesFM add:  --forecaster timesfm")
    print("!" * 78 + "\n")
    print(f"=== TimesFM standalone strategy — {args.instrument} {args.tf} "
          f"(forecaster={args.forecaster}) ===")
    print(summarize_split(train, test))
    print("\nTuning on TRAIN (walk-forward grid)... ", flush=True)

    fc = get_forecaster(args.forecaster)
    base = StratParams(context_len=args.context_len)
    res = walk_forward(df, fc, inst, train_frac=args.train_frac, base=base,
                       cache_prefix=f"{args.instrument}_{args.tf}",
                       progress=(args.forecaster != "mock"))
    print("done.\n")

    print(f"BEST PARAMS (chosen on train): {res.best}\n")
    print("-- TRAIN (in-sample, tuned) --")
    print(fmt_stats(res.train_stats, inst.point_value))
    print("\n-- TEST (OUT-OF-SAMPLE, the honest number) --")
    print(fmt_stats(res.test_stats, inst.point_value))

    b = BENCHMARK[args.instrument]
    print(f"\n-- REFERENCE benchmark (MTF fusion, full-period in-sample) --")
    print(f"  net P/L ${b['pnl']:,}   trades {b['n']}   win {b['win']}%   "
          f"PF {b['pf']}   maxDD ${b['max_dd']:,}   return/DD {b['ret_dd']}")
    print("\n  NOTE: TEST is out-of-sample; the benchmark is full-period in-sample — "
          "not directly comparable, but TEST return/DD is the honest yardstick.")
    print("\nTop TRAIN configs:")
    for p, st in res.leaderboard:
        rd = "inf" if st.ret_dd == float("inf") else f"{st.ret_dd:.2f}"
        print(f"  h={p.horizon} edge_k={p.edge_k} floor={p.min_edge_ticks} "
              f"sl={p.sl_mult} tp={p.tp_mult} | n={st.n} pnl=${st.pnl:,.0f} retDD={rd}")


if __name__ == "__main__":
    sys.exit(main())
