"""THE COUNTERFACTUAL: what if we had IGNORED the stop-loss and held on?

Task #3, Phase A. The user's thesis, stated exactly: the static stop "took the loss and exited, while
continuing with the contract and abandoning the stop loss (for only this minute) will make the exit
profitable." The 2025-03-07 payrolls case is the poster child: stopped out at -$800, and the market
closed the SAME MINUTE where holding would have paid +$2,160.

The excursion study (study_excursions.py) argued AGAINST this: heat separates winners from losers with
only a 1.4% overlap, so a 40-point adverse move is a genuine loser 98.6% of the time.

BUT THAT ARGUMENT WAS TOO BROAD, and this study exists because of it. "Heat separates winners from
losers" says the FIXED stop is well placed. It does NOT say that among the trades that DID get stopped,
there is no recoverable subset. That is a narrower question and it is the one that decides Task #3.

So: for every hard-stopped trade, replay it with the stop DISABLED and see what actually happened next.

THE RULES OF THE COUNTERFACTUAL (stated before running, so they cannot be tuned to flatter the result):
  * We keep the take-profit exactly as it is.
  * We keep the time cap / end-of-day exit exactly as they are.
  * "Ignoring the stop" is NOT unbounded risk. A DISASTER FLOOR at `floor_mult` x the original stop
    distance always applies. Without it we would be measuring a martingale, not a strategy.
  * If nothing resolves by the end of the scan window, we mark the trade unresolved and EXCLUDE it —
    we do not silently count an open position as a win.

WHAT THIS DOES NOT DO. This is a SINGLE-TRADE counterfactual. It ignores sequence effects: a trade held
longer may block the next entry, so the true portfolio effect differs. That is what the full engine
implementation (Phase C) measures. This study sizes the PRIZE; it does not bank it.

  python3 optimize/fundamentals/study_stop_counterfactual.py --tf 4h --floor-mult 3
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from optimize import data, instruments, signals               # noqa: E402
from optimize.fast_engine import fast_backtest, signals_to_int    # noqa: E402
from perf._common import champion_preset                      # noqa: E402
from optimize.fundamentals.champion_params import champion_stops  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tf", default="4h")
    ap.add_argument("--instrument", default="NQ")
    ap.add_argument("--floor-mult", type=float, default=3.0,
                    help="disaster floor as a multiple of the original stop distance")
    ap.add_argument("--max-hold-1m", type=int, default=1440,
                    help="give up after this many 1-min bars past the stop (1440 = one day)")
    a = ap.parse_args()

    df, df1, box, vf, n = data.load_inputs(a.tf, instrument=a.instrument)
    p = champion_preset(a.tf)
    sl_soft, sl_hard, tp, _flip = champion_stops(p)
    gp = float(p.get("gate_pct", 60))
    pv = instruments.point_value(a.instrument)

    sig = signals_to_int(signals.decision_signals(df, box))
    gate = vf <= float(np.percentile(vf[:n], gp))
    MD = df1["Date"].to_numpy()
    MH = df1["High"].to_numpy(float)
    ML = df1["Low"].to_numpy(float)
    MC = df1["Close"].to_numpy(float)
    MO = df1["Open"].to_numpy(float)

    F = fast_backtest(df["Date"].to_numpy(), df["Close"].to_numpy(float), sig, gate,
                      MD, MH, ML, MC, sl_soft, sl_hard, tp,
                      _flip, track_excursions=True, m_open=MO)

    stopped = [t for t in F if t["exit_reason"] == "STOP_LOSS_HARD"]
    print(f"\n{a.instrument} {a.tf}  ·  SL {sl_soft}/{sl_hard}  TP {tp}  ·  ${pv}/pt")
    print(f"{len(F)} trades, of which {len(stopped)} were killed by the HARD STOP")
    print(f"realized on those: ${sum(t['pnl_points'] for t in stopped)*pv:,.0f}")
    print(f"\ncounterfactual rules: TP kept · disaster floor = {a.floor_mult:.0f}x stop "
          f"({a.floor_mult*sl_hard:.0f} pts) · give up after {a.max_hold_1m} 1-min bars\n")

    rows = []
    for t in stopped:
        ep = float(t["entry_price"])
        long = t["direction"] == "long"
        # the bar the stop fired on = entry bar + (bars_1m - 1)
        e0 = int(np.searchsorted(MD, np.datetime64(t["entry_time"]), side="left"))
        s0 = e0 + int(t["bars_1m"]) - 1
        hi_i = min(s0 + a.max_hold_1m, len(MC) - 1)
        if s0 >= hi_i:
            continue

        tp_line = ep + tp if long else ep - tp
        floor_line = (ep - a.floor_mult * sl_hard) if long else (ep + a.floor_mult * sl_hard)

        H, L = MH[s0 + 1:hi_i + 1], ML[s0 + 1:hi_i + 1]
        hit_tp = np.flatnonzero(H >= tp_line) if long else np.flatnonzero(L <= tp_line)
        hit_fl = np.flatnonzero(L <= floor_line) if long else np.flatnonzero(H >= floor_line)
        i_tp = int(hit_tp[0]) if len(hit_tp) else 10 ** 9
        i_fl = int(hit_fl[0]) if len(hit_fl) else 10 ** 9

        if i_tp == 10 ** 9 and i_fl == 10 ** 9:
            outcome, cf = "unresolved", None           # excluded — never counted as a win
        elif i_tp <= i_fl:
            outcome, cf = "RECOVERED to TP", (tp if long else tp)
        else:
            outcome, cf = "hit the DISASTER FLOOR", -(a.floor_mult * sl_hard)

        rows.append({"outcome": outcome, "cf_points": cf,
                     "real_points": float(t["pnl_points"]),
                     "mfe": float(t["mfe_points"]), "bars": int(t["bars_1m"])})

    rec = [r for r in rows if r["outcome"].startswith("RECOVERED")]
    flo = [r for r in rows if r["outcome"].startswith("hit the DISASTER")]
    unr = [r for r in rows if r["outcome"] == "unresolved"]
    resolved = rec + flo

    print("=" * 76)
    print("WHAT HAPPENED IF WE IGNORED THE STOP")
    print("=" * 76)
    print(f"  RECOVERED all the way to take-profit : {len(rec):>4}  ({100*len(rec)/max(len(rows),1):>5.1f}%)")
    print(f"  fell through the disaster floor      : {len(flo):>4}  ({100*len(flo)/max(len(rows),1):>5.1f}%)")
    print(f"  unresolved within {a.max_hold_1m} bars (EXCLUDED)  : {len(unr):>4}")
    print()

    if not resolved:
        print("  nothing resolved — cannot evaluate.")
        return 1

    real = sum(r["real_points"] for r in resolved) * pv
    cf = sum(r["cf_points"] for r in resolved) * pv
    print(f"  on the {len(resolved)} RESOLVED trades:")
    print(f"    what we ACTUALLY made (stop honoured): ${real:>12,.0f}")
    print(f"    what we WOULD have made (stop ignored): ${cf:>12,.0f}")
    print(f"    difference:                            ${cf-real:>+12,.0f}")
    print()

    # The break-even question: how often must it recover to be worth it?
    win_pts = tp + sl_hard                    # +60 instead of -40 => +100 swing
    lose_pts = a.floor_mult * sl_hard - sl_hard   # -120 instead of -40 => -80 swing
    be = lose_pts / (win_pts + lose_pts)
    actual = len(rec) / len(resolved)
    print(f"  BREAK-EVEN recovery rate needed: {100*be:.1f}%")
    print(f"    (recovering turns -{sl_hard:.0f} into +{tp:.0f} = +{win_pts:.0f} pts;")
    print(f"     flooring turns -{sl_hard:.0f} into -{a.floor_mult*sl_hard:.0f} = -{lose_pts:.0f} pts)")
    print(f"  ACTUAL recovery rate:            {100*actual:.1f}%")
    print()
    if actual > be:
        print(f"  ✅ {100*actual:.1f}% > {100*be:.1f}% — ignoring the stop is PROFITABLE in this sample.")
        print("     NOT YET A RESULT: needs a causal rule (we cannot ignore EVERY stop — we must")
        print("     decide AT the stop bar), a null test, and out-of-sample. Phase B.")
    else:
        print(f"  ❌ {100*actual:.1f}% < {100*be:.1f}% — ignoring the stop LOSES money in this sample.")
        print("     Blanket 'ignore the stop' is dead. A SELECTIVE rule could still work, but it")
        print("     would have to beat this base rate by a wide margin. Phase B decides.")

    # Was 'was it winning first?' predictive of recovery? (a free first look at Phase B)
    print()
    print("=" * 76)
    print("FIRST LOOK AT A PREDICTOR — does peak profit (MFE) before the stop predict recovery?")
    print("=" * 76)
    for lo_, hi_ in [(0, 10), (10, 20), (20, 30), (30, 1000)]:
        sub = [r for r in resolved if lo_ <= r["mfe"] < hi_]
        if not sub:
            continue
        rr = sum(1 for r in sub if r["outcome"].startswith("RECOVERED")) / len(sub)
        print(f"  trades whose peak profit was {lo_:>3}-{hi_ if hi_<1000 else '+':>4} pts: "
              f"n={len(sub):>4}   recovered {100*rr:>5.1f}%   "
              f"{'PROFITABLE' if rr > be else 'loses'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
