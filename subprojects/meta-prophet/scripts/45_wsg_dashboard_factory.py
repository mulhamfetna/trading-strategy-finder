"""Workstream G — dashboard factory: one sibling clone per vol-lever, entry-mode dropdown.

For each volatility lever (none / S / G / S+G) writes a standalone dashboard under
dashboard_combos/<lever>/ (index.html cloned from the verified dashboard/index.html, with the
config dropdown repurposed to the THREE entry modes: normal / flipped / cusum_flip). The MAIN
dashboard/ is never touched.

Each dashboard keeps the original window picker (2025 / 2026 / full) and panels (candles+trades,
adaptive SL/TP distances, regime gate, equity). The cusum_flip config is built by running the
clone both normal and flipped, then choosing per-trade (by entry bar) according to the causal
CUSUM change-point decision on the normal trade stream (notes/32, k=20 h=400).

ENGINE: verified single-contract clone only (engine_clone/). No 1-1-2 ladder. Generated data.js
is git-ignored (regenerable); the index.html clones + README are tracked.
"""
from __future__ import annotations

import json
import re
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
LEVERS = {"none": (False, False), "S": (True, False), "G": (False, True), "S+G": (True, True)}
ENTRY_MODES = ["normal", "flipped", "cusum_flip"]
CUSUM_K, CUSUM_H = 20.0, 400.0


def _ts(dt): return int(pd.Timestamp(dt).timestamp())


def rule_cusum(pnl, k=CUSUM_K, h=CUSUM_H):
    n = len(pnl); mode = np.ones(n); prev = 1; s_hi = s_lo = 0.0
    for i in range(n):
        mode[i] = prev; x = pnl[i]
        s_hi = max(0.0, s_hi + x - k); s_lo = max(0.0, s_lo - x - k)
        if s_lo > h: prev = -1; s_hi = s_lo = 0.0
        elif s_hi > h: prev = 1; s_hi = s_lo = 0.0
    return mode


def _trade_dict(t):
    return {"entry_idx": int(t["entry_idx"]), "entry_time": _ts(t["entry_time"]),
            "exit_time": _ts(t["exit_time"]), "entry_price": float(t["entry_price"]),
            "exit_price": float(t["exit_price"]), "direction": t["direction"],
            "exit_reason": t["exit_reason"], "pnl_points": float(t["pnl_points"]),
            "sl_hard_line": float(t["sl_hard_line"]), "tp_hard_line": float(t["tp_hard_line"])}


def _run(d4, d1, box, use_S, use_G, S, G, flip):
    kw = {}
    if use_S: kw["sl_tp_mult"] = S
    if use_G: kw["entry_gate"] = G
    p = bm.SimpleStrategyParams(sl_soft_points=SL_SOFT, sl_hard_points=SL_HARD, tp_soft_points=TP_HARD,
                                tp_hard_points=TP_HARD, data_path_4h="", data_path_1min="",
                                box_data_path="", flip_entry_direction=flip)
    trades, _ = bm.SimpleStrategy(p).backtest(d4, d1, box, **kw)
    return [t for t in trades if t.get("exit_reason") not in (None, "OPEN")]


def _panels(d4, use_S, use_G, S, G):
    times = [_ts(d4["Date"].iloc[i]) for i in range(len(d4))]
    sl = [{"time": times[i], "value": SL_HARD * (float(S[i]) if use_S else 1.0)} for i in range(len(d4))]
    tp = [{"time": times[i], "value": TP_HARD * (float(S[i]) if use_S else 1.0)} for i in range(len(d4))]
    gate = [{"time": times[i], "value": (1 if (not use_G or bool(G[i])) else 0)} for i in range(len(d4))]
    return sl, tp, gate


def _equity_summary(closed):
    eq, cum = [], 0.0
    for t in sorted(closed, key=lambda x: x["exit_time"]):
        cum += float(t["pnl_points"]) * NQ_PV
        eq.append({"time": int(t["exit_time"]), "value": round(cum, 2)})
    pnl = np.array([t["pnl_points"] for t in closed]) if closed else np.array([0.0])
    pd_ = pnl * NQ_PV; ea = np.cumsum(pd_)
    dd = float((np.maximum.accumulate(ea) - ea).max()) if len(ea) else 0.0
    return eq, {"pnl": float(pd_.sum()), "n": len(closed),
                "win": float((pnl > 0).mean() * 100) if closed else 0.0, "dd": dd}


def build_window(d4, d1, box, vf, S, G, lo, hi, use_S, use_G):
    d4w = d4.iloc[lo:hi].reset_index(drop=True)
    t0, t1 = d4w["Date"].iloc[0], d4w["Date"].iloc[-1] + pd.Timedelta(hours=4)
    d1w = d1[(d1["Date"] >= t0) & (d1["Date"] < t1)].reset_index(drop=True)
    sS, gG = S[lo:hi], G[lo:hi]
    candles = [{"time": _ts(d4w["Date"].iloc[i]), "open": float(d4w["Open"].iloc[i]),
                "high": float(d4w["High"].iloc[i]), "low": float(d4w["Low"].iloc[i]),
                "close": float(d4w["Close"].iloc[i])} for i in range(len(d4w))]
    vol = [{"time": _ts(d4w["Date"].iloc[i]), "value": round(float(vf[lo + i]), 2)} for i in range(len(d4w))]
    sl, tp, gate = _panels(d4w, use_S, use_G, sS, gG)

    nrm = [_trade_dict(t) for t in _run(d4w, d1w, box, use_S, use_G, sS, gG, flip=False)]
    flp = [_trade_dict(t) for t in _run(d4w, d1w, box, use_S, use_G, sS, gG, flip=True)]
    # cusum: causal mode from normal stream, pick per entry bar
    flp_by_idx = {t["entry_idx"]: t for t in flp}
    nrm_sorted = sorted(nrm, key=lambda x: x["entry_idx"])
    mode = rule_cusum(np.array([t["pnl_points"] for t in nrm_sorted]))
    cus = []
    for t, m in zip(nrm_sorted, mode):
        cus.append(t if m > 0 else flp_by_idx.get(t["entry_idx"], t))

    configs = {}
    for name, closed in (("normal", nrm), ("flipped", flp), ("cusum_flip", cus)):
        eq, summ = _equity_summary(closed)
        configs[name] = {"trades": closed, "sl_dist": sl, "tp_dist": tp,
                         "gate": gate, "equity": eq, "summary": summ}
    return {"candles": candles, "vol": vol, "configs": configs}


_OPTS = ('      <option value="normal">normal entry</option>\n'
         '      <option value="flipped">flipped entry</option>\n'
         '      <option value="cusum_flip" selected>cusum dynamic-flip</option>')


def clone_index(template: str, lever: str) -> str:
    html = re.sub(r'(<select id="cfg">\s*).*?(\s*</select>)',
                  lambda m: m.group(1) + "\n" + _OPTS + m.group(2), template, flags=re.DOTALL)
    html = html.replace("<title>", f"<title>[{lever}] ")
    return html


def main():
    df4, df1, box = bm.load_all()
    n2025 = int((df4["_year"] == 2025).sum()); N = len(df4)
    vf = bm.har_rv_forecast(df4)
    gthr = float(np.percentile(vf[:n2025], 80))
    S = bm.lever_sl_tp(vf, mode="expanding"); G = bm.lever_gate(vf, gthr)
    split_ts = _ts(df4.iloc[n2025]["Date"])
    windows = {"2025": (0, n2025), "2026": (n2025, N), "full": (0, N)}

    template = (ROOT / "dashboard" / "index.html").read_text()
    base = ROOT / "dashboard_combos"; base.mkdir(exist_ok=True)

    for lever, (use_S, use_G) in LEVERS.items():
        datasets = {w: build_window(df4, df1, box, vf, S, G, lo, hi, use_S, use_G)
                    for w, (lo, hi) in windows.items()}
        d = base / lever; d.mkdir(exist_ok=True)
        (d / "data.js").write_text("window.DASHBOARD_DATA = " +
                                   json.dumps({"datasets": datasets, "split_ts": split_ts,
                                               "windows": list(windows.keys())}) + ";\n")
        (d / "index.html").write_text(clone_index(template, lever))
        s = datasets["full"]["configs"]
        print(f"[{lever:>3}] full: normal=${s['normal']['summary']['pnl']:>9,.0f}  "
              f"flipped=${s['flipped']['summary']['pnl']:>9,.0f}  "
              f"cusum=${s['cusum_flip']['summary']['pnl']:>9,.0f}  -> {d}")
    print(f"\nwrote {len(LEVERS)} sibling dashboards under {base} (main dashboard/ untouched)")


if __name__ == "__main__":
    main()
