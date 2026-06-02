"""Workstream G — combination tournament on the CLONED single-contract engine.

Crosses two independent decision axes, all at 1 contract, on the VERIFIED clone
(engine_clone/, never the main engine; never the 1-1-2 ladder):

  ENTRY MODE  x  VOL LEVER
  ----------     ---------
  normal         none   (mult=1, no gate)
  flipped        S      (HAR-RV adaptive SL/TP multiplier, causal expanding-normalised)
  cusum_flip     G      (HAR-RV vol gate: skip the top-20%-vol bars)
                 S+G

= 3 x 4 = 12 combinations. The HAR-RV forecast is the Workstream-A/Phase-F winner
(outputs/realized_vol_4h.csv); the CUSUM flip detector is notes/32 (k=20, h=400).

Efficiency + correctness: for each VOL LEVER we run the engine ONCE normal and ONCE flipped
(8 runs), match trades by entry_idx, and derive the three entry modes from those two streams
(cusum_flip picks normal- or flipped-pnl per trade by the causal CUSUM decision). We also
assert the flip symmetry (flipped_pnl ~= -normal_pnl) and report the max deviation.

HONESTY: there is still only ONE regime change in the data (n=1). Any flip result — including
CUSUM — is fitted to that single event and is ILLUSTRATIVE, not validated. Trust the mechanism
and the risk-reduction, not the specific dollar figure.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJ = Path("/mnt/data/projects/trading")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJ)); sys.path.insert(0, str(ROOT))

from src.data.loader import load_data
from engine_clone.simple_strategy_adaptive import SimpleStrategy, SimpleStrategyParams

NQ_PV = 20.0
CUSUM_K, CUSUM_H = 20.0, 400.0


def load_all():
    f4, f1, fb = [], [], []
    for year in (2025, 2026):
        d = PROJ / "data" / f"{year}_data"
        a = load_data(str(d / f"NQ_4h_{year}.csv")); a["_year"] = year
        b = load_data(str(d / f"NQ_1m_{year}.csv"))
        c = pd.read_csv(d / f"NQ_full_data_{year}.csv"); c["Date"] = pd.to_datetime(c["Date"]).dt.normalize()
        f4.append(a); f1.append(b); fb.append(c)
    df4 = pd.concat(f4).sort_values("Date").reset_index(drop=True)
    df1 = pd.concat(f1).sort_values("Date").reset_index(drop=True)
    box = pd.concat(fb).drop_duplicates(subset=["Date"]).set_index("Date", drop=False)
    return df4, df1, box


def har_rv_forecast(df4):
    rvdf = pd.read_csv(ROOT / "outputs" / "realized_vol_4h.csv")
    rvdf["datetime"] = pd.to_datetime(rvdf["datetime"])
    rv = rvdf.set_index("datetime")["rv_pts"].reindex(df4["Date"].values).to_numpy(float)
    rv = pd.Series(rv).ffill().bfill().to_numpy()
    n = len(rv); vf = np.full(n, np.nan)
    for i in range(n):
        if i >= 30:
            vf[i] = 0.5 * rv[i - 1] + 0.3 * rv[i - 6:i].mean() + 0.2 * rv[i - 30:i].mean()
    return np.where(np.isfinite(vf), vf, np.nanmedian(vf))


def lever_sl_tp(vf):
    n = len(vf); cummean = np.array([vf[: i + 1].mean() for i in range(n)])
    return np.clip(vf / np.clip(cummean, 1e-9, None), 0.25, 4.0)


def rule_cusum(pnl, k=CUSUM_K, h=CUSUM_H):
    n = len(pnl); mode = np.ones(n); prev = 1; s_hi = s_lo = 0.0
    for i in range(n):
        mode[i] = prev; x = pnl[i]
        s_hi = max(0.0, s_hi + x - k); s_lo = max(0.0, s_lo - x - k)
        if s_lo > h: prev = -1; s_hi = s_lo = 0.0
        elif s_hi > h: prev = 1; s_hi = s_lo = 0.0
    return mode


def run(df4, df1, box, flip, sl_tp_mult=None, entry_gate=None):
    p = SimpleStrategyParams(sl_soft_points=80.0, sl_hard_points=100.0, tp_soft_points=50.0,
                             tp_hard_points=50.0, data_path_4h="", data_path_1min="",
                             box_data_path="", flip_entry_direction=flip)
    trades, _ = SimpleStrategy(p).backtest(df4, df1, box, sl_tp_mult=sl_tp_mult, entry_gate=entry_gate)
    rows = [(int(t["entry_idx"]), float(t["pnl_points"]), pd.Timestamp(t["exit_time"]).year)
            for t in trades if t.get("exit_reason") not in (None, "OPEN")]
    return pd.DataFrame(rows, columns=["entry_idx", "pnl_pts", "year"])


def metrics(pnl_pts, year):
    pnl_d = pnl_pts * NQ_PV
    eq = np.cumsum(pnl_d)
    dd = float((np.maximum.accumulate(eq) - eq).max()) if len(eq) else 0.0
    return dict(pnl=float(pnl_d.sum()),
                pnl_2025=float(pnl_d[year == 2025].sum()),
                pnl_2026=float(pnl_d[year == 2026].sum()),
                n=int(len(pnl_pts)), win=float((pnl_pts > 0).mean() * 100) if len(pnl_pts) else 0.0,
                dd=dd)


def main():
    df4, df1, box = load_all()
    vf = har_rv_forecast(df4)
    S = lever_sl_tp(vf)
    G = vf <= np.percentile(vf[: int((df4["_year"] == 2025).sum())], 80)

    vol_levers = {"none": dict(), "S": dict(sl_tp_mult=S),
                  "G": dict(entry_gate=G), "S+G": dict(sl_tp_mult=S, entry_gate=G)}

    rows = []
    sym_devs = []
    for lev, kw in vol_levers.items():
        nrm = run(df4, df1, box, flip=False, **kw)   # FULL normal stream
        flp = run(df4, df1, box, flip=True, **kw)     # FULL flipped stream
        # normal / flipped metrics on their OWN full streams (no lossy merge)
        rn = metrics(nrm["pnl_pts"].to_numpy(), nrm["year"].to_numpy())
        rf = metrics(flp["pnl_pts"].to_numpy(), flp["year"].to_numpy())
        # cusum_flip: causal per-trade choice over the normal stream order; when the CUSUM
        # says "flip", use the matched flipped-trade pnl (by entry_idx) if it exists, else
        # fall back to -normal. Symmetry is NOT assumed (we measure how far off it is).
        flp_by_idx = dict(zip(flp["entry_idx"], flp["pnl_pts"]))
        pn = nrm["pnl_pts"].to_numpy(); yr = nrm["year"].to_numpy(); eidx = nrm["entry_idx"].to_numpy()
        mode = rule_cusum(pn)
        matched = np.array([flp_by_idx.get(int(e), np.nan) for e in eidx])
        sym_devs.append(np.nanmax(np.abs(matched - (-pn))) if np.isfinite(matched).any() else np.nan)
        pc = np.where(mode > 0, pn, np.where(np.isfinite(matched), matched, -pn))
        rc = metrics(pc, yr)
        for em, r in (("normal", rn), ("flipped", rf), ("cusum_flip", rc)):
            r["entry_mode"] = em; r["vol_lever"] = lev; r["combo"] = f"{em}+{lev}"; rows.append(r)
    sym_dev = float(np.nanmax(sym_devs))

    out = pd.DataFrame(rows).sort_values("pnl", ascending=False).reset_index(drop=True)
    base = out.loc[out.combo == "normal+none", "pnl"].iloc[0]
    out["vs_base_%"] = (out["pnl"] - base) / abs(base) * 100
    cols = ["combo", "pnl", "pnl_2025", "pnl_2026", "vs_base_%", "n", "win", "dd"]
    out[cols].to_csv(ROOT / "outputs" / "wsg_combination_tournament.csv", index=False)

    pd.set_option("display.width", 140)
    print(f"flip-symmetry max per-trade deviation: {sym_dev:.4f} pts (expect ~0)\n")
    print("WS-G COMBINATION TOURNAMENT (single contract, cloned engine):")
    print(out[cols].to_string(index=False, float_format=lambda v: f"{v:,.0f}"))
    print(f"\nbaseline (normal+none) = ${base:,.0f}   [n=1 regime: flip rows ILLUSTRATIVE]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
