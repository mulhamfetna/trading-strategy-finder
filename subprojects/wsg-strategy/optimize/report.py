"""H.8 — outputs: per-TF Pareto front CSV + plot + cross-timeframe leaderboard.

Reads the persisted Optuna studies (optimize/studies/wsh.db), extracts each timeframe's Pareto
front (profit vs drawdown), and writes:
  results/<tf>_pareto.csv     — every Pareto-optimal param set + (median P/L, worst maxDD)
  results/<tf>_pareto.png     — profit-vs-drawdown scatter (all trials + front), if matplotlib
  results/leaderboard.csv     — per-TF highlights: max-P/L point, and best P/L with maxDD ≤ $5k

No auto-winner is chosen (D3): the full front is preserved; the leaderboard only flags reference
points. Run after optimizer.py has populated studies for the timeframes of interest.

CLI:  python3 subprojects/wsg-strategy/optimize/report.py [tf ...]   (default: all studies found)
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import optuna

_HERE = Path(__file__).resolve().parent
_DB = _HERE / "studies" / "wsh.db"
_RESULTS = _HERE / "results"
_RESULTS.mkdir(exist_ok=True)

DD_CAP = 5000.0
PARAM_COLS = ["sl_soft", "sl_hard", "tp", "gate_pct", "dd_limit", "cooldown", "flip"]


def _row(t) -> dict:
    p = t.params
    return {
        "median_pnl": round(t.values[0], 1),
        "worst_dd": round(-t.values[1], 1),
        "sl_soft": round(p["sl_soft"], 1),
        "sl_hard": round(p["sl_soft"] + p["sl_hard_delta"], 1),
        "tp": round(p["tp"], 1),
        "gate_pct": round(p["gate_pct"], 1),
        "dd_limit": round(p["dd_limit"], 0),
        "cooldown": p["cooldown"],
        "flip": p["flip"],
    }


def export_tf(tf_name: str) -> dict | None:
    try:
        study = optuna.load_study(study_name=f"wsh_{tf_name}", storage=f"sqlite:///{_DB}")
    except KeyError:
        print(f"[{tf_name}] no study found", flush=True)
        return None
    front = sorted(study.best_trials, key=lambda t: -t.values[1])  # by drawdown asc
    rows = [_row(t) for t in front]
    # per-TF Pareto CSV
    cpath = _RESULTS / f"{tf_name}_pareto.csv"
    with cpath.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["median_pnl", "worst_dd"] + PARAM_COLS)
        w.writeheader(); w.writerows(rows)
    # plot
    _plot(tf_name, study, front)
    # leaderboard highlights
    best_pnl = max(rows, key=lambda r: r["median_pnl"]) if rows else None
    capped = [r for r in rows if r["worst_dd"] <= DD_CAP]
    best_capped = max(capped, key=lambda r: r["median_pnl"]) if capped else None
    print(f"[{tf_name}] front {len(rows)} pts → {cpath.name}; "
          f"max P/L ${best_pnl['median_pnl']:,.0f} @ DD ${best_pnl['worst_dd']:,.0f}" if best_pnl
          else f"[{tf_name}] empty front", flush=True)
    return {"timeframe": tf_name, "n_front": len(rows), "best_pnl": best_pnl, "best_capped": best_capped}


def _plot(tf_name, study, front):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return
    done = [t for t in study.trials if t.values]
    xs = [-t.values[1] for t in done]; ys = [t.values[0] for t in done]
    fx = [-t.values[1] for t in front]; fy = [t.values[0] for t in front]
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(xs, ys, s=12, c="#8aa", alpha=0.4, label="trials")
    ax.plot(sorted(zip(fx, fy)) and [p[0] for p in sorted(zip(fx, fy))],
            [p[1] for p in sorted(zip(fx, fy))], "-o", c="#2962ff", ms=4, label="Pareto front")
    ax.axvline(DD_CAP, ls="--", c="#888", lw=1, label=f"${DD_CAP:,.0f} cap")
    ax.set_xlabel("worst-fold max drawdown ($)"); ax.set_ylabel("median fold P/L ($)")
    ax.set_title(f"WS-H {tf_name}: profit vs drawdown (Pareto front)")
    ax.legend(); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(_RESULTS / f"{tf_name}_pareto.png", dpi=110); plt.close(fig)


def main(argv: list[str]) -> int:
    if argv:
        names = argv
    else:
        names = [s.study_name.replace("wsh_", "")
                 for s in optuna.get_all_study_summaries(storage=f"sqlite:///{_DB}")
                 if s.study_name.startswith("wsh_")]
    lb = [export_tf(n) for n in names]
    lb = [x for x in lb if x]
    # cross-TF leaderboard
    lpath = _RESULTS / "leaderboard.csv"
    with lpath.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["timeframe", "front_pts", "maxPL_pnl", "maxPL_dd",
                    "bestCapped_pnl", "bestCapped_dd", "bestCapped_params"])
        for x in lb:
            bp, bc = x["best_pnl"], x["best_capped"]
            w.writerow([x["timeframe"], x["n_front"],
                        bp["median_pnl"] if bp else "", bp["worst_dd"] if bp else "",
                        bc["median_pnl"] if bc else "", bc["worst_dd"] if bc else "",
                        ({k: bc[k] for k in PARAM_COLS} if bc else "")])
    print(f"\nwrote {lpath}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
