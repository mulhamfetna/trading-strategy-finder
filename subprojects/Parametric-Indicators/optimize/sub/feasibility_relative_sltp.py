"""Stage 0 feasibility — is a RELATIVE SL/TP (= k · driver) more stable over time than absolute points?

The robustness thesis behind 'derived SL/TP': an absolute optimum like "SL = 150 pts" drifts as the market
changes (so it needs re-optimizing), but a RATIO "SL = k · driver" should stay ~constant if the driver
explains the drift. This script tests that on the existing rolling-3-month sub_optimizer table: for each
candidate driver D and each target (best_sl_soft/sl_hard/tp), it compares the dispersion (coefficient of
variation, CV = std/mean) of the RATIO target/D across windows against the CV of the raw absolute target.

  ratio CV << absolute CV  ⇒  the ratio is the stable quantity ⇒ relative sizing self-recalibrates ⇒ GO.

Drivers tested (all available per window in the table): atr_mean, harv_mean (HAR-RV vf proxy), price_mean.
Seed k = mean(target/D) over windows = the ConstantPolicy starting coefficients for Stage 1/2.
GO/NO-GO is printed; no engine change, no look-ahead (this is a property of the labels themselves).
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DEFAULT_TABLE = HERE / "results" / "subopt_table_sl40-175_tp40-250.csv"   # guarded = operationally sensible
DRIVERS = {"atr": "atr_mean", "harv(vf)": "harv_mean", "price": "price_mean"}
TARGETS = {"sl_soft": "best_sl_soft", "sl_hard": "best_sl_hard", "tp": "best_tp"}


def cv(x: np.ndarray) -> float:
    x = np.asarray(x, float); m = x.mean()
    return float(x.std(ddof=1) / m) if m != 0 else float("nan")


def main() -> int:
    table = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_TABLE
    df = pd.read_csv(table)
    n_all = len(df)
    clean = df[df.get("bound_clipped", 0) == 0] if "bound_clipped" in df else df
    print(f"table: {table.name}  |  windows: {n_all} total, {len(clean)} with bound_clipped==0 (used)")
    print(f"span: {df['anchor'].iloc[0]} … {df['anchor'].iloc[-1]}\n")

    rows = []
    for tname, tcol in TARGETS.items():
        abs_cv = cv(clean[tcol].to_numpy())
        best = None
        for dname, dcol in DRIVERS.items():
            k = clean[tcol].to_numpy(float) / clean[dcol].to_numpy(float)
            r = float(np.corrcoef(clean[tcol], clean[dcol])[0, 1])
            ratio_cv = cv(k)
            # time-drift: mean k first-half vs second-half (relative change)
            h = len(k) // 2
            drift = abs(k[h:].mean() - k[:h].mean()) / k.mean() if k.mean() else float("nan")
            rows.append((tname, dname, abs_cv, ratio_cv, abs_cv / ratio_cv if ratio_cv else float("nan"),
                         r, float(k.mean()), drift))
            if best is None or ratio_cv < best[1]:
                best = (dname, ratio_cv, float(k.mean()), drift)
        print(f"[{tname}]  absolute CV = {abs_cv:.3f}   (how much the raw optimal {tname} drifts)")
        for (tn, dn, acv, rcv, imp, r, km, dr) in [x for x in rows if x[0] == tname]:
            flag = "  <= best" if dn == best[0] else ""
            print(f"    /{dn:9s}  ratioCV={rcv:.3f}  (×{imp:4.2f} tighter)  r={r:+.2f}  k̄={km:.3f}  drift={dr*100:4.1f}%{flag}")
        print(f"    -> best driver for {tname}: {best[0]}  (seed k={best[2]:.3f})\n")

    # GO/NO-GO: relative beats absolute for SL (the risk-critical line) by a clear margin, low drift.
    res = {t: min([x for x in rows if x[0] == t], key=lambda z: z[3]) for t in TARGETS}
    sl = res["sl_soft"]
    go = (sl[3] < sl[2]) and (sl[3] * 1.25 < sl[2]) and (sl[7] < 0.25)   # ratioCV<absCV, ≥25% tighter, drift<25%
    print("=" * 78)
    print(f"VERDICT: {'GO' if go else 'NO-GO / needs-thought'} — "
          f"sl_soft ratio is {'tighter' if sl[3] < sl[2] else 'NOT tighter'} than absolute "
          f"(ratioCV {sl[3]:.3f} vs absCV {sl[2]:.3f}), best driver={sl[1]}, half-split drift={sl[7]*100:.1f}%.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
