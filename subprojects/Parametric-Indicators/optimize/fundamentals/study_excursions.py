"""What the excursion tracker reveals — the empirical case FOR (or against) a dynamic stop-loss.

Until now the engine only knew a trade's P/L at exit. It could not answer the question that matters:
"was this loss a genuine adverse move, or did we give back a winner?" Now it can.

The four questions, in the order that decides whether Task #3 is even worth building:

  Q1. GIVEBACK — of our LOSING trades, how many were in PROFIT first, and by how much?
      If losers never go up, there is nothing to protect and a dynamic stop is pointless.

  Q2. HEAT — of our WINNING trades, how close did they come to being stopped out?
      This is the crux. If winners routinely take -35 points of heat against a -40 stop, then the
      stop is sitting right in the noise and we are killing winners by a hair. If winners barely go
      against us at all, the stop is well placed and "ignore the stop" would just be a licence to
      turn small losses into big ones.

  Q3. THE COUNTERFACTUAL — for the trades that were STOPPED OUT, what would have happened if we had
      ignored the stop and simply held to the take-profit or the time cap? This is the direct dollar
      value of Task #3. It is also the number most likely to be a mirage, so it gets tested honestly.

  Q4. IS THE STOP EVEN IN THE RIGHT PLACE? Compare the MAE distribution of winners vs losers. If they
      overlap heavily, NO fixed stop can separate them — which is the mathematical argument for a
      dynamic one.

  python3 optimize/fundamentals/study_excursions.py --tf 4h
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from optimize import data, instruments, signals              # noqa: E402
from optimize.fast_engine import fast_backtest, signals_to_int   # noqa: E402
from perf._common import champion_preset                     # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tf", default="4h")
    ap.add_argument("--instrument", default="NQ")
    a = ap.parse_args()

    df, df1, box, vf, n = data.load_inputs(a.tf, instrument=a.instrument)
    p = champion_preset(a.tf)
    sl_hard = float(p.get("sl_hard_points", 40))
    sl_soft = float(p.get("sl_soft_points", 30))
    tp = float(p.get("tp_hard_points", 60))
    gp = float(p.get("gate_pct", 60))
    pv = instruments.point_value(a.instrument)

    sig = signals_to_int(signals.decision_signals(df, box))
    gate = vf <= float(np.percentile(vf[:n], gp))
    F = fast_backtest(df["Date"].to_numpy(), df["Close"].to_numpy(float), sig, gate,
                      df1["Date"].to_numpy(), df1["High"].to_numpy(float),
                      df1["Low"].to_numpy(float), df1["Close"].to_numpy(float),
                      sl_soft, sl_hard, tp, bool(p.get("flip_entry_direction", False)),
                      track_excursions=True)

    pnl = np.array([t["pnl_points"] for t in F])
    mfe = np.array([t["mfe_points"] for t in F])
    mae = np.array([t["mae_points"] for t in F])
    rsn = np.array([t["exit_reason"] for t in F])
    win, lose = pnl > 0, pnl < 0

    print(f"\n{a.instrument} {a.tf}  ·  champion SL {sl_soft}/{sl_hard} TP {tp}  ·  ${pv}/point")
    print(f"{len(F)} trades   ({win.sum()} winners, {lose.sum()} losers)\n")

    # ------------------------------------------------------------------ Q1 GIVEBACK
    print("=" * 78)
    print("Q1 — GIVEBACK: were our LOSERS ever winning?")
    print("=" * 78)
    for thr in [10, 20, 30, 40, 60]:
        k = int((mfe[lose] >= thr).sum())
        print(f"  losers that were EVER >= +{thr:>3.0f} pts (${thr*pv:>7,.0f}) in profit: "
              f"{k:>4} / {int(lose.sum())}  ({100*k/max(lose.sum(),1):>5.1f}%)")
    gb = mfe[lose]
    print(f"\n  median peak profit of a LOSING trade: {np.median(gb):>6.1f} pts  (${np.median(gb)*pv:,.0f})")
    print(f"  total profit reached and then given back: "
          f"${gb.sum()*pv:,.0f}  across {int(lose.sum())} losers")

    # ------------------------------------------------------------------ Q2 HEAT
    print()
    print("=" * 78)
    print("Q2 — HEAT: how close did our WINNERS come to being stopped out?")
    print("=" * 78)
    heat = -mae[win]                       # positive points of adverse movement
    print(f"  the hard stop sits at {sl_hard:.0f} pts of heat.")
    for q in [50, 75, 90, 95, 99]:
        print(f"    {q}th percentile of winner heat: {np.percentile(heat, q):>6.1f} pts")
    near = int((heat >= sl_hard * 0.75).sum())
    print(f"\n  winners that came within 25% of the stop (>= {0.75*sl_hard:.0f} pts heat): "
          f"{near} / {int(win.sum())}  ({100*near/max(win.sum(),1):.1f}%)")
    if near / max(win.sum(), 1) > 0.10:
        print("  ⇒ a meaningful slice of winners nearly died. The stop IS in the noise.")
    else:
        print("  ⇒ winners rarely approach the stop. It is NOT sitting in the noise —")
        print("    which weakens the case for 'ignore the stop' (it would mostly just enlarge losses).")

    # ------------------------------------------------------------------ Q4 SEPARABILITY
    print()
    print("=" * 78)
    print("Q4 — CAN ANY FIXED STOP SEPARATE WINNERS FROM LOSERS?")
    print("=" * 78)
    hw, hl = -mae[win], -mae[lose]
    print(f"  heat taken by WINNERS: median {np.median(hw):>6.1f}  mean {hw.mean():>6.1f} pts")
    print(f"  heat taken by LOSERS : median {np.median(hl):>6.1f}  mean {hl.mean():>6.1f} pts")
    # overlap: P(a random winner took MORE heat than a random loser)
    ov = float((hw[:, None] > hl[None, :]).mean())
    print(f"\n  P(a random WINNER took more heat than a random LOSER) = {ov:.3f}")
    print("    0.50 = the two are indistinguishable by heat alone (no fixed stop can separate them)")
    print("    0.00 = winners never go against us and losers always do (a perfect stop exists)")
    if ov > 0.25:
        print(f"  ⇒ {100*ov:.0f}% overlap. A FIXED stop CANNOT cleanly separate them. This is the")
        print("    mathematical case for a dynamic stop: the decision needs MORE than the price level.")
    else:
        print("  ⇒ low overlap — a fixed stop separates them well. Dynamic stop has little to add.")

    # ------------------------------------------------------------------ Q3 COUNTERFACTUAL
    print()
    print("=" * 78)
    print("Q3 — THE STOPPED-OUT TRADES: what were they doing?")
    print("=" * 78)
    st = rsn == "STOP_LOSS_HARD"
    if st.sum():
        print(f"  hard-stopped trades: {int(st.sum())}  "
              f"(${pnl[st].sum()*pv:,.0f} realized)")
        was_up = int((mfe[st] >= tp * 0.5).sum())
        print(f"  of those, {was_up} ({100*was_up/st.sum():.1f}%) had ALREADY been >= +{tp*0.5:.0f} pts up")
        print(f"  median peak profit before being stopped: {np.median(mfe[st]):.1f} pts")
    print()
    print("  NOTE: the true counterfactual ('what if we had ignored the stop?') requires re-running")
    print("  the engine with the stop disabled for those bars — that is Task #3, and it must be")
    print("  null-tested. This section only sizes the OPPORTUNITY; it does not claim the money.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
