"""M2 walk-forward: expanding quarterly, theta-on-train, per-fold test vs champion. Two lead configs."""
from __future__ import annotations
import argparse
import research.kalman_fusion  # noqa: F401
from optimize import counterfactual_pause as cp
from research.kalman_fusion.m2_trend import trend_z
from research.kalman_fusion.m2_walkforward import walk_forward

CONFIGS = [("4h", "filter"), ("combined", "redirect")]


def _q(k):  # 20253 -> "2025Q3"
    return f"{k // 10}Q{k % 10}"


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--tf", default="4h"); a = ap.parse_args()
    C = cp.load_champion(a.tf)
    Z = trend_z(C, frames=("4h", "1m"))
    for frame, mode in CONFIGS:
        wf = walk_forward(C, Z[frame], mode)
        print(f"\n== M2 walk-forward: frame={frame} mode={mode} ==")
        print(f"{'quarter':8} {'theta':>8} {'M2_P/L':>11} {'M2_n':>5} {'M2_win%':>8}  {'champ_P/L':>11} {'champ_n':>7} {'M2>champ':>8}")
        for r in wf["rows"]:
            m2, ch = r["m2"], r["champ"]
            print(f"{_q(r['q']):8} {r['theta']:8.4f} {m2['pnl']:11,.0f} {m2['n']:5d} {100*m2['win']:7.1f}%  "
                  f"{ch['pnl']:11,.0f} {ch['n']:7d} {str(m2['pnl'] > ch['pnl']):>8}")
        print(f"  AGGREGATE: M2 ${wf['sum_m2_pnl']:,.0f} vs champion ${wf['sum_champ_pnl']:,.0f} "
              f"| M2 beats champ in {wf['folds_m2_wins']}/{wf['n_folds']} folds")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
