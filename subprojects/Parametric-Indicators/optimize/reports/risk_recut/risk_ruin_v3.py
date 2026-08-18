"""RISK-02b (Issue #3) — the RUIN-constrained sizing bound on the deployed book, honest fills.

WHY THIS EXISTS. risk_recut_v2.py reproduced the established Z2/Z4 Monte-Carlo faithfully and got an
absurd answer: PnL:DD rising monotonically to the edge of the grid (f=4%, median drawdown 72%), median
growth 13x. That is not an optimum, it is a broken objective, and the break is instructive.

The Z2/Z4 simulator computes wealth as cumprod(max(1 + f*R, 1e-9)) and reports the MEDIAN path. Two
assumptions hide in there:

  * `max(..., 1e-9)` turns a bankrupting trade into "wealth becomes ~0, now keep compounding". Ruin is
    not absorbing, so it never registers as ruin.
  * the MEDIAN path never experiences the rare catastrophic trade at all, so the tail that decides
    sizing is exactly what the statistic discards.

Both were harmless on the OLD engine, where a gapped stop filled AT THE LINE and no trade could lose
more than 1 risk unit — bounded loss makes median drawdown a sufficient constraint. With gap_fills=True
the ledger contains the real thing: **21.8% of trades lose more than their hard stop**, the worst reaches
-183R, and a single such trade at f=1% costs 183% of capital. Under unbounded per-trade loss the binding
constraint is not median drawdown at all — it is single-trade ruin.

So this script keeps the same ledger and asks the question that actually binds:
  * bankruptcy is ABSORBING — 1 + f*R <= 0 ends the path at zero, permanently;
  * we report P(ruin) and P(drawdown >= 50%), not just the median;
  * and f_survive = 1/|worst observed R|, the largest fraction at which the worst trade ON RECORD does
    not end you.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "/home/dev/Mulham")
import risk_recut_v2 as V2  # noqa: E402  — reuse the exact ledger builder, unchanged

M, N = 4000, 1000
GRID = [0.0005, 0.001, 0.002, 0.003, 0.004, 0.006, 0.008, 0.010, 0.015, 0.020, 0.030, 0.040]


def sim_ruin(base, f, rng):
    """Monte Carlo where bankruptcy is ABSORBING and the tail is not averaged away."""
    idx = rng.integers(0, len(base), size=(M, N))
    R = base[idx]
    step = 1.0 + f * R
    bankrupt_step = step <= 0.0                       # a single trade that wipes the account
    ever_bankrupt = bankrupt_step.any(axis=1)
    # Neutralize post-bankruptcy steps so a dead path cannot "recover"; its wealth is pinned at 0 below.
    safe = np.where(bankrupt_step, 1.0, np.maximum(step, 1e-12))
    W = np.cumprod(safe, axis=1)
    peak = np.maximum.accumulate(W, axis=1)
    dd = (1.0 - W / peak).max(axis=1)
    final = W[:, -1].copy()
    final[ever_bankrupt] = 0.0
    dd[ever_bankrupt] = 1.0
    return {
        "median_growth": float(np.median(final)),
        "median_dd": float(np.median(dd)),
        "p_ruin": float(ever_bankrupt.mean()),
        "p_dd50": float((dd >= 0.50).mean()),
        "p_dd90": float((dd >= 0.90).mean()),
        "p_lose_half": float((final < 0.5).mean()),
    }


def report(name, base, seeds=(0, 1, 2, 3)):
    worst = float(base.min())
    f_survive = 1.0 / abs(worst) if worst < 0 else float("inf")
    print(f"\n{'=' * 104}")
    print(f"{name} — {len(base):,} trades | expectancy {base.mean():+.4f}R | worst {worst:.2f}R")
    print(f"  f_survive = 1/|worst R| = {100*f_survive:.3f}%  "
          f"(above this, the worst trade ALREADY ON RECORD ends the account)")
    print(f"{'=' * 104}")
    print(f"  {'f':>7} {'med growth':>11} {'med dd':>8} {'P(ruin)':>9} {'P(dd>=50%)':>11} "
          f"{'P(dd>=90%)':>11} {'P(lose half)':>13}")
    print("  " + "-" * 96)
    rows = []
    for f in GRID:
        agg = {}
        for sd in seeds:                              # average over seeds — the noise check, built in
            r = sim_ruin(base, f, np.random.default_rng(sd))
            for k, v in r.items():
                agg.setdefault(k, []).append(v)
        m = {k: float(np.mean(v)) for k, v in agg.items()}
        rows.append((f, m))
        flag = ""
        if f > f_survive:
            flag = "  <- worst-on-record wipes you out"
        elif m["p_ruin"] > 0.01:
            flag = "  <- >1% of paths ruined"
        print(f"  {100*f:>6.2f}% {m['median_growth']:>11.3f}x {100*m['median_dd']:>7.1f}% "
              f"{100*m['p_ruin']:>8.2f}% {100*m['p_dd50']:>10.1f}% {100*m['p_dd90']:>10.1f}% "
              f"{100*m['p_lose_half']:>12.1f}%{flag}")
    # The defensible operating point: largest f with P(ruin)=0 AND P(dd>=50%) under 5%.
    ok = [f for f, m in rows if m["p_ruin"] == 0.0 and m["p_dd50"] < 0.05 and f <= f_survive]
    rec = max(ok) if ok else None
    print(f"  => largest f with NO ruin and P(dd>=50%)<5%: "
          f"{100*rec:.3f}%" if rec else "  => NO fraction on the grid is safe by that rule")
    return {"worst_R": worst, "f_survive": f_survive, "rows": rows, "recommended": rec}


def main():
    print("Building the cap-aware deployed ledger (reusing risk_recut_v2, unchanged) ...")
    per, _ = V2.build(cap_aware=True)
    allR = np.concatenate([r for m in per.values() for r in m.values()])
    exNG = np.concatenate([r for i, m in per.items() if i != "NG" for r in m.values()])

    out = {"whole_book": report("WHOLE DEPLOYED BOOK (all 9 markets)", allR),
           "ex_NG": report("BOOK EXCLUDING NG", exNG)}
    for inst in V2.INSTS:
        if per.get(inst):
            r = np.concatenate(list(per[inst].values()))
            out[inst] = report(f"{inst} ALONE", r)

    print(f"\n{'=' * 104}")
    print("PER-MARKET RUIN BOUND — the largest risk fraction each market can carry")
    print(f"{'=' * 104}")
    print(f"  {'mkt':>5} {'trades':>9} {'worst R':>10} {'f_survive':>11} {'safe f':>9}   verdict")
    for k in ["whole_book", "ex_NG"] + V2.INSTS:
        if k not in out:
            continue
        d = out[k]
        rec = d["recommended"]
        verdict = "OK" if rec else "NO SAFE SIZE ON GRID"
        print(f"  {k:>5} {'':>9} {d['worst_R']:>10.2f} {100*d['f_survive']:>10.3f}% "
              f"{(f'{100*rec:.3f}%' if rec else '--'):>9}   {verdict}")

    p = Path("/home/dev/Mulham/risk2/risk_ruin_v3.json")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, default=float))
    print(f"\nWROTE {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
