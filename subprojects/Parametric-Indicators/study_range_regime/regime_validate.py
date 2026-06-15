"""Phase S3-gate — MULTI-FOLD walk-forward validation of the top regime cells.

S3 selected cells on ONE OOS window → selection/overfit risk. Here we take each top cell's FIXED config
(TF, rule, SL-mode, W, S — already chosen) and score it vs the fixed champion across K contiguous folds
spanning the whole 2024–2026 series. A *real* edge beats fixed in MOST folds; a one-window fluke does not.

Regime labels are causal over the full history (slicing a fold keeps each bar's label using only its own
past), so a fold is a realistic live sub-period. Engine = exact + champion breaker (reused from regime_eval).

Usage: python3 study_range_regime/regime_validate.py [--pct 0.05] [--folds 6]
"""
from __future__ import annotations
import sys, argparse
from pathlib import Path
import numpy as np
import pandas as pd

_HERE = Path(__file__).resolve().parent
if str(_HERE.parent) not in sys.path:
    sys.path.insert(0, str(_HERE.parent))

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("regime_eval", _HERE / "regime_eval.py")
RE = _ilu.module_from_spec(_spec); _spec.loader.exec_module(RE)   # reuse _eval/_factor/_trend_combo/_retdd

from optimize import signals as sig_mod                            # noqa: E402
from optimize.sub.data_2024_2026 import load_bundle                # noqa: E402
from optimize.sub.suboptimizer import champion, freeze_once        # noqa: E402

# top-3 distinct cells from S3 (results/regime_eval_ranked.csv)
TOP = [
    ("Q", "mean_rev",     "both",   2.0, 0.6),
    ("M", "trend_follow", "pinned", 1.25, 1.0),
    ("Q", "trend_follow", "pinned", 1.25, 1.0),
]


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--pct", type=float, default=0.05)
    ap.add_argument("--folds", type=int, default=6)
    ap.add_argument("--out", default=str(_HERE / "results" / "regime_validate_folds.csv")); a = ap.parse_args()
    champ = champion()
    df4, df1, box, vf, months = load_bundle()
    sig_obj = sig_mod.decision_signals(df4, box)
    _si, gate = freeze_once(df4, df1, box, vf, champ)
    feat = RE.regime_features.build(df4, a.pct)
    direction = np.where(sig_obj == "long", "long", np.where(sig_obj == "short", "short", "hold")).astype(object)
    N = len(df4)
    bounds = np.linspace(0, N, a.folds + 1, dtype=int)
    folds = [(int(bounds[i]), int(bounds[i + 1])) for i in range(a.folds)]
    dt = pd.to_datetime(df4["Date"]).dt.strftime("%Y-%m")

    rows = []
    print(f"{a.folds} folds over {dt.iloc[0]}…{dt.iloc[-1]}  (fixed champion = baseline each fold)\n")
    # precompute per-cell full mult arrays
    cells = []
    for (tf, rule, mode, W, S) in TOP:
        trend = RE._trend_combo(feat, tf)
        mult = RE._factor(trend, direction, rule, W, S)
        cells.append((f"{tf}|{rule}|{mode}|W{W}/S{S}", mode, mult))

    for fi, (lo, hi) in enumerate(folds):
        span = f"{dt.iloc[lo]}…{dt.iloc[hi-1]}"
        fx = RE._eval(df4, df1, box, gate, sig_obj, champ, None, lo, hi, "both")
        fx_r = RE._retdd(fx)
        line = f"fold {fi+1} [{span}] fixed retDD={fx_r:.2f} (pnl {fx['pnl']:.0f}/dd {fx['max_dd']:.0f}/n{fx['n']})"
        for name, mode, mult in cells:
            m = RE._eval(df4, df1, box, gate, sig_obj, champ, mult, lo, hi, mode)
            r = RE._retdd(m); win = r > fx_r
            rows.append({"fold": fi + 1, "span": span, "cell": name, "retDD": round(r, 3),
                         "fixed_retDD": round(fx_r, 3), "pnl": round(m["pnl"], 0), "dd": round(m["max_dd"], 0),
                         "n": m["n"], "beats_fixed": win})
            line += f"\n     {name:34s} retDD={r:5.2f} pnl={m['pnl']:7.0f} {'BEAT' if win else '-'}"
        print(line, flush=True)

    df = pd.DataFrame(rows)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True); df.to_csv(a.out, index=False)
    print("\n=== robustness: folds beaten / total ===")
    for name in [c[0] for c in cells]:
        sub = df[df.cell == name]
        print(f"  {name:34s} beats fixed in {int(sub.beats_fixed.sum())}/{len(sub)} folds  "
              f"(median retDD {sub.retDD.median():.2f} vs fixed {sub.fixed_retDD.median():.2f})")
    print(f"\nwrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
