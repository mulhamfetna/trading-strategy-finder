"""Phase F2 — realized volatility from 1-minute data.

Computes per-4h-bar realized volatility RV = sqrt(sum of squared 1-min log-returns) — a far more
accurate volatility measure than the high-low range proxy used in F1. Then forecasts RV with the
same model family (naive / EWMA / HAR-RV) walk-forward on 2026, and compares to F1's range result.

Raw 1-min data is read READ-ONLY from data/ (not copied — 28MB). The small derived per-4h-bar RV
series is saved into the subproject (outputs/realized_vol_4h.csv) for self-containment.
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.common.data import load_4h_csv, train_eval_split

warnings.filterwarnings("ignore")

DATA = Path("/mnt/data/projects/trading/data")
MIN_FILES = [DATA / "2025_data" / "NQ_1m_2025.csv", DATA / "2026_data" / "NQ_1m_2026.csv"]


# ----- metrics (same as F1) --------------------------------------------------
def rmse(a, p): a, p = np.asarray(a, float), np.asarray(p, float); return float(np.sqrt(np.mean((a - p) ** 2)))
def mae(a, p):  a, p = np.asarray(a, float), np.asarray(p, float); return float(np.mean(np.abs(a - p)))
def corr(a, p): return float(np.corrcoef(a, p)[0, 1])
def qlike(actual, pred):
    a = np.asarray(actual, float) ** 2; p = np.clip(np.asarray(pred, float) ** 2, 1e-12, None)
    r = a / p; return float(np.mean(r - np.log(np.clip(r, 1e-12, None)) - 1))


def compute_rv() -> pd.DataFrame:
    """Per-4h-bar realized volatility in POINTS (so it's comparable to range)."""
    bars4h = load_4h_csv(ROOT / "NQ_4h.csv")
    mins = pd.concat([pd.read_csv(f) for f in MIN_FILES], ignore_index=True)
    mins["datetime"] = pd.to_datetime(mins["datetime"]); mins = mins.sort_values("datetime").reset_index(drop=True)
    mins["lr"] = np.log(mins["close"] / mins["close"].shift(1))

    starts = bars4h["datetime"].to_numpy()
    rv_pts = np.full(len(bars4h), np.nan)
    mt = mins["datetime"].to_numpy()
    for i, T in enumerate(starts):
        end = T + np.timedelta64(4, "h")
        seg = mins["lr"].to_numpy()[(mt >= T) & (mt < end)]
        seg = seg[~np.isnan(seg)]
        if len(seg) > 1:
            # realized variance -> realized vol as a fraction -> convert to points via bar price
            rv_frac = np.sqrt(np.sum(seg ** 2))
            rv_pts[i] = rv_frac * bars4h["close"].iloc[i]
    bars4h["rv_pts"] = rv_pts
    bars4h["range_pts"] = bars4h["high"] - bars4h["low"]
    return bars4h


def run_models(train, evalp, col):
    tr = train[col].to_numpy(float); ev = evalp[col].to_numpy(float)
    hist = list(tr[~np.isnan(tr)]); n = len(ev)
    preds = {k: np.empty(n) for k in ["naive", "ewma", "har"]}
    lam = 0.94; ewma = np.nanmean(tr[-50:])
    for v in tr[~np.isnan(tr)]: ewma = lam * ewma + (1 - lam) * v
    for i in range(n):
        h = np.array(hist)
        preds["naive"][i] = h[-1]
        preds["ewma"][i] = ewma
        preds["har"][i] = 0.5 * h[-1] + 0.3 * h[-6:].mean() + 0.2 * h[-30:].mean()
        realised = ev[i]
        if np.isfinite(realised):
            hist.append(realised); ewma = lam * ewma + (1 - lam) * realised
        else:
            hist.append(h[-1])
    return ev, preds


def main() -> None:
    df = compute_rv()
    df[["datetime", "rv_pts", "range_pts"]].to_csv(ROOT / "outputs" / "realized_vol_4h.csv", index=False)
    print(f"computed realized vol for {df['rv_pts'].notna().sum()}/{len(df)} bars")
    print(f"mean RV: {df['rv_pts'].mean():.1f} pts   mean range: {df['range_pts'].mean():.1f} pts")

    # autocorrelation of RV (expect high)
    rv = df["rv_pts"].dropna().to_numpy(); rvc = rv - rv.mean()
    acf1 = np.sum(rvc[:-1] * rvc[1:]) / np.sum(rvc ** 2)
    print(f"RV lag-1 autocorrelation: {acf1:.3f}")

    # split & forecast RV
    cut = load_4h_csv(ROOT / "NQ_4h_2025.csv")["datetime"].max()
    train = df[df["datetime"] <= cut].reset_index(drop=True)
    evalp = df[df["datetime"] > cut].reset_index(drop=True)
    actual, preds = run_models(train, evalp, "rv_pts")

    mask = np.isfinite(actual)
    rmse_naive = rmse(actual[mask], preds["naive"][mask])
    rows = []
    for k, p in preds.items():
        rows.append({"model": f"rv-{k}", "rmse_pts": rmse(actual[mask], p[mask]),
                     "mae_pts": mae(actual[mask], p[mask]),
                     "lift_vs_naive_%": (rmse_naive - rmse(actual[mask], p[mask])) / rmse_naive * 100,
                     "qlike": qlike(actual[mask], p[mask]), "corr": corr(actual[mask], p[mask])})
    lb = pd.DataFrame(rows).sort_values("rmse_pts")
    lb.to_csv(ROOT / "outputs" / "rv_leaderboard.csv", index=False)
    out = pd.DataFrame({"datetime": evalp["datetime"], "actual_rv": actual,
                        **{f"pred_{k}": v for k, v in preds.items()}})
    out.to_csv(ROOT / "outputs" / "16_rv_forecast.csv", index=False)
    print("\n=== REALIZED-VOL FORECAST LEADERBOARD (2026 walk-forward) ===")
    print(lb.to_string(index=False))


if __name__ == "__main__":
    main()
