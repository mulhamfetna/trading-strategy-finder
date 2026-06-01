"""Phase G — backtest the HAR-RV volatility forecast through the CLONED engine.

ENGINE PROVENANCE: this uses ONLY the VERIFIED simple single-contract engine
(cloned from src/strategy/simple_strategy.py: Stage-1 entry + dual-SL/TP exit, 1 contract,
no ladder). The legacy/unverified 1-1-2 ladder/scaling engine is NOT used anywhere.

SINGLE-CONTRACT CONSTRAINT (user-locked): every backtest holds position size = 1 contract.
Therefore only the levers that preserve single-contract are run:
  S = adaptive SL/TP (moves stop distances; still 1 contract)
  G = regime gate    (trade or skip; 1 contract when trading)
The position-sizing lever (P) is EXCLUDED because scaling contract count violates the
single-contract constraint. Valid cells: baseline, S, G, S+G. Plus a 3-calibration deep-dive
on the S lever. Original engine is never touched (we use engine_clone/).

Causality: the per-bar HAR-RV forecast uses only past bars; gate normalisation uses only
2025 (train) statistics; SL/TP normalisation uses a causal expanding mean.
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
N_2025 = None  # filled at load


# ---------- data ----------
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


# ---------- causal HAR-RV forecast per 4h bar ----------
def har_rv_forecast(df4: pd.DataFrame) -> np.ndarray:
    """Per-bar causal HAR forecast of realized vol (points), from outputs/realized_vol_4h.csv."""
    rvdf = pd.read_csv(ROOT / "outputs" / "realized_vol_4h.csv")
    rvdf["datetime"] = pd.to_datetime(rvdf["datetime"])
    rv = rvdf.set_index("datetime")["rv_pts"].reindex(df4["Date"].values).to_numpy(float)
    # fill any gaps with forward value
    rv = pd.Series(rv).ffill().bfill().to_numpy()
    n = len(rv)
    vf = np.full(n, np.nan)
    for i in range(n):
        if i < 30:
            continue
        vf[i] = 0.5 * rv[i - 1] + 0.3 * rv[i - 6:i].mean() + 0.2 * rv[i - 30:i].mean()
    # neutral fill for warmup
    med = np.nanmedian(vf)
    vf = np.where(np.isfinite(vf), vf, med)
    return vf


# ---------- levers ----------
def lever_sl_tp(vf, mode="expanding", v_ref=None, k=1.0):
    """Per-bar SL/TP multiplier. mode: 'expanding' (calib A, causal same-avg-risk),
    'train' (calib B, frozen train mean), 'sweep' (calib C = B scaled by k)."""
    n = len(vf)
    if mode == "expanding":
        cummean = np.array([vf[: i + 1].mean() for i in range(n)])
        m = vf / np.clip(cummean, 1e-9, None)
    elif mode in ("train", "sweep"):
        m = vf / v_ref
        if mode == "sweep":
            m = k * m
    return np.clip(m, 0.25, 4.0)  # safety clamp


def lever_size(vf, v_ref):
    s = v_ref / np.clip(vf, 1e-9, None)
    return np.clip(s, 0.25, 4.0)


def lever_gate(vf, thresh):
    return vf <= thresh


# ---------- run one config ----------
def run_cfg(df4, df1, box, sl_tp_mult=None, entry_gate=None, size=None):
    p = SimpleStrategyParams(sl_soft_points=80.0, sl_hard_points=100.0, tp_soft_points=50.0,
                             tp_hard_points=50.0, data_path_4h="", data_path_1min="",
                             box_data_path="", flip_entry_direction=False)
    trades, _ = SimpleStrategy(p).backtest(df4, df1, box, sl_tp_mult=sl_tp_mult, entry_gate=entry_gate)
    closed = [t for t in trades if t.get("exit_reason") not in (None, "OPEN")]
    if not closed:
        return dict(pnl=0.0, n=0, win=0.0, dd=0.0, sharpe=0.0, ppt=0.0)
    pnl_pts = np.array([float(t["pnl_points"]) for t in closed])
    if size is not None:
        sz = np.array([float(size[int(t["entry_idx"])]) for t in closed])
        pnl_pts = pnl_pts * sz
    pnl_d = pnl_pts * NQ_PV
    eq = np.cumsum(pnl_d)
    dd = float((np.maximum.accumulate(eq) - eq).max())
    return dict(pnl=float(pnl_d.sum()), n=len(closed),
                win=float((pnl_pts > 0).mean() * 100),
                dd=dd, sharpe=float(pnl_pts.mean() / (pnl_pts.std() + 1e-9)),
                ppt=float(pnl_d.sum() / len(closed)))


def main():
    df4, df1, box = load_all()
    n2025 = int((df4["_year"] == 2025).sum())
    vf = har_rv_forecast(df4)
    v_ref = float(vf[:n2025].mean())
    gate_thr = float(np.percentile(vf[:n2025], 80))

    S = lever_sl_tp(vf, mode="expanding")
    G = lever_gate(vf, gate_thr)

    # SINGLE-CONTRACT ONLY: sizing lever (P) excluded — it would change contract count.
    combos = {
        "0_baseline":  dict(),
        "1_S":         dict(sl_tp_mult=S),
        "2_G":         dict(entry_gate=G),
        "3_S+G":       dict(sl_tp_mult=S, entry_gate=G),
    }
    rows = []
    base = None
    for name, kw in combos.items():
        r = run_cfg(df4, df1, box, **kw)
        if name == "0_baseline":
            base = r["pnl"]
        r["combo"] = name
        r["vs_base_%"] = (r["pnl"] - base) / abs(base) * 100 if base else 0.0
        rows.append(r)
        print(f"{name:<12} pnl=${r['pnl']:>10,.0f}  vs_base={r['vs_base_%']:+6.1f}%  "
              f"n={r['n']:>4}  win={r['win']:4.1f}%  dd=${r['dd']:>9,.0f}  sharpe={r['sharpe']:+.3f}")
    pd.DataFrame(rows)[["combo", "pnl", "vs_base_%", "n", "win", "dd", "sharpe", "ppt"]].to_csv(
        ROOT / "outputs" / "backtest_matrix.csv", index=False)

    # ---- 3-calibration deep-dive on S lever ----
    print("\n=== Calibration deep-dive (S = adaptive SL/TP only) ===")
    calib_rows = []
    cfgs = [("A_expanding_normalize", lever_sl_tp(vf, mode="expanding")),
            ("B_train_frozen",        lever_sl_tp(vf, mode="train", v_ref=v_ref))]
    for k in (0.5, 1.0, 1.5, 2.0):
        cfgs.append((f"C_sweep_k={k}", lever_sl_tp(vf, mode="sweep", v_ref=v_ref, k=k)))
    for name, mult in cfgs:
        r = run_cfg(df4, df1, box, sl_tp_mult=mult)
        r["calib"] = name; r["vs_base_%"] = (r["pnl"] - base) / abs(base) * 100
        calib_rows.append(r)
        print(f"{name:<22} pnl=${r['pnl']:>10,.0f}  vs_base={r['vs_base_%']:+6.1f}%  "
              f"n={r['n']:>4}  win={r['win']:4.1f}%  dd=${r['dd']:>9,.0f}")
    pd.DataFrame(calib_rows)[["calib", "pnl", "vs_base_%", "n", "win", "dd", "sharpe"]].to_csv(
        ROOT / "outputs" / "calibration_sweep.csv", index=False)

    print(f"\nbaseline P/L = ${base:,.0f}  (2025+2026, 1 contract, manual params)")


if __name__ == "__main__":
    main()
