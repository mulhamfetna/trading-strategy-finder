"""Phase S3 — regime → dynamic-TP rule grid, scored OUT-OF-SAMPLE vs the fixed champion.

Grid (answers Q2b + Q3a empirically):
  TF combo  ∈ {M, Q, Y, M∩Q, M∩Y, Q∩Y, M∩Q∩Y}          (intersection = label only if all agree, else NEUTRAL)
  rule      ∈ {mean_rev, trend_follow}                   (mean_rev widens TP on counter-trend; trend_follow inverse)
  SL mode   ∈ {pinned (tp_mult), both (sl_tp_mult)}       (Q3b)
For each cell: small (widen W, shrink S) grid fit on TRAIN (≤2025-06) by return/DD, then scored on TEST
(2025-07…2026-05) against the fixed champion (factor≡1). Causal regime labels (regime_features, no look-ahead).
Engine = exact SimpleStrategy + the champion's drawdown breaker (via stage2._breaker). Ranked CSV + top print.

Usage: python3 study_range_regime/regime_eval.py [--pct 0.05]
"""
from __future__ import annotations
import sys, argparse
from pathlib import Path
import numpy as np
import pandas as pd

_HERE = Path(__file__).resolve().parent
_PI = _HERE.parent          # study_range_regime/ → Parametric-Indicators/ (where engine.py, optimize/ live)
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

from engine import SimpleStrategy, SimpleStrategyParams          # noqa: E402
from optimize import timeframes as TF, signals as sig_mod        # noqa: E402
from optimize.sub.data_2024_2026 import load_bundle              # noqa: E402
from optimize.sub.suboptimizer import champion, freeze_once      # noqa: E402
from optimize.sub.stage2 import _breaker                          # noqa: E402
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("regime_features", _HERE / "regime_features.py")
regime_features = _ilu.module_from_spec(_spec); _spec.loader.exec_module(regime_features)  # noqa: E402

_BAR = TF.get("4h").bar_td
TRAIN_END = "2025-06"
WIDEN = [1.25, 1.5, 2.0]
SHRINK = [0.6, 0.8, 1.0]            # 1.0 = "widen-only" variant
TF_COMBOS = ["M", "Q", "Y", "M&Q", "M&Y", "Q&Y", "M&Q&Y"]
RULES = ["mean_rev", "trend_follow"]
SLMODES = ["pinned", "both"]


def _trend_combo(feat: pd.DataFrame, combo: str) -> np.ndarray:
    cols = {"M": "M_trend", "Q": "Q_trend", "Y": "Y_trend"}
    parts = [cols[c] for c in combo.split("&")]
    arr = feat[parts[0]].to_numpy(object).copy()
    for p in parts[1:]:
        other = feat[p].to_numpy(object)
        arr = np.where((arr == other) & (arr != "NEUTRAL"), arr, "NEUTRAL")
    return arr


def _factor(trend: np.ndarray, direction: np.ndarray, rule: str, W: float, S: float) -> np.ndarray:
    counter = ((trend == "HIGH_TREND") & (direction == "long")) | ((trend == "LOW_TREND") & (direction == "short"))
    withtr = ((trend == "HIGH_TREND") & (direction == "short")) | ((trend == "LOW_TREND") & (direction == "long"))
    f = np.ones(len(trend), dtype=float)
    if rule == "mean_rev":
        f = np.where(counter, W, np.where(withtr, S, 1.0))
    else:
        f = np.where(withtr, W, np.where(counter, S, 1.0))
    return f


def _eval(df4, df1, box, gate, sig_obj, champ, mult, lo, hi, mode):
    d = df4.iloc[lo:hi].reset_index(drop=True)
    t0 = d["Date"].iloc[0]; t1 = d["Date"].iloc[-1] + _BAR
    d1 = df1[(df1["Date"] >= t0) & (df1["Date"] < t1)].reset_index(drop=True)
    sp = SimpleStrategyParams(sl_soft_points=float(champ["sl_soft"]), sl_hard_points=float(champ["sl_hard"]),
                              tp_soft_points=float(champ["tp"]), tp_hard_points=float(champ["tp"]),
                              data_path_4h="", data_path_1min="", box_data_path="", flip_entry_direction=False)
    kw = {}
    if mult is not None:
        m = np.asarray(mult[lo:hi], dtype=float)
        kw["sl_tp_mult" if mode == "both" else "tp_mult"] = m
    trades, _ = SimpleStrategy(sp).backtest(d, d1, box, entry_gate=np.asarray(gate[lo:hi], bool),
                                            signals=sig_obj[lo:hi], **kw)
    cand = sorted([t for t in trades if t.get("exit_reason") not in (None, "OPEN")],
                  key=lambda t: pd.Timestamp(t["entry_time"]))
    return _breaker(cand, float(champ["dd_limit"]), int(champ["cooldown"]), float(champ["pv"]))


def _retdd(m):
    return (m["pnl"] / m["max_dd"]) if m["max_dd"] > 0 else (m["pnl"] if m["pnl"] > 0 else 0.0)


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--pct", type=float, default=0.05)
    ap.add_argument("--out", default=str(_HERE / "results" / "regime_eval_ranked.csv")); a = ap.parse_args()
    champ = champion()
    df4, df1, box, vf, months = load_bundle()
    sig_obj = sig_mod.decision_signals(df4, box)
    _si, gate = freeze_once(df4, df1, box, vf, champ)
    feat = regime_features.build(df4, a.pct)
    N = len(df4); tr_hi = int(np.nonzero(months <= TRAIN_END)[0][-1]) + 1
    direction = np.where(sig_obj == "long", "long", np.where(sig_obj == "short", "short", "hold")).astype(object)

    fixed_tr = _eval(df4, df1, box, gate, sig_obj, champ, None, 0, tr_hi, "both")
    fixed_te = _eval(df4, df1, box, gate, sig_obj, champ, None, tr_hi, N, "both")
    print(f"FIXED champion — TRAIN pnl={fixed_tr['pnl']:.0f} dd={fixed_tr['max_dd']:.0f} | "
          f"TEST pnl={fixed_te['pnl']:.0f} dd={fixed_te['max_dd']:.0f} retDD={_retdd(fixed_te):.2f} n={fixed_te['n']}", flush=True)

    rows = []
    for combo in TF_COMBOS:
        trend = _trend_combo(feat, combo)
        for rule in RULES:
            for mode in SLMODES:
                best = None  # (train_retdd, W, S)
                for W in WIDEN:
                    for S in SHRINK:
                        if W == 1.0 and S == 1.0:
                            continue
                        mult = _factor(trend, direction, rule, W, S)
                        mtr = _eval(df4, df1, box, gate, sig_obj, champ, mult, 0, tr_hi, mode)
                        r = _retdd(mtr)
                        if best is None or r > best[0]:
                            best = (r, W, S)
                _, W, S = best
                mult = _factor(trend, direction, rule, W, S)
                te = _eval(df4, df1, box, gate, sig_obj, champ, mult, tr_hi, N, mode)
                rows.append({"tf": combo, "rule": rule, "sl_mode": mode, "W": W, "S": S,
                             "test_pnl": round(te["pnl"], 0), "test_dd": round(te["max_dd"], 0),
                             "test_retDD": round(_retdd(te), 3), "test_n": te["n"], "test_win": te["win"],
                             "vs_fixed_pnl": round(te["pnl"] - fixed_te["pnl"], 0),
                             "beats_fixed_retDD": _retdd(te) > _retdd(fixed_te)})
                print(f"  [{combo:6s} {rule:11s} {mode:6s}] best W{W} S{S} -> TEST pnl={te['pnl']:.0f} "
                      f"dd={te['max_dd']:.0f} retDD={_retdd(te):.2f} n={te['n']} "
                      f"{'BEATS' if _retdd(te) > _retdd(fixed_te) else '-'}", flush=True)

    df = pd.DataFrame(rows).sort_values("test_retDD", ascending=False).reset_index(drop=True)
    df.loc[len(df)] = {"tf": "FIXED", "rule": "-", "sl_mode": "-", "W": 1.0, "S": 1.0,
                       "test_pnl": round(fixed_te["pnl"], 0), "test_dd": round(fixed_te["max_dd"], 0),
                       "test_retDD": round(_retdd(fixed_te), 3), "test_n": fixed_te["n"], "test_win": fixed_te["win"],
                       "vs_fixed_pnl": 0, "beats_fixed_retDD": False}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True); df.to_csv(a.out, index=False)
    print(f"\nTOP 8 by TEST return/DD (fixed retDD={_retdd(fixed_te):.2f}):")
    print(df.head(8).to_string(index=False))
    print(f"\nwrote {a.out} ({len(rows)} cells)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
