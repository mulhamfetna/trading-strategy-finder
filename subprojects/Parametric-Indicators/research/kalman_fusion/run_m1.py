"""M1 static-vote director: fit weights on 2025, sweep theta, print IS/OOS front. Heavy → server."""
from __future__ import annotations
import argparse, csv
import numpy as np
import research.kalman_fusion  # noqa: F401
from optimize import counterfactual_pause as cp
from research.kalman_fusion.m1_fusion import finer_tf_directions, fit_weights, evaluate_m1, n_split
from research.kalman_fusion.ceiling import eligible_dropped


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tf", default="4h")
    ap.add_argument("--tfs", default="1h,15m,5m")
    ap.add_argument("--out", default="research/kalman_fusion/m1_front.csv")
    a = ap.parse_args()
    C = cp.load_champion(a.tf)
    Z, cols = finer_tf_directions(C, tfs=tuple(a.tfs.split(",")))
    ns = n_split(C)
    idxs_is = [i for i in eligible_dropped(C)["idxs"] if i < ns]        # 2025 dropped only
    w = fit_weights(Z, C, idxs_is)
    print("columns:", cols, " weights:", [round(x, 3) for x in w])
    rows = []
    print(f"{'theta':>6} {'IS_ent':>7} {'IS_P/L':>12} {'IS_win%':>8}  {'OOS_ent':>8} {'OOS_P/L':>12} {'OOS_win%':>9}")
    for th in [round(x, 2) for x in np.linspace(0.0, 1.0, 11)]:
        is_m, oos_m = evaluate_m1(C, Z, w, th)
        print(f"{th:6.2f} {is_m.n_entries:7d} {is_m.total_pnl:12,.0f} {100*is_m.win_rate:7.1f}%  "
              f"{oos_m.n_entries:8d} {oos_m.total_pnl:12,.0f} {100*oos_m.win_rate:8.1f}%")
        rows.append(dict(theta=th, is_entries=is_m.n_entries, is_pnl=is_m.total_pnl, is_win=is_m.win_rate,
                         is_payoff=is_m.payoff, oos_entries=oos_m.n_entries, oos_pnl=oos_m.total_pnl,
                         oos_win=oos_m.win_rate, oos_payoff=oos_m.payoff))
    with open(a.out, "w", newline="") as f:
        wtr = csv.DictWriter(f, fieldnames=list(rows[0])); wtr.writeheader(); wtr.writerows(rows)
    print(f"\nwrote {len(rows)} rows -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
