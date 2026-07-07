"""M2 trend-state sweep: for each frame-config x mode, sweep theta -> IS/OOS front. Heavy -> server."""
from __future__ import annotations
import argparse, csv
import numpy as np
import research.kalman_fusion  # noqa: F401
from optimize import counterfactual_pause as cp
from research.kalman_fusion.m2_trend import trend_z, evaluate_m2
from research.kalman_fusion.m1_fusion import n_split
from research.kalman_fusion.ceiling import eligible_dropped


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tf", default="4h")
    ap.add_argument("--out", default="research/kalman_fusion/m2_front.csv")
    a = ap.parse_args()
    C = cp.load_champion(a.tf)
    Z = trend_z(C, frames=("4h", "1m"))
    # thresholds are |z| QUANTILES computed on 2025 (IS) dropped signals ONLY (no OOS leakage; scale-free).
    ns = n_split(C)
    idxs_is = [i for i in eligible_dropped(C)["idxs"] if i < ns]
    pcts = [0.0, 0.50, 0.60, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95]
    rows = []
    for frame in ("4h", "1m", "combined"):
        thetas = list(np.quantile(np.abs(Z[frame][idxs_is]), pcts)) + [1e9]
        for mode in ("redirect", "filter"):
            print(f"\n== frame={frame} mode={mode} ==")
            print(f"{'theta':>8} {'IS_ent':>7} {'IS_P/L':>12} {'IS_win%':>8}  {'OOS_ent':>8} {'OOS_P/L':>12} {'OOS_win%':>9}")
            for th in thetas:
                is_m, oos_m = evaluate_m2(C, Z[frame], th, mode)
                print(f"{th:8.4f} {is_m.n_entries:7d} {is_m.total_pnl:12,.0f} {100*is_m.win_rate:7.1f}%  "
                      f"{oos_m.n_entries:8d} {oos_m.total_pnl:12,.0f} {100*oos_m.win_rate:8.1f}%")
                rows.append(dict(frame=frame, mode=mode, theta=th, is_entries=is_m.n_entries,
                                 is_pnl=is_m.total_pnl, is_win=is_m.win_rate, oos_entries=oos_m.n_entries,
                                 oos_pnl=oos_m.total_pnl, oos_win=oos_m.win_rate, oos_payoff=oos_m.payoff))
    with open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print(f"\nwrote {len(rows)} rows -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
