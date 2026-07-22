"""GAP-AWARE FILLS — the NET impact on every champion (old model vs new).

study_gap_fills.py measured only the STOP side (money the old model never charged). This measures the
NET effect the engine actually produces, which also includes the other direction: a gap past the
TAKE-PROFIT fills BETTER. Reporting only the stop side would overstate the damage.

  OLD: gap_fills=False — every hard SL/TP fills exactly at the line (the fill may never have existed)
  NEW: gap_fills=True  — if the bar OPENED beyond the line, fill at the OPEN

Same signals, same gate, same champion parameters. Only the fill model differs.

  WSH_DATA_BASE=... python3 -u optimize/fundamentals/study_gap_impact.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from optimize import data, signals                                      # noqa: E402
from optimize.fast_engine import fast_backtest, signals_to_int          # noqa: E402
from optimize.fundamentals.champion_params import champion_stops        # noqa: E402
from perf._common import champion_preset                                # noqa: E402

TFS = ["4h", "2h", "1h", "15m", "5m", "2m"]
PV = 20.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--instrument", default="NQ")
    a = ap.parse_args()

    print("\nGAP-AWARE FILLS — net effect on each champion (old fill-at-line vs new fill-at-open)\n")
    print(f"  {'tf':>4} {'trades':>7} {'OLD $':>12} {'NEW $':>12} {'delta $':>11} {'delta %':>8} "
          f"{'$/trade':>9}")
    print("-" * 72)

    tot_old = tot_new = 0.0
    tot_n = 0
    for tf in TFS:
        df, df1, box, vf, n = data.load_inputs(tf, instrument=a.instrument)
        p = champion_preset(tf)
        ss, sh, tp, flip = champion_stops(p, tf)
        sig = signals_to_int(signals.decision_signals(df, box))
        gate = vf <= float(np.percentile(vf[:n], float(p["gate_pct"])))
        DD, DC = df["Date"].to_numpy(), df["Close"].to_numpy(float)
        MD = df1["Date"].to_numpy()
        MH, ML = df1["High"].to_numpy(float), df1["Low"].to_numpy(float)
        MC, MO = df1["Close"].to_numpy(float), df1["Open"].to_numpy(float)

        def run(gap):
            F = fast_backtest(DD, DC, sig, gate, MD, MH, ML, MC, ss, sh, tp, flip,
                              m_open=MO, gap_fills=gap)
            return np.array([t["pnl_points"] for t in F], float)

        old = run(False)
        new = run(True)
        assert len(old) == len(new), "trade COUNT must not change — only the fill price does"
        o_usd, n_usd = float(old.sum()) * PV, float(new.sum()) * PV
        d = n_usd - o_usd
        tot_old += o_usd; tot_new += n_usd; tot_n += len(new)
        pct = 100.0 * d / abs(o_usd) if o_usd else 0.0
        print(f"  {tf:>4} {len(new):>7} {o_usd:>12,.0f} {n_usd:>12,.0f} {d:>11,.0f} {pct:>7.1f}% "
              f"{d/max(1,len(new)):>9.2f}")

    print("-" * 72)
    d = tot_new - tot_old
    pct = 100.0 * d / abs(tot_old) if tot_old else 0.0
    print(f"  {'ALL':>4} {tot_n:>7} {tot_old:>12,.0f} {tot_new:>12,.0f} {d:>11,.0f} {pct:>7.1f}% "
          f"{d/max(1,tot_n):>9.2f}")

    print("\n" + "=" * 72)
    print("READ")
    print("=" * 72)
    print("  Trade COUNT is identical by construction — the gap rule changes the FILL PRICE, never")
    print("  whether or when a trade exits. So this is a clean like-for-like P&L comparison.")
    print("  The delta is NET: stops that gapped cost more, take-profits that gapped paid more.")
    print("  This is the honest cost of the old optimism, and every historical P&L figure in the")
    print("  project was overstated by roughly this amount.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
