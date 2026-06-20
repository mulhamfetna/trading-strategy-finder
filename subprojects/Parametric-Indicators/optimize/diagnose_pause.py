"""Diagnose WHAT causes the champion's long no-entry pauses — read-only, no engine change.

For the wsh4 1-min 4h champion, recompute the per-decision-bar entry gate exactly as core.backtest_metrics
does (vol_gate ∧ ¬veto ∧ confirm≥K, on box-signal bars) and attribute every bar to its blocking cause:
  no_signal   — the box produced no long/short signal that bar (no entry candidate at all)
  vol_gated   — candidate, but HAR-RV forecast > the gate_pct percentile (vol gate blocked it)
  vetoed      — candidate, vol ok, but an indicator vetoed
  confirm<K   — candidate, vol ok, not vetoed, but < K confirmers
  would_enter — gate fully open (an entry opportunity)

Then it finds the LONGEST gap between would_enter bars and breaks that gap down by cause — answering: is the
pause driven by the VOL GATE (⇒ a gate redesign helps) or simply by sparse box signals (⇒ it does not)?

Run:  python3 -m optimize.diagnose_pause [--tf 4h]
"""
from __future__ import annotations

import argparse
import sys
import numpy as np
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_PI = _HERE.parent
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

from optimize import two_stage as TS
from indicators import library, runner
from volatility import gate_threshold


def diagnose(tf: str = "4h") -> dict:
    ctx = TS._Ctx(tf, split_sltp=False, ind_1min=True, folds=5, min_trades=5, warm_start=True)
    if not ctx.has_champion:
        raise SystemExit("no champion seed found (need optimize/results/wsh4_champions_full.json)")
    d, d1, box, vf, n_split = ctx.df_dec, ctx.df1, ctx.box, ctx.vf, ctx.n_split
    bar_td = ctx.tf.bar_td
    cont = ctx.champ_cont
    gate_pct = float(cont["gate_pct"]); K = int(cont["k"])
    params = ctx.build_params(ctx.champ_en, ctx.champ_flip, cont)
    specs = params["indicators"]
    inds = library.from_specs([s for s in specs if s.get("enabled")])

    n = len(d)
    sig = np.asarray(ctx.sig_int)[:n]
    candidate = sig != 0                                    # the box produced a long/short signal this bar

    # vol gate (causal threshold frozen on vf[:n_split]) — same as core.backtest_metrics
    vol_gate = np.ones(n, dtype=bool)
    if gate_pct > 0:
        gthr = gate_threshold(vf, n_split, gate_pct)
        vol_gate = vf[:n] <= gthr

    # indicator veto / confirm (1-minute source, as the champion was tuned)
    src = runner.indicator_source_1min(d, d1, bar_td)
    votes = runner.compute_votes(d, box, inds, src=src)
    vmask = np.asarray(runner.veto_mask(d, box, inds, src=src, votes=votes))[:n]
    cmask = np.asarray(runner.confirm_mask(d, box, inds, K, src=src, votes=votes))[:n]

    cause = np.empty(n, dtype=object)
    cause[~candidate] = "no_signal"
    c = candidate
    cause[c & ~vol_gate] = "vol_gated"
    cause[c & vol_gate & vmask] = "vetoed"
    cause[c & vol_gate & ~vmask & ~cmask] = "confirm<K"
    would = c & vol_gate & ~vmask & cmask
    cause[would] = "would_enter"

    bars_per_day = 24.0 / (bar_td.total_seconds() / 3600.0)
    cats = ["no_signal", "vol_gated", "vetoed", "confirm<K", "would_enter"]
    hist = {k: int((cause == k).sum()) for k in cats}

    # longest gap between would_enter bars
    wi = np.flatnonzero(would)
    longest = {"len_bars": 0, "days": 0.0, "start": None, "end": None, "by_cause": {}}
    if len(wi) >= 2:
        gaps = np.diff(wi)
        j = int(np.argmax(gaps))
        a, b = int(wi[j]), int(wi[j + 1])               # gap is bars (a, b)
        seg = cause[a + 1:b]
        longest = {"len_bars": int(b - a - 1), "days": round((b - a - 1) / bars_per_day, 2),
                   "start": str(d["Date"].iloc[a + 1]), "end": str(d["Date"].iloc[b - 1]),
                   "by_cause": {k: int((seg == k).sum()) for k in cats if k != "would_enter"}}
    return {"tf": tf, "n_bars": n, "gate_pct": gate_pct, "K": K, "n_would_enter": int(would.sum()),
            "bars_per_day": round(bars_per_day, 2), "hist": hist, "longest_gap": longest}


def main() -> int:
    import warnings; warnings.filterwarnings("ignore")
    ap = argparse.ArgumentParser(); ap.add_argument("--tf", default="4h"); a = ap.parse_args()
    r = diagnose(a.tf)
    print(f"=== pause diagnosis [{r['tf']}]  champion gate_pct={r['gate_pct']:.0f}  K={r['K']}  "
          f"{r['bars_per_day']:.1f} bars/day ===")
    print(f"bars={r['n_bars']}  would-enter opportunities={r['n_would_enter']}")
    tot = r["n_bars"]
    print("--- per-bar blocking cause (all bars) ---")
    for k, v in r["hist"].items():
        print(f"  {k:12} {v:6}  ({100*v/tot:4.1f}%)")
    g = r["longest_gap"]
    print(f"--- LONGEST gap between entry opportunities: {g['days']} days ({g['len_bars']} bars) "
          f"{g['start']} → {g['end']} ---")
    if g["by_cause"]:
        gb = sum(g["by_cause"].values()) or 1
        for k, v in g["by_cause"].items():
            print(f"  {k:12} {v:5}  ({100*v/gb:4.1f}% of the gap)")
        cand_blocked = gb - g["by_cause"].get("no_signal", 0)
        print(f"  → of the {gb} pause bars, {cand_blocked} had a box signal that the GATE blocked "
              f"({100*cand_blocked/gb:.1f}%); {g['by_cause'].get('no_signal',0)} had no signal at all.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
