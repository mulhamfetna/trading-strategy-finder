#!/usr/bin/env python3
"""Render the mega-report result figures (PNG) from the VERIFIED experiment numbers.
Clean bars for magnitude; colorblind-safe palette; direct value labels (color is never the sole
encoding); one axis; recessive grid. Saves to reports/figures/.

Run:  python3 make_figures.py <out_dir>
"""
import sys, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

GRAY, GREEN, RED, BLUE = "#6b7785", "#3a9d5d", "#d1495b", "#4c78a8"
plt.rcParams.update({"figure.dpi": 130, "font.size": 11, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.grid": True, "grid.alpha": 0.25,
                     "grid.linewidth": 0.6, "axes.axisbelow": True})


def barlabels(ax, bars, fmt):
    for b in bars:
        h = b.get_height()
        ax.annotate(fmt(h), (b.get_x()+b.get_width()/2, h), ha="center",
                    va="bottom" if h >= 0 else "top", fontsize=10, fontweight="bold",
                    xytext=(0, 3 if h >= 0 else -3), textcoords="offset points")


def fig_timesfm(out):
    fig, ax = plt.subplots(figsize=(6.6, 4))
    groups = ["In-sample\n(2025–26 bull)", "Out-of-sample\n(2024–26)"]
    ref = [9.36, 5.52]; gate = [18.78, 4.62]
    x = range(len(groups)); w = 0.36
    b1 = ax.bar([i-w/2 for i in x], ref, w, color=GRAY, label="reference (no gate)")
    b2 = ax.bar([i+w/2 for i in x], gate, w, color=[GREEN, RED], label="+ TimesFM vol-gate")
    barlabels(ax, b1, lambda v: f"{v:.2f}"); barlabels(ax, b2, lambda v: f"{v:.2f}")
    ax.set_xticks(list(x)); ax.set_xticklabels(groups); ax.set_ylabel("Return / Drawdown")
    ax.set_title("TimesFM vol-gate: helps in-sample, FAILS out-of-sample", fontweight="bold")
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    ax.annotate("green = gate helps · red = gate hurts", (0, -0.18), xycoords="axes fraction", fontsize=8, color=GRAY)
    fig.tight_layout(); fig.savefig(os.path.join(out, "fig_timesfm.png")); plt.close(fig)


def fig_regime(out):
    fig, ax = plt.subplots(figsize=(6.6, 4))
    labels = ["calm", "mid", "mid", "turbulent"]; vals = [-0.17, 1.88, 3.76, 4.15]
    cols = [RED, GRAY, GRAY, GREEN]
    b = ax.bar(range(4), vals, color=cols, width=0.62)
    barlabels(ax, b, lambda v: f"{v:.2f}")
    ax.axhline(0, color="#333", linewidth=0.8)
    ax.set_xticks(range(4)); ax.set_xticklabels([f"regime {i}\n{l}" for i, l in enumerate(labels)])
    ax.set_ylabel("Return / Drawdown of the strategy")
    ax.set_title("The strategy is VOL-SEEKING — best in the most turbulent regime", fontweight="bold")
    ax.annotate("loses only in the calmest regime → a high-vol veto removes its best trades",
                (0, -0.2), xycoords="axes fraction", fontsize=8, color=GRAY)
    fig.tight_layout(); fig.savefig(os.path.join(out, "fig_regime_hmm.png")); plt.close(fig)


def fig_chronos(out):
    fig, ax = plt.subplots(figsize=(6.6, 4))
    labels = ["reference\n(no gate)", "+ TimesFM\ngate", "+ Chronos-2\ngate"]
    vals = [5.52, 4.62, 4.63]; cols = [GRAY, RED, RED]
    b = ax.bar(range(3), vals, color=cols, width=0.6)
    barlabels(ax, b, lambda v: f"{v:.2f}")
    ax.set_xticks(range(3)); ax.set_xticklabels(labels); ax.set_ylabel("Return / Drawdown")
    ax.set_title("Chronos-2 fails identically to TimesFM (bands correlate 0.71)", fontweight="bold")
    ax.annotate("3 independent methods agree: vol-gating does not help a vol-seeking strategy",
                (0, -0.2), xycoords="axes fraction", fontsize=8, color=GRAY)
    fig.tight_layout(); fig.savefig(os.path.join(out, "fig_chronos.png")); plt.close(fig)


def fig_sizing(out):
    fig, ax = plt.subplots(figsize=(7, 4))
    labels = ["flat sizing\n(baseline)", "inverse-vol\ntargeting (textbook)", "regime size-ramp\n(size WITH vol)"]
    vals = [151872, 129007, 162228]; cols = [GRAY, RED, GREEN]
    b = ax.bar(range(3), vals, color=cols, width=0.6)
    barlabels(ax, b, lambda v: f"${v/1000:.0f}k")
    ax.set_xticks(range(3)); ax.set_xticklabels(labels)
    ax.set_ylabel("Profit at EQUAL risk (max-DD held = $27,508)")
    ax.set_ylim(0, 185000)
    ax.set_title("THE WINNER: size WITH volatility → +$10.4k at identical drawdown", fontweight="bold")
    ax.annotate("textbook inverse-vol sizing HURTS (shrinks the trades we earn on)",
                (0, -0.2), xycoords="axes fraction", fontsize=8, color=GRAY)
    fig.tight_layout(); fig.savefig(os.path.join(out, "fig_sizing.png")); plt.close(fig)


def fig_concentration(out):
    fig, ax = plt.subplots(figsize=(6.2, 4))
    labels = ["high concentration\n(mega-cap)", "low concentration\n(broad)"]
    vals = [294, 286]; b = ax.bar(range(2), vals, color=[BLUE, BLUE], width=0.5)
    barlabels(ax, b, lambda v: f"${v:.0f}/trade")
    ax.set_xticks(range(2)); ax.set_xticklabels(labels); ax.set_ylabel("Per-trade mean P&L")
    ax.set_ylim(0, 360)
    ax.set_title("Concentration: NO edge — gap $8, permutation p = 0.97", fontweight="bold")
    ax.annotate("bootstrap 90% CI [-$393, +$423] includes zero → not significant",
                (0, -0.2), xycoords="axes fraction", fontsize=8, color=GRAY)
    fig.tight_layout(); fig.savefig(os.path.join(out, "fig_concentration.png")); plt.close(fig)


def main():
    out = sys.argv[1]; os.makedirs(out, exist_ok=True)
    fig_timesfm(out); fig_regime(out); fig_chronos(out); fig_sizing(out); fig_concentration(out)
    print("wrote:", ", ".join(sorted(os.listdir(out))))


if __name__ == "__main__":
    main()
