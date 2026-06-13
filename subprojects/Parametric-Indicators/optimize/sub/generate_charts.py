"""Generate the figures for the sub-optimizer study doc (STUDY_sub_optimizer.md).
Reads results/subopt_table.csv (Stage 1) + the Stage-2 OOS numbers (recorded constants). Writes PNGs to
results/charts/. Pure matplotlib (Agg)."""
from __future__ import annotations

import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

_HERE = Path(__file__).resolve().parent
# Env-overridable so the constrained run reuses the same script (default = original study):
#   SUBOPT_TABLE (input csv) · SUBOPT_CHARTDIR (output) · SUBOPT_OOS_{PNL,DD,DDPL} (4 csv vals: fixed,opt1,opt2,opt3)
_CH = Path(os.environ.get("SUBOPT_CHARTDIR", str(_HERE / "results" / "charts")))
_CH.mkdir(parents=True, exist_ok=True)
d = pd.read_csv(os.environ.get("SUBOPT_TABLE", str(_HERE / "results" / "subopt_table.csv")))
x = np.arange(len(d))
SL_C, TP_C = 149.8, 120.2  # champion base


def _r(a, b):
    m = np.isfinite(d[a]) & np.isfinite(d[b])
    return np.corrcoef(d[a][m], d[b][m])[0, 1]


# 1 — price growth
plt.figure(figsize=(10, 3.4))
plt.plot(x, d.price_mean, "-o", ms=3, color="#2962ff")
plt.xticks(x[::2], d.anchor[::2], rotation=60, fontsize=7)
plt.title("NQ price level per window (premise: the range widens over time)")
plt.ylabel("mean price"); plt.tight_layout(); plt.savefig(_CH / "01_price_growth.png", dpi=110); plt.close()

# 2 — best SL/TP time series
plt.figure(figsize=(10, 3.6))
plt.plot(x, d.best_sl_soft, "-o", ms=3, label="best sl_soft")
plt.plot(x, d.best_sl_hard, "-o", ms=3, label="best sl_hard")
plt.plot(x, d.best_tp, "-o", ms=3, label="best tp")
plt.axhline(SL_C, ls="--", c="grey", lw=.8); plt.axhline(TP_C, ls=":", c="grey", lw=.8)
plt.xticks(x[::2], d.anchor[::2], rotation=60, fontsize=7)
plt.title("Best SL/TP per window (noisy; dashed = champion sl_soft / tp)")
plt.ylabel("points"); plt.legend(fontsize=8); plt.tight_layout()
plt.savefig(_CH / "02_sltp_timeseries.png", dpi=110); plt.close()

# 3 — scatter vs price (sl_soft, tp) with fit + r
fig, ax = plt.subplots(1, 2, figsize=(10, 3.6))
for a, col, c in [(ax[0], "best_sl_soft", "#00897b"), (ax[1], "best_tp", "#e53935")]:
    a.scatter(d.price_mean, d[col], s=22, color=c)
    m, b = np.polyfit(d.price_mean, d[col], 1)
    xs = np.array([d.price_mean.min(), d.price_mean.max()]); a.plot(xs, m * xs + b, "k--", lw=1)
    a.set_title(f"{col} vs price   r={_r(col,'price_mean'):+.2f}"); a.set_xlabel("mean price"); a.set_ylabel("points")
fig.suptitle("No clean price relationship (weak r; tp even negative)"); plt.tight_layout()
plt.savefig(_CH / "03_scatter_vs_price.png", dpi=110); plt.close()

# 4 — scatter vs ATR
fig, ax = plt.subplots(1, 2, figsize=(10, 3.6))
for a, col, c in [(ax[0], "best_sl_soft", "#00897b"), (ax[1], "best_tp", "#e53935")]:
    a.scatter(d.atr_mean, d[col], s=22, color=c)
    a.set_title(f"{col} vs ATR   r={_r(col,'atr_mean'):+.2f}"); a.set_xlabel("ATR(14) mean"); a.set_ylabel("points")
fig.suptitle("Vs volatility (ATR): also weak"); plt.tight_layout()
plt.savefig(_CH / "04_scatter_vs_atr.png", dpi=110); plt.close()

# 5 — SL/TP as % of price
plt.figure(figsize=(10, 3.4))
plt.plot(x, d.sl_pct_of_price, "-o", ms=3, label=f"sl% (CV={d.sl_pct_of_price.std()/d.sl_pct_of_price.mean():.2f})")
plt.plot(x, d.tp_pct_of_price, "-o", ms=3, label=f"tp% (CV={d.tp_pct_of_price.std()/d.tp_pct_of_price.mean():.2f})")
plt.axhline(d.sl_pct_of_price.mean(), ls="--", c="#00897b", lw=.8); plt.axhline(d.tp_pct_of_price.mean(), ls="--", c="#e53935", lw=.8)
plt.xticks(x[::2], d.anchor[::2], rotation=60, fontsize=7)
plt.title("SL/TP as % of price — not a stable constant ratio either")
plt.ylabel("% of price"); plt.legend(fontsize=8); plt.tight_layout()
plt.savefig(_CH / "05_pct_of_price.png", dpi=110); plt.close()

# 6 — Stage-2 OOS comparison (recorded)
rules = ["fixed", "opt1\nATR", "opt2\nrobust", "opt3\naggregate"]
_oos = lambda k, dflt: [float(x) for x in os.environ[k].split(",")] if os.environ.get(k) else dflt
pnl = _oos("SUBOPT_OOS_PNL", [67627, 62001, 57514, 111464])
dd = _oos("SUBOPT_OOS_DD", [16204, 11057, 30975, 55748])
ddpl = _oos("SUBOPT_OOS_DDPL", [24, 18, 54, 50])
fig, ax = plt.subplots(1, 2, figsize=(10, 3.6))
bars = ax[0].bar(rules, pnl, color=["#607d8b", "#2962ff", "#ff9800", "#e53935"])
ax[0].set_title("TEST P/L ($)"); ax[0].axhline(67627, ls="--", c="grey", lw=.8)
for b, v in zip(bars, pnl): ax[0].text(b.get_x()+b.get_width()/2, v, f"{v/1000:.0f}k", ha="center", va="bottom", fontsize=8)
b2 = ax[1].bar(rules, ddpl, color=["#607d8b", "#2962ff", "#ff9800", "#e53935"])
ax[1].axhline(25, ls="--", c="red", lw=1); ax[1].set_title("Drawdown / P&L (%)  — red = 25% budget")
for b, v in zip(b2, ddpl): ax[1].text(b.get_x()+b.get_width()/2, v, f"{v}%", ha="center", va="bottom", fontsize=8)
fig.suptitle("Stage 2 OOS: opt3 highest P/L but BREACHES the 25% DD budget; opt1 only one within budget")
plt.tight_layout(); plt.savefig(_CH / "06_stage2_oos.png", dpi=110); plt.close()

print("charts →", _CH)
for p in sorted(_CH.glob("*.png")):
    print(" ", p.name)
