"""SIZING · Z1 — the Kelly fraction on OUR ledgers, and how uncertain it is.

SIZE-01 gave the formula f* = (B*p - q)/B and its single loudest warning: Kelly is ~10-20x more sensitive
to the EDGE (p) than to variance, and our p is estimated on a finite, fluke-window ledger. So the number
that matters is not just f* but the CONFIDENCE INTERVAL on f* — how far it moves across the sampling
uncertainty in p. This computes both, on the actual NQ champion trades.

Two estimates of full Kelly:
  * binary formula  f* = (B*p - q)/B, with realized p and B = mean-win / mean-loss.
  * numerical (dispersion-aware)  f* = argmax_f  mean( log(1 + f * r_i) ),  r_i = pnl_points_i / stop_pts.
    Per SIZE-01 K5 (Jensen), the dispersion-aware f* is <= the binary one — it is the honest number.
f = fraction of capital RISKED per trade (a full stop-out loses f * capital).

Then BOOTSTRAP the ledger to get the 95% CI on f* — the parameter-safety argument for sitting well below
full Kelly, before any tail haircut (which K6 says must be a further cut + a hard exposure cap).

  WSH_DATA_BASE=/home/dev/Mulham/wsg-h python3 -u optimize/fundamentals/study_kelly.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from optimize import data, signals                               # noqa: E402
from optimize.fast_engine import fast_backtest, signals_to_int   # noqa: E402
from perf._common import champion_preset                         # noqa: E402

TFS = ["4h", "2h", "1h", "15m", "5m", "2m"]
STOP = 40.0
FGRID = np.linspace(0.001, 0.95, 400)


def num_kelly(r):
    """argmax_f mean(log(1+f*r)) on a grid; returns f* and the growth at f*."""
    g = np.array([np.mean(np.log1p(f * r)) for f in FGRID])
    i = int(np.argmax(g))
    return (FGRID[i], g[i]) if g[i] > 0 else (0.0, 0.0)          # f*=0 if no positive-growth fraction


def trades(tf):
    df, df1, box, vf, n = data.load_inputs(tf, instrument="NQ")
    p = champion_preset(tf)
    sig = signals_to_int(signals.decision_signals(df, box))
    gate = vf <= float(np.percentile(vf[:n], float(p.get("gate_pct", 60))))
    F = fast_backtest(df["Date"].to_numpy(), df["Close"].to_numpy(float), sig, gate,
                      df1["Date"].to_numpy(), df1["High"].to_numpy(float), df1["Low"].to_numpy(float),
                      df1["Close"].to_numpy(float), float(p.get("sl_soft_points", 30)), STOP,
                      float(p.get("tp_hard_points", 60)), bool(p.get("flip_entry_direction", False)))
    return np.array([t["pnl_points"] for t in F], float)


def main() -> int:
    rng = np.random.default_rng(0)
    allr = []
    print(f"\nNQ champions · Kelly fraction f (= fraction of capital RISKED per trade) · stop {STOP:.0f}pt\n")
    print(f"  {'tf':>4} {'n':>5} {'win%':>6} {'B(w/l)':>7} {'binary f*':>10} {'numeric f*':>11} "
          f"{'f* 95% CI':>18} {'half':>6} {'quarter':>8}")
    for tf in TFS:
        try:
            pnl = trades(tf)
        except Exception as e:                                    # noqa: BLE001
            print(f"  {tf:>4} FAIL {str(e)[:40]}"); continue
        r = pnl / STOP                                            # normalized by risk
        allr.append(r)
        p_ = float((r > 0).mean())
        w = r[r > 0].mean() if (r > 0).any() else 0.0
        l = -r[r < 0].mean() if (r < 0).any() else 1.0
        B = w / l
        fbin = max(0.0, (B * p_ - (1 - p_)) / B)
        fnum, _ = num_kelly(r)
        boot = np.array([num_kelly(rng.choice(r, len(r), replace=True))[0] for _ in range(2000)])
        lo, hi = np.percentile(boot, [2.5, 97.5])
        print(f"  {tf:>4} {len(r):>5} {100*p_:>5.1f}% {B:>7.2f} {100*fbin:>9.1f}% {100*fnum:>10.1f}% "
              f"  [{100*lo:>4.1f}%, {100*hi:>4.1f}%] {100*fnum/2:>5.1f}% {100*fnum/4:>7.1f}%")

    R = np.concatenate(allr)
    p_ = float((R > 0).mean()); w = R[R > 0].mean(); l = -R[R < 0].mean(); B = w / l
    fbin = max(0.0, (B * p_ - (1 - p_)) / B); fnum, _ = num_kelly(R)
    boot = np.array([num_kelly(rng.choice(R, len(R), replace=True))[0] for _ in range(3000)])
    lo, hi = np.percentile(boot, [2.5, 97.5])
    exp_pts = R.mean() * STOP
    print(f"\n  POOLED n={len(R)}  win {100*p_:.1f}%  B={B:.2f}  expectancy {exp_pts:+.1f} pts/trade "
          f"(${exp_pts*20:+.0f})")
    print(f"  full Kelly f*: binary {100*fbin:.1f}%  numeric {100*fnum:.1f}%  95% CI [{100*lo:.1f}%, {100*hi:.1f}%]")

    print("\n" + "=" * 92)
    print("READ — what fraction should we actually risk per trade?")
    print("=" * 92)
    print(f"  full Kelly (numeric)  : {100*fnum:.1f}% of capital risked per trade  <- the CEILING, never exceed")
    print(f"  half-Kelly            : {100*fnum/2:.1f}%   (keeps ~75% of growth, cuts 50%-drawdown prob to ~12.5%)")
    print(f"  quarter-Kelly         : {100*fnum/4:.1f}%   (edge-uncertainty safe — K3: mean-error dominates)")
    print(f"  f* 95% CI lower bound : {100*lo:.1f}%   <- parameter-safety floor; sit at/below this for the edge alone")
    print(f"\n  Then a FURTHER tail/gap haircut + a HARD exposure cap (K6, catastrophe principle) — not yet")
    print(f"  applied here. The honest endpoint (tiny fluke-window edge + fat tail): a SMALL fixed fraction")
    print(f"  (<= quarter-Kelly, and bounded by the CI floor) with a hard contract cap. Next: Z2 = simulate")
    print(f"  gap-through-stop fills (D2/D3 tail) to read off the tail-safe fraction; Z3 = fixed-frac vs vol-target.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
