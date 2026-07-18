#!/usr/bin/env python3
"""Experiment 3: does the high-vol VETO help a vol-HURT strategy?

The vol veto HURT our breakout (vol-seeking). Hypothesis: on a mean-reversion strategy (which volatility
HURTS — fading a strong move gets run over), the SAME causal high-vol veto should HELP. If so, the earlier
NO-GOs were strategy-specific, not a flaw in the vol signal.

Build a simple causal NQ 1h mean-reversion baseline (fade 2-sigma deviations from a 20-bar mean, exit on
reversion or a max hold), then apply the same causal p85 VolGate on each entry's realized volatility.

Run:  python3 meanrev_experiment.py <NQ_1h.csv>
"""
from __future__ import annotations
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, "/home/dev/Mulham/tfm-repro/vendor-baseline")
from gate_service import VolGate, _stats

PV, MA, ENTRY_Z, EXIT_Z, MAXHOLD, COST = 20.0, 20, 2.0, 0.5, 24, 5.0


def build_meanrev(csv):
    df = pd.read_csv(csv); df.columns = [c.strip().lower() for c in df.columns]
    df["dt"] = pd.to_datetime(df["datetime"]); df = df.sort_values("dt").reset_index(drop=True)
    c = df["close"].to_numpy(float)
    ma = pd.Series(c).rolling(MA).mean().to_numpy()
    sd = pd.Series(c).rolling(MA).std().to_numpy()
    z = (c - ma) / sd
    rv = pd.Series(np.log(c)).diff().rolling(MA).std().to_numpy()   # causal realized vol
    trades = []
    i = MA
    n = len(c)
    while i < n - 1:
        if np.isfinite(z[i]) and abs(z[i]) >= ENTRY_Z:
            direction = -1 if z[i] > 0 else 1        # fade: short if above, long if below
            entry = c[i]; j = i + 1
            while j < n and j - i < MAXHOLD and abs(z[j]) > EXIT_Z:
                j += 1
            j = min(j, n - 1)
            pnl = direction * (c[j] - entry) * PV - COST
            trades.append((df["dt"].iloc[i], pnl, rv[i - 1] if i - 1 >= 0 else np.nan))
            i = j + 1
        else:
            i += 1
    return pd.DataFrame(trades, columns=["dt", "pnl", "rv"])


def main():
    t = build_meanrev(sys.argv[1])
    t = t[t["dt"] >= pd.Timestamp("2015-01-01")].reset_index(drop=True)   # enough trades
    pnl = t["pnl"].to_numpy(float); rv = t["rv"].to_numpy(float)
    yr = t["dt"].dt.year.to_numpy()
    base = _stats(pnl)
    print(f"mean-reversion baseline: {len(t)} trades {t['dt'].min().date()}..{t['dt'].max().date()}")
    print(f"  UNGATED: P/L=${base['pnl']:,.0f} DD=${base['dd']:,.0f} Ret/DD={base['ret_dd']:.2f} win={base['win']:.0f}%")
    # same causal p85 vol veto (single VolGate instance!)
    g = VolGate(pct=85.0)
    keep = np.array([g.allow(x if np.isfinite(x) else None) for x in rv])
    gated = _stats(pnl[keep])
    print(f"  + HIGH-VOL VETO p85: P/L=${gated['pnl']:,.0f} DD=${gated['dd']:,.0f} Ret/DD={gated['ret_dd']:.2f} "
          f"(vetoed {len(pnl)-keep.sum()})  {'HELPS' if gated['ret_dd']>base['ret_dd'] else 'HURTS'}")
    print("\nper-year Ret/DD  ungated -> gated:")
    for y in sorted(set(yr)):
        m = yr == y; b = _stats(pnl[m]); gg = _stats(pnl[m & keep])
        print(f"  {y}: {b['ret_dd']:.2f} -> {gg['ret_dd']:.2f}  ({'+' if gg['ret_dd']>b['ret_dd'] else ''}{gg['ret_dd']-b['ret_dd']:.2f})")


if __name__ == "__main__":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass
    main()
