"""Run the news CONTEXT-dependence study. SERVER ONLY (needs the 16-year 1-minute frame).

  python3 -m research.news_context.run_study --k 40 --horizons 5,15,30,60 \
      --ma-days 50 --draws 1000 --seed 20260723
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_PROJ = Path(__file__).resolve().parents[2]
if str(_PROJ) not in sys.path:
    sys.path.insert(0, str(_PROJ))

from optimize.fundamentals.extended_data import load_1m_extended     # noqa: E402
from research.news_context.contexts import (                          # noqa: E402
    label_c1_policy_regime, label_c2_vol_regime, label_c3_trend,
)
from research.news_context.ledger import attach_returns, load_ledger  # noqa: E402
from research.news_context.stats import (                             # noqa: E402
    assoc, bucket_delta, min_detectable_rho, shuffle_control,
)


def _regime_csv() -> Path:
    """The HMM daily labels live in the sibling regime-edge subproject."""
    return _PROJ.parent / "regime-edge" / "data" / "nq_daily_regime.csv"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, required=True, help="C1 trailing window in releases")
    ap.add_argument("--horizons", required=True)
    ap.add_argument("--ma-days", type=int, required=True)
    ap.add_argument("--draws", type=int, required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--out", default="results/news_context")
    a = ap.parse_args()
    hs = [int(x) for x in a.horizons.split(",")]
    reg_csv = _regime_csv()

    n_tests = 3 * len(hs)
    alpha_bonf = 0.05 / n_tests
    print("=" * 78)
    print("NEWS CONTEXT-DEPENDENCE -- parameters actually used")
    print(f"  C1 trailing k    : {a.k} releases")
    print(f"  horizons (min)   : {hs}")
    print(f"  C3 MA days       : {a.ma_days}")
    print(f"  shuffle draws    : {a.draws}")
    print(f"  seed             : {a.seed}")
    print(f"  regime csv       : {reg_csv}  (exists={reg_csv.exists()})")
    print(f"  tests            : 3 splits x {len(hs)} horizons = {n_tests}")
    print(f"  Bonferroni alpha : {alpha_bonf:.5f}")
    print("=" * 78)
    if not reg_csv.exists():
        raise SystemExit(f"ABORT: regime labels not found at {reg_csv}")

    sur = load_ledger()
    print(f"\nledger: {len(sur)} releases {sur['Date'].min().date()} -> {sur['Date'].max().date()}")
    df1 = load_1m_extended("NQ")
    print(f"price : {len(df1):,} 1-min bars {df1['Date'].min()} -> {df1['Date'].max()}")

    sur = attach_returns(sur, df1, hs)
    for h in hs:
        print(f"  ret_{h}: {int(sur[f'ret_{h}'].notna().sum())} priced releases")

    z = sur["surprise_z"].to_numpy(float)
    rows = []
    for h in hs:
        rc = f"ret_{h}"
        r = sur[rc].to_numpy(float)
        pooled = assoc(z, r)
        print(f"\n[h={h}] POOLED spearman={pooled['spearman']:+.4f} "
              f"pearson={pooled['pearson']:+.4f} n={pooled['n']}")

        splits = {
            "C1_policy_regime": (label_c1_policy_regime(sur, rc, a.k), "POS", "NEG"),
            "C2_vol_regime":    (label_c2_vol_regime(sur, reg_csv), "CALM", "TURBULENT"),
            "C3_trend":         (label_c3_trend(sur, df1, a.ma_days), "UP", "DOWN"),
        }
        for name, (lab, A, B) in splits.items():
            aa = assoc(z[lab == A], r[lab == A])
            bb = assoc(z[lab == B], r[lab == B])
            d = bucket_delta(z, r, lab, A, B)
            p, pct = shuffle_control(z, r, lab, A, B, a.draws, np.random.default_rng(a.seed))
            mde = min_detectable_rho(aa["n"], bb["n"])
            sig = (not np.isnan(p)) and p < alpha_bonf
            print(f"  {name:17s} {A:>9s}: rho={aa['spearman']:+.4f} n={aa['n']:4d} | "
                  f"{B:>9s}: rho={bb['spearman']:+.4f} n={bb['n']:4d} | "
                  f"delta={d:+.4f} p={p:.4f} MDE={mde:.4f} "
                  f"{'*** BEATS CONTROL' if sig else 'no'}")
            rows.append({"horizon": h, "split": name, "bucket_a": A, "bucket_b": B,
                         "rho_a": aa["spearman"], "n_a": aa["n"],
                         "rho_b": bb["spearman"], "n_b": bb["n"],
                         "delta": d, "shuffle_p": p, "shuffle_pct": pct,
                         "mde_rho": mde, "bonferroni_alpha": alpha_bonf,
                         "beats_control": sig,
                         "pooled_spearman": pooled["spearman"],
                         "pooled_pearson": pooled["pearson"], "pooled_n": pooled["n"]})

    outdir = Path(a.out)
    outdir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(outdir / "context_dependence.csv", index=False)

    n_sig = sum(1 for x in rows if x["beats_control"])
    worst_mde = np.nanmax([x["mde_rho"] for x in rows])
    print("\n" + "=" * 78)
    print(f"[VERDICT INPUT] {n_sig}/{len(rows)} tests beat the shuffled control at "
          f"Bonferroni alpha={alpha_bonf:.5f}")
    print(f"[VERDICT INPUT] worst-case minimum detectable |delta rho| = {worst_mde:.4f} "
          f"(a null below this is UNDERPOWERED, not evidence of absence)")
    print("=" * 78)
    print(f"wrote {outdir}/context_dependence.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
