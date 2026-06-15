"""Export the cross-year SL/TP-scale comparison tables (STUDY_cross_year_scale.md) as CSV data files.

Dashboard-consistent path (build_payload, per-window gate). Emits:
  results/cross_year_scale_sweep.csv   — year × scale → pnl, dd, retDD, n, win
  results/cross_year_q1_recovery.csv   — year → mean_vf, mean_atr, mean_price, vol/ATR-implied scale, optimum
  results/cross_year_q2_compare.csv    — year × {fixed, vol_scaled, oracle} → pnl, dd  (+ TOTAL row)
"""
from __future__ import annotations
import sys, json
from pathlib import Path
import numpy as np
import pandas as pd

_HERE = Path(__file__).resolve().parent
if str(_HERE.parent) not in sys.path:
    sys.path.insert(0, str(_HERE.parent))
import strategy                       # noqa: E402
from indicators import classic        # noqa: E402

CH = json.load(open(_HERE.parent / "shareable/winning_strategy_backtester/champions/4h.json"))["preset"]
BASE = dict(sl_soft=149.8, sl_hard=167.1, tp=120.2)
SCALES = [0.5, 0.6, 0.75, 0.9, 1.0, 1.25]
YEARS = ["2024", "2025", "2026"]
RES = _HERE / "results"; RES.mkdir(parents=True, exist_ok=True)


def run(df4, df1, vf, box, n, y, scale):
    p = dict(CH); p["timeframe"] = "4h"; p["window"] = y
    p["sl_soft"] = round(BASE["sl_soft"] * scale, 2)
    p["sl_hard"] = round(BASE["sl_hard"] * scale, 2)
    p["tp"] = round(BASE["tp"] * scale, 2)
    s = strategy.build_payload(df4, df1, box, vf, n, p)["meta"]["summary"]
    dd = s["max_dd"]
    return dict(pnl=round(s["pnl"], 0), dd=round(dd, 0),
                retDD=round(s["pnl"] / dd, 3) if dd > 0 else 0.0, n=s["n_taken"], win=s["win"])


def main() -> int:
    df4, df1, box, vf, n = strategy.get_bundle("4h")

    # 1) scale sweep
    rows = []
    for y in YEARS:
        for sc in SCALES:
            r = run(df4, df1, vf, box, n, y, sc); rows.append(dict(year=y, scale=sc, **r))
    sweep = pd.DataFrame(rows); sweep.to_csv(RES / "cross_year_scale_sweep.csv", index=False)
    # best scale per year by retDD
    best = {y: sweep[sweep.year == y].sort_values("retDD", ascending=False).iloc[0]["scale"] for y in YEARS}

    # 2) q1 recovery (per-year vol/range level from each own bundle)
    lvl = {}
    for y in YEARS:
        d4, d1, b, vfy, ny = strategy.load_year_bundle(int(y))
        atr = classic.atr(d4["High"].to_numpy(float), d4["Low"].to_numpy(float), d4["Close"].to_numpy(float), 14)
        lvl[y] = dict(mean_vf=round(float(np.nanmean(vfy)), 1), mean_atr=round(float(np.nanmean(atr)), 1),
                      mean_price=round(float(d4["Close"].mean()), 0))
    ref_vf, ref_atr = lvl["2025"]["mean_vf"], lvl["2025"]["mean_atr"]
    q1 = pd.DataFrame([dict(year=y, **lvl[y],
                            vol_implied_scale=round(lvl[y]["mean_vf"] / ref_vf, 2),
                            atr_implied_scale=round(lvl[y]["mean_atr"] / ref_atr, 2),
                            optimum_scale=best[y]) for y in YEARS])
    q1.to_csv(RES / "cross_year_q1_recovery.csv", index=False)

    # 3) q2 compare: fixed(1.0) vs vol_scaled(ATR ratio) vs oracle(best)
    q2rows = []; tot = {"fixed": [0, 0], "vol_scaled": [0, 0], "oracle": [0, 0]}
    atr_sc = {y: float(q1[q1.year == y]["atr_implied_scale"].iloc[0]) for y in YEARS}
    for y in YEARS:
        f = run(df4, df1, vf, box, n, y, 1.0)
        v = run(df4, df1, vf, box, n, y, atr_sc[y])
        o = run(df4, df1, vf, box, n, y, best[y])
        q2rows.append(dict(year=y, fixed_pnl=f["pnl"], fixed_dd=f["dd"],
                           vol_scaled_scale=atr_sc[y], vol_scaled_pnl=v["pnl"], vol_scaled_dd=v["dd"],
                           oracle_scale=best[y], oracle_pnl=o["pnl"], oracle_dd=o["dd"]))
        tot["fixed"][0] += f["pnl"]; tot["fixed"][1] = max(tot["fixed"][1], f["dd"])
        tot["vol_scaled"][0] += v["pnl"]; tot["vol_scaled"][1] = max(tot["vol_scaled"][1], v["dd"])
        tot["oracle"][0] += o["pnl"]; tot["oracle"][1] = max(tot["oracle"][1], o["dd"])
    q2rows.append(dict(year="TOTAL", fixed_pnl=tot["fixed"][0], fixed_dd=tot["fixed"][1],
                       vol_scaled_scale=None, vol_scaled_pnl=tot["vol_scaled"][0], vol_scaled_dd=tot["vol_scaled"][1],
                       oracle_scale=None, oracle_pnl=tot["oracle"][0], oracle_dd=tot["oracle"][1]))
    pd.DataFrame(q2rows).to_csv(RES / "cross_year_q2_compare.csv", index=False)

    print("wrote 3 CSVs to results/:")
    for f in ("cross_year_scale_sweep.csv", "cross_year_q1_recovery.csv", "cross_year_q2_compare.csv"):
        print("  ", f)
    print("\nbest scale/year:", best)
    print(q2rows[-1])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
