"""Phase S2 (Q2) — RETROSPECTIVE regime/structure charts (insight-only, NOT tradeable).

Renders the registry + structure tables as pictures over 2024–2026 (4h close):
  results/chart_regime_ribbon.png  — price + per-month TREND ribbon (HIGH/LOW/NEUTRAL) + NEW_HIGH markers
                                       + the cumulative all-time high/low envelope
  results/chart_structure_swings.png — price + labeled swing pivots (HH/HL green · LH/LL red), swing_l=3
  results/chart_period_bands.png    — price + monthly range BANDS (merged-band id colour)

These are descriptive (full-period view); the causal per-bar features that feed trades live in
regime_features.py. Reads the CSVs produced by range_registry.py + structure_tables.py.

Usage:  python3 study_range_regime/regime_charts.py
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                            # noqa: E402
from matplotlib.patches import Patch                       # noqa: E402

_PI = Path(__file__).resolve().parents[1]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))
from optimize.sub.data_2024_2026 import load_bundle        # noqa: E402

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
TREND_COLOR = {"HIGH_TREND": "#1a9850", "LOW_TREND": "#d73027", "NEUTRAL": "#bdbdbd"}


def _price():
    df4, _df1, _box, _vf, _m = load_bundle()
    return pd.to_datetime(df4["Date"]), df4["Close"].to_numpy(float)


def chart_regime_ribbon(dt, close):
    reg = pd.read_csv(RES / "registry_month.csv", parse_dates=["low_time", "high_time"])
    reg["start"] = pd.to_datetime(reg["period"] + "-01")
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(dt, close, lw=0.8, color="#222", label="NQ close (4h)")
    # per-month trend ribbon as background spans
    months = reg.sort_values("start").reset_index(drop=True)
    for i, r in months.iterrows():
        x0 = r["start"]
        x1 = months["start"].iloc[i + 1] if i + 1 < len(months) else dt.iloc[-1]
        ax.axvspan(x0, x1, color=TREND_COLOR.get(r["trend"], "#bdbdbd"), alpha=0.18, lw=0)
    # cumulative all-time high/low envelope (the new/repeat anchor)
    ax.plot(dt, pd.Series(close).cummax(), color="#1a9850", lw=0.7, ls="--", alpha=0.6, label="all-time high")
    ax.plot(dt, pd.Series(close).cummin(), color="#d73027", lw=0.7, ls="--", alpha=0.6, label="all-time low")
    nh = reg[reg["signal"] == "NEW_HIGH"]
    ax.scatter(nh["high_time"], nh["high"], marker="^", color="#1a9850", s=70, zorder=5, label="NEW_HIGH (record)")
    handles = [Patch(color=TREND_COLOR[k], alpha=0.3, label=k) for k in TREND_COLOR]
    ax.legend(handles=handles + ax.get_legend_handles_labels()[0], loc="upper left", fontsize=8)
    ax.set_title("Regime ribbon — monthly TREND (relative HH/LL) + NEW_HIGH records · 2024–2026 (retrospective)")
    ax.set_ylabel("price"); fig.tight_layout(); fig.savefig(RES / "chart_regime_ribbon.png", dpi=110)
    plt.close(fig)


def chart_structure_swings(dt, close):
    sw = pd.read_csv(RES / "structure_swings_l3.csv", parse_dates=["pivot_time"])
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(dt, close, lw=0.7, color="#888", label="NQ close (4h)")
    palette = {"HH": "#1a9850", "HL": "#66bd63", "LH": "#f46d43", "LL": "#d73027", "FIRST": "#999"}
    for lab, col in palette.items():
        s = sw[sw["label"] == lab]
        ax.scatter(s["pivot_time"], s["pivot_price"], s=22, color=col, label=f"{lab} ({len(s)})", zorder=4)
    ax.legend(loc="upper left", fontsize=8, ncol=2)
    ax.set_title("Market structure — labeled swing pivots (close-based, swing_l=3) · 2024–2026")
    ax.set_ylabel("price"); fig.tight_layout(); fig.savefig(RES / "chart_structure_swings.png", dpi=110)
    plt.close(fig)


def chart_period_bands(dt, close):
    reg = pd.read_csv(RES / "registry_month.csv")
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(dt, close, lw=0.8, color="#222", label="NQ close (4h)")
    cmap = plt.get_cmap("tab10")
    for _, r in reg.iterrows():
        x0 = pd.to_datetime(r["period"] + "-01")
        x1 = x0 + pd.offsets.MonthEnd(1)
        ax.add_patch(plt.Rectangle((x0, r["low"]), x1 - x0, r["high"] - r["low"],
                                   color=cmap(int(r["band_id"]) % 10), alpha=0.22, lw=0))
    ax.set_title("Monthly range bands (merged-band colour; repeats reuse a colour) · 2024–2026")
    ax.set_ylabel("price"); ax.legend(loc="upper left", fontsize=8)
    fig.tight_layout(); fig.savefig(RES / "chart_period_bands.png", dpi=110); plt.close(fig)


def main() -> int:
    RES.mkdir(parents=True, exist_ok=True)
    dt, close = _price()
    chart_regime_ribbon(dt, close)
    chart_structure_swings(dt, close)
    chart_period_bands(dt, close)
    print("wrote chart_regime_ribbon.png, chart_structure_swings.png, chart_period_bands.png to", RES)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
