"""Phase S1b — PRICE-RANGE REGISTRY (the literal point-1 / point-2 deliverable).

Delivers the user's original spec, points 1–3, as explicit registry TABLES (not per-bar features):

  1. For each MONTH, QUARTER and YEAR across 2024/2025/2026: register the highest price point and the
     lowest price point (true intrabar extremes from 1-MINUTE data) + the time each extreme occurred.
  2. Assign a NEW/REPEAT signal to each period's range:
       a. merge tolerance `margin = pct · price` (Q2a-approved % basis; logged per period in points).
          A period's box merges into an existing BAND iff |top−band_top| ≤ margin AND |bottom−band_bottom|
          ≤ margin → union (bigger swallows smaller); it is a REPEAT of that band.
       b. a box farther than the margin = a DIFFERENT band (NEW).
       c. each band is counted once on first appearance, then its `repeat_count` grows as later (non-
          contiguous) periods land in it.
       d. NEW_HIGH = this period's high broke above ALL prior territory (+margin); NEW_LOW = symmetric.
  3. TREND per period (relative period-over-period structure — user rule 2026-06-15):
     HIGH_TREND ⇐ a HIGHER HIGH than the prior period (HH); LOW_TREND ⇐ a LOWER LOW (LL);
     outside bar (both) / inside bar (neither) → NEUTRAL. Independent of the new/repeat signal,
     which stays anchored to the cumulative ALL-TIME record (a new lowest/highest ever since watching).

This is descriptive/insight (retrospective period boxes). The CAUSAL per-decision-bar version that actually
feeds the trade rule lives in `regime_features.py`. Both share the same definitions.

Emits results/registry_{month,quarter,year}.csv + results/band_registry_{month,quarter,year}.csv and prints
markdown tables for the study doc.

Usage:  python3 study_range_regime/range_registry.py [--pct 0.05]
"""
from __future__ import annotations
import sys, argparse
from pathlib import Path
import numpy as np
import pandas as pd

_PI = Path(__file__).resolve().parents[1]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))
from optimize.sub.data_2024_2026 import load_bundle   # noqa: E402  (full 2024–2026 span)

HERE = Path(__file__).resolve().parent
RES = HERE / "results"


def _labels(dt: pd.Series):
    d = pd.to_datetime(dt)
    month = d.dt.strftime("%Y-%m")
    quarter = d.dt.year.astype(str) + "-Q" + ((d.dt.month - 1) // 3 + 1).astype(str)
    year = d.dt.year.astype(str)
    return {"month": month, "quarter": quarter, "year": year}


def _period_extremes(df1: pd.DataFrame, label: pd.Series) -> pd.DataFrame:
    """True high/low price points per period from 1-minute data, with the timestamp of each extreme."""
    g = pd.DataFrame({"lab": label.to_numpy(), "Date": pd.to_datetime(df1["Date"]).to_numpy(),
                      "High": df1["High"].to_numpy(float), "Low": df1["Low"].to_numpy(float),
                      "Close": df1["Close"].to_numpy(float)})
    order = list(dict.fromkeys(label.tolist()))                       # chronological unique periods
    rows = []
    for lab in order:
        sub = g[g.lab == lab]
        hi_i = sub["High"].idxmax(); lo_i = sub["Low"].idxmin()
        rows.append(dict(period=lab,
                         low=round(float(sub["Low"].min()), 2),
                         low_time=pd.Timestamp(g.loc[lo_i, "Date"]),
                         high=round(float(sub["High"].max()), 2),
                         high_time=pd.Timestamp(g.loc[hi_i, "Date"]),
                         mean_close=round(float(sub["Close"].mean()), 2)))
    out = pd.DataFrame(rows)
    out["range_pts"] = (out["high"] - out["low"]).round(2)
    return out


def _new_repeat_trend(reg: pd.DataFrame, pct: float):
    """Add margin_pts, NEW_HIGH/NEW_LOW (vs all prior territory), band_id + repeat_count, and look-back trend."""
    hi = reg["high"].to_numpy(float); lo = reg["low"].to_numpy(float); price = reg["mean_close"].to_numpy(float)
    margin = pct * price
    n = len(reg)

    # ---- NEW_HIGH / NEW_LOW vs ALL completed prior periods (+margin) ----
    prior_top = pd.Series(hi).cummax().shift(1).to_numpy(float)
    prior_bot = pd.Series(lo).cummin().shift(1).to_numpy(float)
    new_high = (~np.isnan(prior_top)) & (hi > prior_top + margin)
    new_low = (~np.isnan(prior_bot)) & (lo < prior_bot - margin)

    # ---- band identity (merge/swallow within margin; bigger swallows smaller) + repeat count ----
    bands = []                       # each: dict(bottom, top, count, first)
    band_id = np.full(n, -1, int); repeat_count = np.zeros(n, int)
    for i in range(n):
        m = margin[i]; placed = False
        for b in bands:
            if abs(hi[i] - b["top"]) <= m and abs(lo[i] - b["bottom"]) <= m:
                b["top"] = max(b["top"], hi[i]); b["bottom"] = min(b["bottom"], lo[i])   # union (swallow)
                b["count"] += 1
                band_id[i] = b["id"]; repeat_count[i] = b["count"]; placed = True
                break
        if not placed:
            b = dict(id=len(bands), bottom=lo[i], top=hi[i], count=1, first=i)
            bands.append(b); band_id[i] = b["id"]; repeat_count[i] = 1
    is_new_band = repeat_count == 1

    # ---- trend: RELATIVE period-over-period structure (user rule, 2026-06-15) ----
    # HIGH_TREND ⇐ this period made a HIGHER HIGH than the prior period (HH); LOW_TREND ⇐ a LOWER LOW (LL).
    # Outside bar (both HH and LL) or inside bar (neither) → NEUTRAL. period 0 has no prior → NEUTRAL.
    # NB: this is independent of the new/repeat signal, which stays anchored to the cumulative all-time record.
    trend = np.full(n, "NEUTRAL", dtype=object)
    prior_hi = np.r_[np.nan, hi[:-1]]; prior_lo = np.r_[np.nan, lo[:-1]]
    hh = hi > prior_hi          # higher high than the immediately-prior period
    ll = lo < prior_lo          # lower low than the immediately-prior period
    trend[hh & ~ll] = "HIGH_TREND"
    trend[ll & ~hh] = "LOW_TREND"

    reg = reg.copy()
    reg["margin_pts"] = np.round(margin, 1)
    reg["signal"] = np.where(new_high, "NEW_HIGH", np.where(new_low, "NEW_LOW",
                             np.where(is_new_band, "NEW_RANGE", "REPEAT")))
    reg["band_id"] = band_id
    reg["repeat_count"] = repeat_count
    reg["trend"] = trend
    return reg, bands


def _band_summary(reg: pd.DataFrame) -> pd.DataFrame:
    """Distinct bands with their final extent, repeat count, and the periods that landed in them (2c)."""
    rows = []
    for bid, sub in reg.groupby("band_id"):
        periods = sub["period"].tolist()
        rows.append(dict(band_id=int(bid), bottom=round(float(sub["low"].min()), 2),
                         top=round(float(sub["high"].max()), 2),
                         times_seen=len(periods), first_period=periods[0],
                         periods=";".join(periods)))
    return pd.DataFrame(rows).sort_values("band_id").reset_index(drop=True)


def _md(reg: pd.DataFrame, tag: str) -> str:
    cols = ["period", "low", "low_time", "high", "high_time", "range_pts", "margin_pts",
            "signal", "band_id", "repeat_count", "trend"]
    d = reg[cols].copy()
    d["low_time"] = pd.to_datetime(d["low_time"]).dt.strftime("%Y-%m-%d %H:%M")
    d["high_time"] = pd.to_datetime(d["high_time"]).dt.strftime("%Y-%m-%d %H:%M")
    head = "| " + " | ".join(cols) + " |"
    sep = "|" + "|".join(["---"] * len(cols)) + "|"
    lines = [head, sep]
    for _, r in d.iterrows():
        lines.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    return f"### {tag.capitalize()} registry\n" + "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pct", type=float, default=0.05, help="merge margin as fraction of price (Q2a)")
    a = ap.parse_args()
    RES.mkdir(parents=True, exist_ok=True)
    _df4, df1, _box, _vf, _months = load_bundle()
    labs = _labels(df1["Date"])

    md_blocks = []
    for tf in ("month", "quarter", "year"):
        reg = _period_extremes(df1, labs[tf])
        reg, _bands = _new_repeat_trend(reg, a.pct)
        reg.to_csv(RES / f"registry_{tf}.csv", index=False)
        bs = _band_summary(reg)
        bs.to_csv(RES / f"band_registry_{tf}.csv", index=False)
        md_blocks.append(_md(reg, tf))
        sig = reg["signal"].value_counts().to_dict()
        print(f"{tf}: {len(reg)} periods | bands={reg['band_id'].nunique()} | signals={sig}")

    (RES / "REGISTRY_TABLES.md").write_text(
        "# Price-range registry — high/low + new/repeat + trend per month/quarter/year (2024–2026)\n\n"
        f"Source: 1-minute true intrabar extremes (`optimize.sub.data_2024_2026.load_bundle`); "
        f"merge margin = {a.pct:.0%} of price (logged per period as `margin_pts`).\n\n"
        + "\n\n".join(md_blocks) + "\n")
    print(f"\nwrote registry_*.csv, band_registry_*.csv, REGISTRY_TABLES.md to {RES}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
