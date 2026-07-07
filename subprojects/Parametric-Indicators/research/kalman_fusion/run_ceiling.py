"""Compute + print the M0 ceiling for a champion (default NQ 4h). Read-only; heavy run → server."""
from __future__ import annotations
import argparse, csv
import research.kalman_fusion  # noqa: F401
from optimize import counterfactual_pause as cp
from research.kalman_fusion.ceiling import ceiling_report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tf", default="4h")
    ap.add_argument("--out", default="research/kalman_fusion/ceiling_4h.csv")
    a = ap.parse_args()
    C = cp.load_champion(a.tf)
    rep = ceiling_report(C)
    rows = []
    print(f"{'stratum':12} {'n_drop':>7} {'variant':8} {'entry%':>7} {'payoff':>7} {'totalP/L':>12} {'win%':>6}")
    for key in ("champion", "all", "vol_gated", "vetoed", "confirm<K"):
        blk = rep[key]
        if key == "champion":
            p = blk
            print(f"{key:12} {'-':>7} {'base':8} {100*p['entry_rate']:6.1f}% {p['payoff']:7.2f} {p['total_pnl']:12,.0f} {100*p['win_rate']:5.1f}%")
            rows.append(dict(stratum=key, variant="base",
                             **{k: p[k] for k in ("entry_rate", "payoff", "total_pnl", "win_rate", "n_entries")}))
            continue
        for variant in ("native", "oracle"):
            p = blk[variant]
            print(f"{key:12} {blk['n_dropped']:7} {variant:8} {100*p['entry_rate']:6.1f}% {p['payoff']:7.2f} {p['total_pnl']:12,.0f} {100*p['win_rate']:5.1f}%")
            rows.append(dict(stratum=key, variant=variant, n_dropped=blk["n_dropped"],
                             **{k: p[k] for k in ("entry_rate", "payoff", "total_pnl", "win_rate", "n_entries")}))
    with open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=sorted({k for r in rows for k in r}))
        w.writeheader(); w.writerows(rows)
    print(f"\nwrote {len(rows)} rows -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
