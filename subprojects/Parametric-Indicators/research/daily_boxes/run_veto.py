"""Option C — test whether a daily-zone VETO would improve the book. SERVER ONLY.

Usage:
  python3 -m research.daily_boxes.run_veto --tf 4h --seed 20260723 --draws 1000 --block 20 --loc-frac 0.02
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_PROJ = Path(__file__).resolve().parents[2]
if str(_PROJ) not in sys.path:
    sys.path.insert(0, str(_PROJ))

from optimize import counterfactual_pause as cp                          # noqa: E402
from research.daily_boxes.informativeness import (                       # noqa: E402
    block_bootstrap_diff_ci, control_location,
)
from research.daily_boxes.levels import DAILY_LEVELS                     # noqa: E402
from research.daily_boxes.veto_test import veto_split                    # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tf", required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--draws", type=int, required=True)
    ap.add_argument("--block", type=int, required=True)
    ap.add_argument("--loc-frac", type=float, required=True)
    ap.add_argument("--out", default="results/daily_boxes")
    a = ap.parse_args()

    C = cp.load_champion(a.tf)
    trades = cp.champion_taken_trades(C)
    tp = float(C["params"]["tp"])
    pv = float(C["pv"])
    box = C["box"]

    print("=" * 72)
    print("OPTION C -- DAILY-ZONE VETO TEST -- parameters actually used")
    print(f"  timeframe        : {a.tf}")
    print(f"  champion tp      : {tp} points  (= ${tp * pv:,.0f} target per contract)")
    print(f"  point value      : ${pv}")
    print(f"  seed/draws/block : {a.seed} / {a.draws} / {a.block}")
    print(f"  loc control frac : {a.loc_frac}")
    print(f"  trades in book   : {len(trades)}")
    print(f"  daily zones      : {[p[2] for p in DAILY_LEVELS]}")
    print("=" * 72)

    if not trades:
        raise SystemExit("ABORT: champion produced no trades")

    rng = np.random.default_rng(a.seed)
    rows = []
    for arm, bx in (("real", box),
                    ("control_location", control_location(box, DAILY_LEVELS, rng, a.loc_frac))):
        r = veto_split(trades, bx, DAILY_LEVELS, tp_points=tp, point_value=pv)
        # the decisive number: are WALLED trades worse than CLEAR ones?
        pt, lo, hi = block_bootstrap_diff_ci(r["walled_points"], r["clear_points"],
                                             a.block, a.draws, 0.10,
                                             np.random.default_rng(a.seed + 1))
        thesis_holds = hi < 0.0        # walled must be RELIABLY worse for a veto to be justified
        print(f"\n[{arm}] walled={r['n_walled']}/{r['n_trades']} "
              f"({r['n_walled']/r['n_trades']:.1%} of the book)")
        print(f"[{arm}] mean walled = {r['mean_walled_points']:+.2f}pt "
              f"(${r['mean_walled_dollars']:+,.0f})   "
              f"mean clear = {r['mean_clear_points']:+.2f}pt (${r['mean_clear_dollars']:+,.0f})")
        print(f"[{arm}] walled - clear = {pt:+.2f}pt  CI90=[{lo:+.2f},{hi:+.2f}]  "
              f"{'WALLED RELIABLY WORSE -> veto justified' if thesis_holds else 'no reliable difference'}")
        print(f"[{arm}] a veto would DELETE {r['n_walled']} trades worth "
              f"${r['pnl_removed_dollars']:+,.0f} (book total ${r['total_pnl_dollars']:+,.0f})")
        rows.append({"tf": a.tf, "arm": arm, "n_trades": r["n_trades"], "n_walled": r["n_walled"],
                     "mean_walled_points": r["mean_walled_points"],
                     "mean_clear_points": r["mean_clear_points"],
                     "diff_points": pt, "ci90_lo": lo, "ci90_hi": hi,
                     "thesis_holds": thesis_holds,
                     "pnl_removed_dollars": r["pnl_removed_dollars"],
                     "total_pnl_dollars": r["total_pnl_dollars"]})

    outdir = Path(a.out); outdir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(outdir / f"{a.tf}_veto.csv", index=False)

    real = rows[0]
    print("\n" + "=" * 72)
    print(f"[VERDICT INPUT] real thesis_holds={real['thesis_holds']}  "
          f"control thesis_holds={rows[1]['thesis_holds']}")
    print(f"[VERDICT INPUT] vetoing would remove ${real['pnl_removed_dollars']:+,.0f} "
          f"from a ${real['total_pnl_dollars']:+,.0f} book")
    print("=" * 72)
    print(f"wrote {outdir}/{a.tf}_veto.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
