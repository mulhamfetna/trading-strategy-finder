#!/usr/bin/env python3
"""Render a dashboard-style 'deployed candidate' result card (screenshot) for the experimental regime
size-ramp overlay. Shows the OFF (golden-safe) vs ON (experimental) states + the honest banner.

Run:  python3 deploy_card.py <out.png>
"""
import sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

GRAY, GREEN, AMBER, INK = "#6b7785", "#3a9d5d", "#c77d0a", "#22303c"
fig = plt.figure(figsize=(8.6, 4.8), dpi=130); fig.patch.set_facecolor("#f4f6f8")
ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off")

# header
ax.text(0.04, 0.92, "Backtesting system · EXPERIMENTAL overlay", fontsize=11, color=GRAY, weight="bold")
ax.text(0.04, 0.84, "Regime Size-Ramp  (NQ 1h+4h fusion)", fontsize=17, color=INK, weight="bold")
# amber banner
ax.add_patch(FancyBboxPatch((0.04, 0.70), 0.92, 0.09, boxstyle="round,pad=0.01",
                            fc="#fdf3e2", ec=AMBER, lw=1.2, transform=ax.transAxes))
ax.text(0.06, 0.745, "⚠  CANDIDATE — magnitude UNCONFIRMED (n=1 book). Off by default (golden-safe). "
        "Signal real (96% vs random, 4/5 folds); dollar uplift 90% CI [-$21k,+$61k].",
        fontsize=8.6, color="#8a5a06", va="center")

# two stat tiles: OFF and ON
def tile(x, title, tcol, rows):
    ax.add_patch(FancyBboxPatch((x, 0.12), 0.43, 0.52, boxstyle="round,pad=0.012",
                                fc="white", ec="#d8dee4", lw=1, transform=ax.transAxes))
    ax.text(x+0.02, 0.575, title, fontsize=12, color=tcol, weight="bold")
    for i, (k, v) in enumerate(rows):
        yy = 0.49 - i*0.085
        ax.text(x+0.02, yy, k, fontsize=10, color=GRAY)
        ax.text(x+0.41, yy, v, fontsize=11, color=INK, weight="bold", ha="right")

tile(0.04, "OFF  (default)", GRAY, [
    ("Profit", "$151,872"), ("Max drawdown", "$27,508"), ("Return / DD", "5.52"),
    ("vs flat book", "identical ✓")])
tile(0.53, "ON  (experimental)", GREEN, [
    ("Profit  (equal risk)", "$162,228"), ("Max drawdown", "$27,508 (held)"), ("Return / DD", "5.90"),
    ("Δ at equal risk", "+$10,356  (candidate)")])

ax.text(0.04, 0.05, "flag: --enable · ramp 0.5→1.5 by causal HMM regime · equal-risk normalized · per-instrument",
        fontsize=8, color=GRAY)
fig.savefig(sys.argv[1], facecolor=fig.get_facecolor()); print("wrote", sys.argv[1])
