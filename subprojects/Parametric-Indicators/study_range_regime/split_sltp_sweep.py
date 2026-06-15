"""Q1 — sweep SEPARATE long vs short SL/TP for the deployed champion (all indicators fixed = 4h-1m winner).

Holds the champion gate + 8 indicators + breaker FIXED; varies ONLY the long-side and short-side SL/TP scale
(independently) around the champion's shared base (sl_soft=149.8 / sl_hard=167.1 / tp=120.2). Each side's three
points scale together. Scored via the dashboard-canonical `strategy.build_payload` (per-window gate), full
2024–2026 + per-year columns. Baseline = shared (long_scale=short_scale=1.0). Ranked by return/DD.

Emits results/split_sltp_sweep.csv (+ prints the table). Decision read in REPORT_Q1_split_sltp.md.
Usage:  python3 study_range_regime/split_sltp_sweep.py
"""
from __future__ import annotations
import sys, json
from pathlib import Path
import numpy as np
import pandas as pd

_PI = Path(__file__).resolve().parents[1]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))
import strategy                                            # noqa: E402

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
CH = json.load(open(_PI / "shareable/winning_strategy_backtester/champions/4h.json"))["preset"]
BASE = dict(sl_soft=149.8, sl_hard=167.1, tp=120.2)
SCALES = [0.5, 0.75, 1.0, 1.25, 1.5]


def _side(scale):
    return dict(sl_soft=round(BASE["sl_soft"] * scale, 2),
                sl_hard=round(BASE["sl_hard"] * scale, 2),
                tp=round(BASE["tp"] * scale, 2))


def run(df4, df1, vf, box, n, window, long_s, short_s):
    p = dict(CH); p["timeframe"] = "4h"; p["window"] = window
    L, S = _side(long_s), _side(short_s)
    p.update(long_sl_soft=L["sl_soft"], long_sl_hard=L["sl_hard"], long_tp=L["tp"],
             short_sl_soft=S["sl_soft"], short_sl_hard=S["sl_hard"], short_tp=S["tp"])
    s = strategy.build_payload(df4, df1, box, vf, n, p)["meta"]["summary"]
    dd = s["max_dd"]
    return dict(pnl=round(s["pnl"], 0), dd=round(dd, 0),
                retDD=round(s["pnl"] / dd, 3) if dd > 0 else 0.0, n=s["n_taken"], win=s["win"])


def main() -> int:
    RES.mkdir(parents=True, exist_ok=True)
    df4, df1, box, vf, n = strategy.get_bundle("4h")
    rows = []
    for ls in SCALES:
        for ss in SCALES:
            full = run(df4, df1, vf, box, n, "full", ls, ss)
            y24 = run(df4, df1, vf, box, n, "2024", ls, ss)
            y25 = run(df4, df1, vf, box, n, "2025", ls, ss)
            y26 = run(df4, df1, vf, box, n, "2026", ls, ss)
            rows.append(dict(long_scale=ls, short_scale=ss,
                             pnl=full["pnl"], dd=full["dd"], retDD=full["retDD"], n=full["n"], win=full["win"],
                             pnl_2024=y24["pnl"], pnl_2025=y25["pnl"], pnl_2026=y26["pnl"]))
            print(f"  L{ls} S{ss}: full pnl={full['pnl']:.0f} dd={full['dd']:.0f} retDD={full['retDD']:.2f} n={full['n']}", flush=True)
    df = pd.DataFrame(rows)
    base = df[(df.long_scale == 1.0) & (df.short_scale == 1.0)].iloc[0]
    df["vs_base_pnl"] = (df["pnl"] - base["pnl"]).round(0)
    df["symmetric"] = df.long_scale == df.short_scale
    df = df.sort_values("retDD", ascending=False).reset_index(drop=True)
    df.to_csv(RES / "split_sltp_sweep.csv", index=False)
    print(f"\nBASELINE (shared 1.0/1.0): pnl={base['pnl']:.0f} dd={base['dd']:.0f} retDD={base['retDD']:.2f} n={base['n']}")
    print("\nTOP 8 by full-period return/DD:")
    print(df.head(8).to_string(index=False))
    best_asym = df[~df.symmetric].iloc[0]
    print(f"\nbest ASYMMETRIC: L{best_asym.long_scale}/S{best_asym.short_scale} retDD={best_asym.retDD} "
          f"pnl={best_asym.pnl:.0f} (vs base {base['retDD']:.2f}/{base['pnl']:.0f})")
    print(f"wrote {RES/'split_sltp_sweep.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
