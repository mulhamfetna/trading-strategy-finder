#!/usr/bin/env python3
"""PROMOTE the sizing result properly (Exp2 follow-up).

Exp2 showed a regime size-ramp (calm 0.5x -> turbulent 1.5x) lifts Return/DD 5.52->5.90 but RAISES
absolute drawdown ($27.5k->$31.0k). "Promote" = make it honest:
  1. EQUAL-RISK: normalize the ramped book so max-DD == the flat book's, and report the P/L uplift at
     IDENTICAL risk (Return/DD gain -> profit at equal drawdown).
  2. SCALE-ROBUSTNESS: does it help across a range of ramp steepnesses (not one cherry-picked scale)?
  3. OOS HOLDOUT: the vol-seeking ORDERING is decided on 2024-2025; apply the fixed a-priori ramp to
     2026 (held out) and check it still helps.
  4. RANDOM-REGIME control on the chosen config.

Run:  python3 promote_sizing.py <NQ_1h.csv> <fusion_log.csv>
"""
from __future__ import annotations
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, "/home/dev/Mulham/regime-hmm")
from regime_baseline import daily_features, fit_hmm, bic, filtered_states, TRAIN_END, RESTARTS

RNG = np.random.default_rng(21)


def dd(p):
    eq = np.cumsum(p); return float((np.maximum.accumulate(eq) - eq).max()) if len(p) else 0.0
def rdd(p):
    p = np.asarray(p, float); d = dd(p); return p.sum() / d if d else float("inf")


def regimes(nq_csv):
    feat = daily_features(nq_csv)
    tr = feat[feat.index < TRAIN_END]; mu, sd = tr.mean(), tr.std()
    Z = ((feat - mu) / sd).to_numpy(); Ztr = ((tr - mu) / sd).to_numpy()
    best = min(((k,) + (lambda r: (r[1], bic(r[1], k, Ztr.shape[1], len(Ztr)), r[0]))(fit_hmm(Ztr, k, RESTARTS))
                for k in (2, 3, 4)), key=lambda x: x[2])
    n, model = best[0], best[3]
    reg, _ = filtered_states(model, Z)
    order = np.argsort(model.means_[:, 1]); rank = {s: i for i, s in enumerate(order)}
    return n, pd.Series([rank[s] for s in reg], index=feat.index)


def main():
    n, daily_reg = regimes(sys.argv[1])
    log = pd.read_csv(sys.argv[2]); ent = log[log["decision"] == "entry"].copy()
    ent["date"] = pd.to_datetime(ent["datetime"]).dt.normalize()
    ent["reg"] = ent["date"].map(daily_reg); ent["yr"] = pd.to_datetime(ent["datetime"]).dt.year
    e = ent.dropna(subset=["reg"]); pnl = e["pnl"].to_numpy(float); rg = e["reg"].to_numpy(int)
    yr = e["yr"].to_numpy()
    flat = pnl; fdd = dd(flat)
    print(f"n_states={n}; trades {len(e)}; FLAT P/L=${flat.sum():,.0f} DD=${fdd:,.0f} Ret/DD={rdd(flat):.2f}\n")

    def ramped(lo, hi):
        return np.linspace(lo, hi, n)[rg] * pnl

    # 1 + 2: scale robustness + equal-risk uplift
    print("=== ramp scale robustness + EQUAL-RISK uplift (P/L at max-DD held = flat) ===")
    for lo, hi in [(0.7, 1.3), (0.5, 1.5), (0.3, 1.7)]:
        s = ramped(lo, hi); r = rdd(s)
        eq_pnl = r * fdd                                   # P/L if we scale the book to match flat DD
        print(f"  ramp {lo}->{hi}: Ret/DD {r:.2f}  (raw P/L ${s.sum():,.0f} DD ${dd(s):,.0f}) | "
              f"EQUAL-RISK P/L ${eq_pnl:,.0f}  (vs flat ${flat.sum():,.0f}, +${eq_pnl-flat.sum():,.0f})")

    # 3: OOS holdout — decide ordering on 2024-25, apply fixed ramp to 2026
    lo, hi = 0.5, 1.5
    is_mask = yr < 2026; oos_mask = yr == 2026
    print("\n=== OOS holdout (ramp fixed a-priori; 2026 held out) ===")
    for name, m in [("2024-25 (in-sample)", is_mask), ("2026 (OOS)", oos_mask)]:
        s = ramped(lo, hi)
        print(f"  {name}: flat Ret/DD {rdd(flat[m]):.2f} -> ramp {rdd(s[m]):.2f}  "
              f"({'HELPS' if rdd(s[m])>rdd(flat[m]) else 'hurts'})")

    # 4: random-regime control on 0.5->1.5, equal-risk
    ramp = np.linspace(lo, hi, n); real = rdd(ramp[rg] * pnl); null = []
    for _ in range(2000):
        null.append(rdd(RNG.permutation(ramp)[rg] * pnl))
    null = np.array(null)
    print(f"\n=== random-regime control (0.5->1.5) ===")
    print(f"  Ret/DD {real:.2f} beats {100*(null<real).mean():.0f}% of random regime->size maps (median {np.median(null):.2f})")
    print(f"\nPROMOTE verdict: at EQUAL risk the ramp earns +${rdd(ramp[rg]*pnl)*fdd-flat.sum():,.0f} more; "
          f"holds OOS {'yes' if rdd((ramp[rg]*pnl)[oos_mask])>rdd(flat[oos_mask]) else 'no'}; beats {100*(null<real).mean():.0f}% of random.")


if __name__ == "__main__":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass
    main()
