"""GAP FILLS — does the backtest understate stop losses when price GAPS through the stop?

THE QUESTION (user, 2026-07-20). When there is a gap between the close of one candle and the open of the
next, and that gap jumps straight past our stop line: does the engine book the loss at the STOP PRICE or
at the REAL price we would actually have been filled at?

THE ANSWER FROM THE CODE — both engines fill AT THE LINE:

    engine.py:397        if m_low <= sh:  exit_reason, fill = 'STOP_LOSS_HARD', sh
    fast_engine.py:13    "long : SLh low<=ep-slh(fill line)"
    fast_engine.py:211   fill = float(cl[ti]) if line is None else float(line)

The TRIGGER is "the bar's extreme touched the line"; the FILL is the line itself. So if a 1-minute bar
OPENS already beyond the stop, the backtest still books the loss at the stop price — a fill that was
never available. Real execution would fill at (approximately) the open.

THIS SCRIPT MEASURES THE SIZE OF THAT OPTIMISM. For every STOP_LOSS_HARD exit we locate the 1-minute bar
that triggered it and ask: was the bar's OPEN already past the stop line?

    long  : gapped iff open < sl_hard_line   (realistic fill = open, WORSE than the line)
    short : gapped iff open > sl_hard_line

Realistic fill = the worse of (line, open). The difference is money the backtest never charged us.

WHY IT MATTERS: Z2 (risk-of-ruin) had to ASSUME a gap rate because it had never been measured — its own
output says "the gap rate g and cap are ASSUMPTIONS from D2/D3, not measured live fills". This converts
that assumption into a measurement. It also bounds how optimistic every P&L figure in the project is.

NOT MODELLED HERE (so the numbers below are a FLOOR, not a ceiling): real slippage beyond the open,
spread, and partial fills. A real fill is at best the open, usually slightly worse.

  WSH_DATA_BASE=... python3 -u optimize/fundamentals/study_gap_fills.py
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
PV = 20.0          # NQ $/point


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--instrument", default="NQ")
    a = ap.parse_args()

    print("\nGAP-THROUGH-THE-STOP — how much does 'fill at the line' understate our losses?\n")
    print(f"  {'tf':>4} {'stops':>6} {'gapped':>7} {'%':>6} {'mean slip':>10} {'worst':>8} "
          f"{'$ missed':>11} {'$/trade':>9}")
    print("-" * 74)

    tot_missed = 0.0
    tot_trades = 0
    tot_stops = 0
    tot_gapped = 0
    worst_all = 0.0

    for tf in TFS:
        df, df1, box, vf, n = data.load_inputs(tf, instrument=a.instrument)
        p = champion_preset(tf)
        ss, sh, tp, flip = champion_stops(p, tf)
        sig = signals_to_int(signals.decision_signals(df, box))
        gate = vf <= float(np.percentile(vf[:n], float(p["gate_pct"])))

        MD = df1["Date"].to_numpy()
        MO = df1["Open"].to_numpy(float)
        F = fast_backtest(df["Date"].to_numpy(), df["Close"].to_numpy(float), sig, gate,
                          MD, df1["High"].to_numpy(float), df1["Low"].to_numpy(float),
                          df1["Close"].to_numpy(float), ss, sh, tp, flip)

        slips = []
        n_stops = 0
        for t in F:
            if t["exit_reason"] != "STOP_LOSS_HARD":
                continue
            n_stops += 1
            k = int(np.searchsorted(MD, np.datetime64(t["exit_time"]), side="left"))
            if not (0 <= k < len(MO)):
                continue
            o = float(MO[k])                      # the OPEN of the bar that triggered the stop
            line = float(t["exit_price"])         # what the backtest booked (= the stop line)
            if t["direction"] == "long" or t["direction"] == 1:
                slip = line - o if o < line else 0.0        # open BELOW the line => worse for a long
            else:
                slip = o - line if o > line else 0.0        # open ABOVE the line => worse for a short
            if slip > 0:
                slips.append(slip)

        s = np.array(slips) if slips else np.zeros(0)
        missed = float(s.sum()) * PV
        pct = 100.0 * len(s) / n_stops if n_stops else 0.0
        worst = float(s.max()) if len(s) else 0.0
        tot_missed += missed
        tot_trades += len(F)
        tot_stops += n_stops
        tot_gapped += len(s)
        worst_all = max(worst_all, worst)
        print(f"  {tf:>4} {n_stops:>6} {len(s):>7} {pct:>5.1f}% {(s.mean() if len(s) else 0):>10.2f} "
              f"{worst:>8.2f} {missed:>11,.0f} {missed/max(1,len(F)):>9.2f}")

    print("-" * 74)
    pct = 100.0 * tot_gapped / tot_stops if tot_stops else 0.0
    print(f"  {'ALL':>4} {tot_stops:>6} {tot_gapped:>7} {pct:>5.1f}% {'':>10} {worst_all:>8.2f} "
          f"{tot_missed:>11,.0f} {tot_missed/max(1,tot_trades):>9.2f}")

    print("\n" + "=" * 74)
    print("READ")
    print("=" * 74)
    print("  'gapped' = the 1-minute bar that triggered the stop had ALREADY OPENED past the stop line,")
    print("  so the backtest's fill AT the line was never actually available.")
    print("  '$ missed' = what those fills would have cost at the bar's open instead — money the")
    print("  backtest never charged. It is a FLOOR: real slippage beyond the open is not modelled.")
    print("  '$/trade' spreads that across EVERY trade, so it is directly comparable to the")
    print("  expectancy figure (~$21/trade on the corrected ledger).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
