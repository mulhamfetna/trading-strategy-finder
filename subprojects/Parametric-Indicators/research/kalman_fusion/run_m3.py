"""M3 CLI: walk-forward 3a (regime-scaled exits, decisive). Prints per-fold table + verdict; runs 3b
(regime-gated admission) only if 3a survives. Off the production path."""
from __future__ import annotations
import argparse
import research.kalman_fusion  # noqa: F401
from optimize import counterfactual_pause as cp
from research.kalman_fusion.m3_walkforward import walk_forward_3a, walk_forward_3b


def _q(k):  # 20253 -> "2025Q3"
    return f"{k // 10}Q{k % 10}"


def _fmt_map(m):
    return "{" + ",".join(f"{r}:{m[r][:1]}" for r in (0, 1, 2)) + "}"   # e.g. {0:T,1:B,2:W}


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--tf", default="4h"); a = ap.parse_args()
    C = cp.load_champion(a.tf)

    wf = walk_forward_3a(C)
    print(f"\n== M3-3a walk-forward: regime-scaled EXITS (NQ {a.tf}) ==")
    print(f"{'quarter':8} {'exit_map(L,M,H)':>16} {'M3_P/L':>11} {'base_P/L':>11} {'n':>5} {'M3>base':>8}")
    for r in wf["rows"]:
        print(f"{_q(r['q']):8} {_fmt_map(r['exit_map']):>16} {r['m3_pnl']:11,.0f} {r['base_pnl']:11,.0f} "
              f"{r['n']:5d} {str(r['m3_pnl'] > r['base_pnl']):>8}")
    print(f"  AGGREGATE: M3 ${wf['sum_m3']:,.0f} vs base ${wf['sum_base']:,.0f} "
          f"| M3 beats base in {wf['folds_m3_wins']}/{wf['n_folds']} folds")
    print(f"  VERDICT 3a: {'SURVIVED ✅' if wf['survived'] else 'DEAD ❌ (3b abandoned)'}")

    if not wf["survived"]:
        return 0

    wb = walk_forward_3b(C)
    print(f"\n== M3-3b walk-forward: regime-gated ADMISSION (inherits 3a exits) ==")
    print(f"{'quarter':8} {'admitted':>10} {'added':>6} {'M3_P/L':>11} {'base_P/L':>11} {'M3>base':>8}")
    for r in wb["rows"]:
        print(f"{_q(r['q']):8} {str(r['admitted']):>10} {r['added']:6d} {r['m3_pnl']:11,.0f} "
              f"{r['base_pnl']:11,.0f} {str(r['m3_pnl'] > r['base_pnl']):>8}")
    print(f"  AGGREGATE: M3 ${wb['sum_m3']:,.0f} vs base ${wb['sum_base']:,.0f} "
          f"| M3 beats base in {wb['folds_m3_wins']}/{wb['n_folds']} folds")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
