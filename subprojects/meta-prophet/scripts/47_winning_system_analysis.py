"""WS-G — full analysis + charts for the WINNING drawdown-capped system.

System = vSL_G60 + drawdown breaker(L2500, cd20):
  base SL/TP 20/25/40  |  vol gate @ 60th pct (skip top-40% vol bars)  |  no sl_tp_mult
  drawdown circuit-breaker: lock new entries when running DD>=2500, re-probe after 20 trades.

Re-runs it on the cloned single-contract engine, applies the causal breaker overlay, and emits:
  - dashboard-style analytics (equity, drawdown, monthly, streaks, exit-reasons, exposure)
  - charts -> plots/winning_system/*.png   (tracked)
  - the circuit-breaker state diagram        -> plots/winning_system/state_diagram.png
  - tables -> outputs/winning_system_*.csv   (git-ignored) and printed for the report
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch

PROJ = Path("/mnt/data/projects/trading")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJ)); sys.path.insert(0, str(ROOT))
import importlib.util
spec = importlib.util.spec_from_file_location("bm", ROOT / "scripts" / "17_backtest_matrix.py")
bm = importlib.util.module_from_spec(spec); spec.loader.exec_module(bm)

NQ_PV = 20.0
PLOTS = ROOT / "plots" / "winning_system"; PLOTS.mkdir(parents=True, exist_ok=True)
OUT = ROOT / "outputs"

_ap = argparse.ArgumentParser()
_ap.add_argument("--ss", type=float, default=30); _ap.add_argument("--sh", type=float, default=40)
_ap.add_argument("--tp", type=float, default=60); _ap.add_argument("--gate", type=float, default=60)
_ap.add_argument("--dd", type=float, default=2500); _ap.add_argument("--cd", type=int, default=30)
_A = _ap.parse_args()
SL_SOFT_W, SL_HARD_W, TP_W, GATE_PCT = _A.ss, _A.sh, _A.tp, _A.gate
DD_LIMIT, COOLDOWN = _A.dd, _A.cd
plt.rcParams.update({"figure.facecolor": "white", "axes.grid": True, "grid.alpha": 0.3, "font.size": 10})


def run_engine(df4, df1, box, sl_soft, sl_hard, tp, gate=None):
    p = bm.SimpleStrategyParams(sl_soft_points=sl_soft, sl_hard_points=sl_hard, tp_soft_points=tp,
                                tp_hard_points=tp, data_path_4h="", data_path_1min="",
                                box_data_path="", flip_entry_direction=False)
    trades, _ = bm.SimpleStrategy(p).backtest(df4, df1, box, entry_gate=gate)
    closed = [t for t in trades if t.get("exit_reason") not in (None, "OPEN")]
    closed.sort(key=lambda t: pd.Timestamp(t["entry_time"]))
    return closed


def breaker(pnl_d, dd_limit, cooldown):
    peak = eq = 0.0; locked = False; cd = 0
    keep = np.zeros(len(pnl_d), bool); state = []
    for i, x in enumerate(pnl_d):
        if locked:
            cd -= 1
            if cd <= 0:
                locked = False; peak = eq
            else:
                state.append("LOCKED"); continue
        eq += x; keep[i] = True; peak = max(peak, eq); state.append("TRADING")
        if peak - eq >= dd_limit:
            locked = True; cd = cooldown
    return keep


def equity_series(closed, keep=None):
    rows = [(pd.Timestamp(t["exit_time"]), float(t["pnl_points"]) * NQ_PV) for t in closed]
    if keep is not None:
        rows = [r for r, k in zip(rows, keep) if k]
    rows.sort()
    t = [r[0] for r in rows]; cum = np.cumsum([r[1] for r in rows]) if rows else np.array([])
    return t, cum


def underwater(cum):
    peak = np.maximum.accumulate(cum); return peak - cum


def main():
    df4, df1, box = bm.load_all()
    n2025 = int((df4["_year"] == 2025).sum())
    vf = bm.har_rv_forecast(df4)
    gate = vf <= np.percentile(vf[:n2025], GATE_PCT)

    closed = run_engine(df4, df1, box, SL_SOFT_W, SL_HARD_W, TP_W, gate=gate)
    pnl_d = np.array([float(t["pnl_points"]) * NQ_PV for t in closed])
    keep = breaker(pnl_d, DD_LIMIT, COOLDOWN)

    # baseline (verified params, no gate, no breaker) for comparison
    base_closed = run_engine(df4, df1, box, 80, 100, 50, gate=None)

    # ---- analytics ----
    kept = [t for t, k in zip(closed, keep) if k]
    kp = np.array([float(t["pnl_points"]) * NQ_PV for t in kept])
    yr = np.array([pd.Timestamp(t["exit_time"]).year for t in kept])
    tw, cw = equity_series(closed, keep)
    uw = underwater(cw)
    tb, cb = equity_series(base_closed)

    def streak(mask):  # longest run of True
        best = cur = 0
        for v in mask:
            cur = cur + 1 if v else 0; best = max(best, cur)
        return best
    wins, losses = kp[kp > 0], kp[kp < 0]
    stats = {
        "total_pnl": kp.sum(), "pnl_2025": kp[yr == 2025].sum(), "pnl_2026": kp[yr == 2026].sum(),
        "n_trades": len(kp), "n_available": len(closed), "exposure_pct": 100 * len(kp) / len(closed),
        "win_rate": 100 * (kp > 0).mean(), "avg_win": wins.mean() if len(wins) else 0,
        "avg_loss": losses.mean() if len(losses) else 0,
        "profit_factor": wins.sum() / abs(losses.sum()) if len(losses) and losses.sum() != 0 else float("inf"),
        "max_dd": float(uw.max()), "max_win_streak": streak(kp > 0), "max_loss_streak": streak(kp < 0),
        "best_trade": kp.max(), "worst_trade": kp.min(),
    }
    pd.Series(stats).to_csv(OUT / "winning_system_stats.csv")

    # monthly P/L
    mdf = pd.DataFrame({"exit": [pd.Timestamp(t["exit_time"]) for t in kept], "pnl": kp})
    mdf["ym"] = mdf["exit"].dt.to_period("M").astype(str)
    monthly = mdf.groupby("ym")["pnl"].sum()
    monthly.to_csv(OUT / "winning_system_monthly.csv")

    # exit-reason breakdown
    exr = pd.Series([t["exit_reason"] for t in kept]).value_counts()
    exr.to_csv(OUT / "winning_system_exitreasons.csv")

    # ---- charts ----
    # 1. equity vs baseline
    fig, ax = plt.subplots(figsize=(11, 4.5))
    ax.plot(tw, cw, color="#1f9d55", lw=1.6, label="WINNER  vSL_G60 + breaker")
    ax.plot(tb, cb, color="#b00", lw=1.2, alpha=.7, label="baseline (verified params, no overlay)")
    ax.axvline(df4.iloc[n2025]["Date"], color="#888", ls="--", lw=1, label="2025→2026")
    ax.axhline(0, color="#000", lw=.6); ax.set_title("Equity curve ($, 1 contract)")
    ax.set_ylabel("cumulative P/L ($)"); ax.legend(loc="upper left", fontsize=9)
    fig.tight_layout(); fig.savefig(PLOTS / "equity_vs_baseline.png", dpi=120); plt.close(fig)

    # 2. underwater drawdown
    fig, ax = plt.subplots(figsize=(11, 3.4))
    ax.fill_between(tw, -uw, 0, color="#b00", alpha=.35)
    ax.axhline(-DD_LIMIT, color="#d68", ls="--", lw=1, label=f"breaker limit −${DD_LIMIT:,.0f}")
    ax.axhline(-5000, color="#444", ls=":", lw=1, label="target cap −$5,000")
    ax.set_title(f"Drawdown (underwater) — max ${uw.max():,.0f}")
    ax.set_ylabel("drawdown ($)"); ax.legend(loc="lower left", fontsize=9)
    fig.tight_layout(); fig.savefig(PLOTS / "drawdown_underwater.png", dpi=120); plt.close(fig)

    # 3. monthly P/L
    fig, ax = plt.subplots(figsize=(11, 3.6))
    colors = ["#1f9d55" if v >= 0 else "#b00" for v in monthly.values]
    ax.bar(range(len(monthly)), monthly.values, color=colors)
    ax.set_xticks(range(len(monthly))); ax.set_xticklabels(monthly.index, rotation=60, fontsize=8)
    ax.axhline(0, color="#000", lw=.6); ax.set_title("Monthly P/L ($)"); ax.set_ylabel("P/L ($)")
    fig.tight_layout(); fig.savefig(PLOTS / "monthly_pnl.png", dpi=120); plt.close(fig)

    # 4. per-trade P/L histogram
    fig, ax = plt.subplots(figsize=(8, 3.8))
    ax.hist(kp, bins=40, color="#3676d6", alpha=.8)
    ax.axvline(0, color="#000", lw=.8); ax.set_title("Per-trade P/L distribution ($)")
    ax.set_xlabel("trade P/L ($)"); ax.set_ylabel("count")
    fig.tight_layout(); fig.savefig(PLOTS / "pnl_histogram.png", dpi=120); plt.close(fig)

    # 5. exit-reason breakdown
    fig, ax = plt.subplots(figsize=(7, 3.6))
    ax.bar(exr.index, exr.values, color="#7a5ccc")
    ax.set_title("Exit-reason breakdown"); ax.set_ylabel("# trades")
    for i, v in enumerate(exr.values): ax.text(i, v, str(v), ha="center", va="bottom", fontsize=9)
    fig.tight_layout(); fig.savefig(PLOTS / "exit_reasons.png", dpi=120); plt.close(fig)

    # 6. state diagram of the circuit-breaker
    fig, ax = plt.subplots(figsize=(9, 3.6)); ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(0, 5)
    tr = mpatches.FancyBboxPatch((0.6, 1.8), 3, 1.4, boxstyle="round,pad=0.1",
                                 fc="#d6f5e3", ec="#1f9d55", lw=2)
    lk = mpatches.FancyBboxPatch((6.4, 1.8), 3, 1.4, boxstyle="round,pad=0.1",
                                 fc="#fde0e0", ec="#b00", lw=2)
    ax.add_patch(tr); ax.add_patch(lk)
    ax.text(2.1, 2.5, "TRADING\n(take signals)", ha="center", va="center", fontsize=11, weight="bold")
    ax.text(7.9, 2.5, "LOCKED\n(skip entries)", ha="center", va="center", fontsize=11, weight="bold")
    ax.add_patch(FancyArrowPatch((3.6, 2.9), (6.4, 2.9), arrowstyle="->", mutation_scale=18, lw=2, color="#b00"))
    ax.text(5.0, 3.25, f"running DD ≥ ${DD_LIMIT:,.0f}", ha="center", fontsize=9, color="#b00")
    ax.add_patch(FancyArrowPatch((6.4, 2.1), (3.6, 2.1), arrowstyle="->", mutation_scale=18, lw=2, color="#1f9d55"))
    ax.text(5.0, 1.55, f"after {COOLDOWN} skipped trades\n(peak resets to current equity)", ha="center", fontsize=9, color="#1f9d55")
    ax.add_patch(FancyArrowPatch((1.4, 3.2), (2.8, 3.2), connectionstyle="arc3,rad=-1.2",
                                 arrowstyle="->", mutation_scale=14, lw=1.4, color="#1f9d55"))
    ax.text(2.1, 4.1, "win/small loss\n(stay)", ha="center", fontsize=8, color="#1f9d55")
    ax.add_patch(FancyArrowPatch((8.6, 3.2), (7.2, 3.2), connectionstyle="arc3,rad=1.2",
                                 arrowstyle="->", mutation_scale=14, lw=1.4, color="#b00"))
    ax.text(7.9, 4.1, "cooldown not done\n(stay locked)", ha="center", fontsize=8, color="#b00")
    ax.set_title("Drawdown circuit-breaker — state machine", fontsize=12, weight="bold")
    fig.tight_layout(); fig.savefig(PLOTS / "state_diagram.png", dpi=120); plt.close(fig)

    # ---- print tables for the report ----
    print("=== WINNING SYSTEM — key stats ===")
    for k, v in stats.items():
        print(f"  {k:<16} {v:,.2f}" if isinstance(v, float) else f"  {k:<16} {v}")
    print("\n=== Monthly P/L ===\n" + monthly.to_string())
    print("\n=== Exit reasons ===\n" + exr.to_string())
    print(f"\ncharts -> {PLOTS}/  (6 PNGs incl. state_diagram.png)")
    print(f"baseline final equity ${cb[-1]:,.0f} vs winner ${cw[-1]:,.0f}")


if __name__ == "__main__":
    main()
