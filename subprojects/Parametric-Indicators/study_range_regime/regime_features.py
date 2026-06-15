"""Phase S1 — CAUSAL price-range regime features, one row per 4h decision bar.

For each bar t and each timeframe TF ∈ {month, quarter, year}, using ONLY data up to & INCLUDING t:
  • running current-period box  = [min(Low) .. t, max(High) .. t]   (causal cummin/cummax within the period)
  • completed prior-period boxes = full [min Low, max High] of every period that CLOSED before the current one
  • merge margin (Q2a) = pct · Close_t  (% of price); the resolved points are LOGGED per row as `<tf>_margin_pts`
  • new/repeat (Q2 d): NEW_HIGH if running high > (prior max top + margin); NEW_LOW if running low <
    (prior min bottom − margin); else REPEAT (we are inside known territory)
  • trend (Q3 look-back): of the COMPLETED prior periods, was the most recent extreme a LOW (→ rising →
    LOW_TREND) or a HIGH (→ falling → HIGH_TREND)? else NEUTRAL.  Confirmed by current price vs that extreme.

No look-ahead: every value at row t uses only rows ≤ t (completed periods + the running current period).
A *retrospective* full-period view is a SEPARATE module (regime_charts.py, insight-only). Emits one CSV.

Usage:  python3 study_range_regime/regime_features.py [--pct 0.05] [--tf 4h] [--out <csv>]
"""
from __future__ import annotations
import sys, argparse
from pathlib import Path
import numpy as np
import pandas as pd

_PI = Path(__file__).resolve().parents[1]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))
import strategy  # noqa: E402

HERE = Path(__file__).resolve().parent


def _period_labels(dt: pd.Series):
    """Return month / quarter / year string labels (calendar)."""
    d = pd.to_datetime(dt)
    month = d.dt.strftime("%Y-%m")
    quarter = d.dt.year.astype(str) + "-Q" + ((d.dt.month - 1) // 3 + 1).astype(str)
    year = d.dt.year.astype(str)
    return month, quarter, year


def _tf_features(df: pd.DataFrame, label: pd.Series, pct: float, tag: str) -> pd.DataFrame:
    """Causal regime features for one period granularity (label = per-bar period id)."""
    high = df["High"].to_numpy(float); low = df["Low"].to_numpy(float); close = df["Close"].to_numpy(float)
    g = pd.DataFrame({"lab": label.to_numpy(), "High": high, "Low": low})
    # running current-period extremes (causal: cummax/cummin within the period, up to current row)
    rc_hi = g.groupby("lab")["High"].cummax().to_numpy(float)
    rc_lo = g.groupby("lab")["Low"].cummin().to_numpy(float)

    # period order + full (retrospective, period-level) boxes — used only for completed-period logic
    order = list(dict.fromkeys(label.tolist()))                       # chronological unique periods
    pg = g.groupby("lab").agg(phi=("High", "max"), plo=("Low", "min")).reindex(order)
    phi = pg["phi"].to_numpy(float); plo = pg["plo"].to_numpy(float)
    # prior (strictly-before) running extremes across COMPLETED periods
    prior_top = pd.Series(phi).cummax().shift(1).to_numpy(float)      # max high of periods before period i
    prior_bot = pd.Series(plo).cummin().shift(1).to_numpy(float)      # min low of periods before period i
    nh_period = phi > np.where(np.isnan(prior_top), -np.inf, prior_top)   # period i set a NEW HIGH
    nl_period = plo < np.where(np.isnan(prior_bot), np.inf, prior_bot)    # period i set a NEW LOW
    # most-recent completed new-high / new-low period index (strictly before period i)
    last_nh = np.full(len(order), -1); last_nl = np.full(len(order), -1)
    seen_nh = seen_nl = -1
    for i in range(len(order)):
        last_nh[i] = seen_nh; last_nl[i] = seen_nl          # "as of the START of period i" = excludes i
        if nh_period[i]: seen_nh = i
        if nl_period[i]: seen_nl = i
    pidx = {p: i for i, p in enumerate(order)}

    # map period-level series back to bars
    bi = label.map(pidx).to_numpy(int)
    b_prior_top = prior_top[bi]; b_prior_bot = prior_bot[bi]
    b_last_nh = last_nh[bi]; b_last_nl = last_nl[bi]
    margin = pct * close

    # ---- new / repeat (causal: running box vs prior completed territory) ----
    newrep = np.full(len(df), "REPEAT", dtype=object)
    is_new_hi = (~np.isnan(b_prior_top)) & (rc_hi > b_prior_top + margin)
    is_new_lo = (~np.isnan(b_prior_bot)) & (rc_lo < b_prior_bot - margin)
    newrep[is_new_hi] = "NEW_HIGH"
    newrep[is_new_lo & ~is_new_hi] = "NEW_LOW"

    # ---- trend (look-back over completed periods) ----
    trend = np.full(len(df), "NEUTRAL", dtype=object)
    ref_low = np.where(b_last_nl >= 0, plo[np.clip(b_last_nl, 0, len(plo) - 1)], np.nan)
    ref_high = np.where(b_last_nh >= 0, phi[np.clip(b_last_nh, 0, len(phi) - 1)], np.nan)
    low_more_recent = (b_last_nl > b_last_nh) & (b_last_nl >= 0)
    high_more_recent = (b_last_nh > b_last_nl) & (b_last_nh >= 0)
    trend[low_more_recent & (close > ref_low)] = "LOW_TREND"      # bottomed then rising
    trend[high_more_recent & (close < ref_high)] = "HIGH_TREND"   # topped then falling

    return pd.DataFrame({
        f"{tag}_period": label.to_numpy(),
        f"{tag}_run_lo": np.round(rc_lo, 1), f"{tag}_run_hi": np.round(rc_hi, 1),
        f"{tag}_margin_pts": np.round(margin, 1),
        f"{tag}_newrepeat": newrep, f"{tag}_trend": trend,
    })


def build(df: pd.DataFrame, pct: float) -> pd.DataFrame:
    month, quarter, year = _period_labels(df["Date"])
    out = pd.DataFrame({"Date": pd.to_datetime(df["Date"]).values, "Close": np.round(df["Close"].to_numpy(float), 1)})
    for lab, tag in ((month, "M"), (quarter, "Q"), (year, "Y")):
        out = pd.concat([out, _tf_features(df, lab, pct, tag)], axis=1)
    # 3-TF intersection: do the trend labels agree?
    tr = out[["M_trend", "Q_trend", "Y_trend"]]
    out["trend_agree3"] = (tr.nunique(axis=1) == 1) & (out["M_trend"] != "NEUTRAL")
    out["trend_agree_MQ"] = (out["M_trend"] == out["Q_trend"]) & (out["M_trend"] != "NEUTRAL")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pct", type=float, default=0.05, help="merge margin as a fraction of price (Q2a)")
    ap.add_argument("--tf", default="4h", help="decision timeframe to load")
    ap.add_argument("--out", default=str(HERE / "results" / "regime_features.csv"))
    a = ap.parse_args()
    df4, df1, box, vf, n = strategy.get_bundle(a.tf)
    feat = build(df4, a.pct)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    feat.to_csv(a.out, index=False)
    print(f"rows: {len(feat)}  span {feat['Date'].iloc[0].date()} … {feat['Date'].iloc[-1].date()}  pct={a.pct}")
    for tag in ("M", "Q", "Y"):
        nr = feat[f"{tag}_newrepeat"].value_counts().to_dict()
        tr = feat[f"{tag}_trend"].value_counts().to_dict()
        print(f"  {tag}: new/repeat={nr}  trend={tr}")
    print(f"  trend_agree3={int(feat['trend_agree3'].sum())}  trend_agree_MQ={int(feat['trend_agree_MQ'].sum())}")
    print(f"  margin_pts (M) median={feat['M_margin_pts'].median():.0f}  -> wrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
