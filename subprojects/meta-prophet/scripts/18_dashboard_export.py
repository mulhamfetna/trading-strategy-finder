"""Phase G — export data for the standalone clone dashboard.

Runs the 4 single-contract configs (baseline / S / G / S+G) through the CLONED verified simple
engine, across 3 DATA WINDOWS (2025 / 2026 / full), and writes dashboard/data.js (embedded JS,
so index.html opens with no server / no CORS).

Model definition is FROZEN on 2025 (v_ref, gate threshold) and the per-bar levers are computed once
on the full series, then SLICED per window — so a bar's SL/TP multiplier and gate decision are
identical whether viewed in 'full' or '2026'. The window selector only changes which bars the engine
runs on (same semantics as the original dashboard's 2025 / 2026 / full picker).

ENGINE: verified simple single-contract engine only (engine_clone/). No 1-1-2 ladder.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJ = Path("/mnt/data/projects/trading")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJ)); sys.path.insert(0, str(ROOT))

import importlib.util
spec = importlib.util.spec_from_file_location("bm", ROOT / "scripts" / "17_backtest_matrix.py")
bm = importlib.util.module_from_spec(spec); spec.loader.exec_module(bm)

NQ_PV = 20.0
SL_HARD, TP_HARD, SL_SOFT = 100.0, 50.0, 80.0
CONFIGS = ["0_baseline", "1_S", "2_G", "3_S+G"]


def _ts(dt) -> int:
    return int(pd.Timestamp(dt).timestamp())


def run_config(df4, df1, box, name, S, G):
    """df4/df1 are window slices (df4 index reset); S/G are arrays aligned to df4's 0-based index."""
    kw = {}
    if "S" in name:
        kw["sl_tp_mult"] = S
    if "G" in name:
        kw["entry_gate"] = G
    p = bm.SimpleStrategyParams(sl_soft_points=SL_SOFT, sl_hard_points=SL_HARD, tp_soft_points=TP_HARD,
                                tp_hard_points=TP_HARD, data_path_4h="", data_path_1min="",
                                box_data_path="", flip_entry_direction=False)
    trades, _ = bm.SimpleStrategy(p).backtest(df4, df1, box, **kw)
    closed = [t for t in trades if t.get("exit_reason") not in (None, "OPEN")]

    tr_out = [{
        "entry_time": _ts(t["entry_time"]), "exit_time": _ts(t["exit_time"]),
        "entry_price": float(t["entry_price"]), "exit_price": float(t["exit_price"]),
        "direction": t["direction"], "exit_reason": t["exit_reason"],
        "pnl_points": float(t["pnl_points"]),
        "sl_hard_line": float(t["sl_hard_line"]), "tp_hard_line": float(t["tp_hard_line"]),
    } for t in closed]

    use_S, use_G = "S" in name, "G" in name
    times = [_ts(df4["Date"].iloc[i]) for i in range(len(df4))]
    sl_dist = [{"time": times[i], "value": SL_HARD * (float(S[i]) if use_S else 1.0)} for i in range(len(df4))]
    tp_dist = [{"time": times[i], "value": TP_HARD * (float(S[i]) if use_S else 1.0)} for i in range(len(df4))]
    gate = [{"time": times[i], "value": (1 if (not use_G or bool(G[i])) else 0)} for i in range(len(df4))]

    eq, cum = [], 0.0
    for t in sorted(closed, key=lambda x: pd.Timestamp(x["exit_time"])):
        cum += float(t["pnl_points"]) * NQ_PV
        eq.append({"time": _ts(t["exit_time"]), "value": round(cum, 2)})

    pnl_pts = np.array([float(t["pnl_points"]) for t in closed]) if closed else np.array([0.0])
    pnl_d = pnl_pts * NQ_PV
    eqarr = np.cumsum(pnl_d)
    dd = float((np.maximum.accumulate(eqarr) - eqarr).max()) if len(eqarr) else 0.0
    summary = {"pnl": float(pnl_d.sum()), "n": len(closed),
               "win": float((pnl_pts > 0).mean() * 100) if closed else 0.0, "dd": dd}
    return {"trades": tr_out, "sl_dist": sl_dist, "tp_dist": tp_dist,
            "gate": gate, "equity": eq, "summary": summary}


def build_window(df4, df1, box, vf, S, G, lo, hi):
    """Slice everything to bar range [lo, hi) and run all configs."""
    d4 = df4.iloc[lo:hi].reset_index(drop=True)
    t0, t1 = d4["Date"].iloc[0], d4["Date"].iloc[-1] + pd.Timedelta(hours=4)
    d1 = df1[(df1["Date"] >= t0) & (df1["Date"] < t1)].reset_index(drop=True)
    sS, gG = S[lo:hi], G[lo:hi]
    candles = [{"time": _ts(d4["Date"].iloc[i]), "open": float(d4["Open"].iloc[i]),
                "high": float(d4["High"].iloc[i]), "low": float(d4["Low"].iloc[i]),
                "close": float(d4["Close"].iloc[i])} for i in range(len(d4))]
    vol = [{"time": _ts(d4["Date"].iloc[i]), "value": round(float(vf[lo + i]), 2)} for i in range(len(d4))]
    configs = {name: run_config(d4, d1, box, name, sS, gG) for name in CONFIGS}
    return {"candles": candles, "vol": vol, "configs": configs}


def main():
    df4, df1, box = bm.load_all()
    n2025 = int((df4["_year"] == 2025).sum())
    N = len(df4)
    vf = bm.har_rv_forecast(df4)
    v_ref = float(vf[:n2025].mean()); gthr = float(np.percentile(vf[:n2025], 80))
    S = bm.lever_sl_tp(vf, mode="expanding"); G = bm.lever_gate(vf, gthr)

    windows = {"2025": (0, n2025), "2026": (n2025, N), "full": (0, N)}
    datasets = {}
    for wname, (lo, hi) in windows.items():
        datasets[wname] = build_window(df4, df1, box, vf, S, G, lo, hi)
        for cn in CONFIGS:
            s = datasets[wname]["configs"][cn]["summary"]
            print(f"  [{wname:>4}] {cn:<10} pnl=${s['pnl']:>9,.0f}  n={s['n']:>4}  win={s['win']:4.1f}%  dd=${s['dd']:>8,.0f}")

    split_ts = _ts(df4.iloc[n2025]["Date"])
    payload = {"datasets": datasets, "split_ts": split_ts, "windows": list(windows.keys())}
    out = ROOT / "dashboard" / "data.js"
    out.write_text("window.DASHBOARD_DATA = " + json.dumps(payload) + ";\n")
    print(f"wrote {out}  ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
