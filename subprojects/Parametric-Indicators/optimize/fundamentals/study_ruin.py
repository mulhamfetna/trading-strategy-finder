"""SIZING · Z2 — the TAIL/GAP haircut: what fraction survives a gap-through-the-stop?

Z1 gave the Kelly fraction from the BACKTEST ledger, where every stop-out loses exactly -40 (D1). But D3
showed that live, a single 1-min move can gap THROUGH the stop in a loud regime (blow-through ~9% of bars,
extreme moves to ~160 pts). K6 (SIZE-01): under fat tails, ruin comes from ONE such gap, so sizing must be
capped against a single catastrophic fill, not average variance — and no closed-form haircut exists, so we
simulate.

MODEL (transparent, stated assumptions from D2/D3):
  * base per-trade returns r = pnl_points / stop  (bootstrapped from the NQ champion ledger).
  * GAP OVERLAY: a fraction `g` of stop-outs gap through — their loss is multiplied by a Pareto(alpha=3)
    factor (>=1, matching the D2 tail index ~3), capped at `cap`x the stop (D3 extreme ~160pt = 4x a 40pt
    stop). So a gapped stop loses up to cap x the intended risk.
  * MONTE CARLO the equity path W_{t+1} = W_t*(1 + f*r_t) over N trades, many paths, per risk fraction f.
Read off the largest f holding P(ruin) below a threshold, and compare to Z1's Kelly (2.5%) / quarter (0.6%).

  WSH_DATA_BASE=/home/dev/Mulham/wsg-h python3 -u optimize/fundamentals/study_ruin.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from optimize import data, signals                               # noqa: E402
from optimize.fast_engine import fast_backtest, signals_to_int   # noqa: E402
from perf._common import champion_preset                         # noqa: E402
from optimize.fundamentals.champion_params import champion_stops, describe  # noqa: E402

STOP = 40.0
TFS = ["4h", "2h", "1h", "15m"]      # the champions with a real edge (Z1: 5m/2m ~0)
ALPHA = 3.0                          # D2 tail index
RUIN = 0.10                          # ruin = wealth falls below 10% of start
M, N = 4000, 1000                    # paths, trades per path


def ledger_returns(rng):
    r = []
    for tf in TFS:
        df, df1, box, vf, n = data.load_inputs(tf, instrument="NQ")
        p = champion_preset(tf)
        _SS, _SH, _TP, _FL = champion_stops(p, tf)   # STRICT — a missing stop must raise, never default
        print(describe(p, tf), flush=True)
        sig = signals_to_int(signals.decision_signals(df, box))
        gate = vf <= float(np.percentile(vf[:n], float(p.get("gate_pct", 60))))
        F = fast_backtest(df["Date"].to_numpy(), df["Close"].to_numpy(float), sig, gate,
                          df1["Date"].to_numpy(), df1["High"].to_numpy(float), df1["Low"].to_numpy(float),
                          df1["Close"].to_numpy(float), _SS, _SH,
                          _TP, _FL)
        r.append(np.array([t["pnl_points"] for t in F], float) / STOP)
    return np.concatenate(r)


def simulate(base, f, g, cap, rng):
    """M paths x N trades; apply gap overlay to stop-outs; return P(ruin), P(50% DD), median final W."""
    idx = rng.integers(0, len(base), size=(M, N))
    R = base[idx]
    stop_mask = R <= -0.999                                       # a full-stop loss (r ~ -1)
    gap = (rng.random((M, N)) < g) & stop_mask
    # Pareto(alpha) factor >=1, capped
    u = rng.random((M, N))
    fac = np.minimum(cap, (1.0 - u) ** (-1.0 / ALPHA))
    R = np.where(gap, R * fac, R)                                 # gapped stops lose more
    step = 1.0 + f * R
    step = np.maximum(step, 1e-9)                                 # a single trade can't go below ~0
    logW = np.cumsum(np.log(step), axis=1)
    W = np.exp(logW)
    runmax = np.maximum.accumulate(W, axis=1)
    dd = 1.0 - W / runmax
    p_ruin = float(np.mean(W.min(axis=1) < RUIN))
    p_dd50 = float(np.mean(dd.max(axis=1) > 0.50))
    return p_ruin, p_dd50, float(np.median(W[:, -1]))


def main() -> int:
    rng = np.random.default_rng(0)
    base = ledger_returns(rng)
    print(f"\nNQ edge-champions (4h/2h/1h/15m) · n={len(base)} trades · win {100*(base>0).mean():.1f}% · "
          f"expectancy {base.mean()*STOP:+.1f} pts")
    print(f"gap model: alpha={ALPHA}, cap={{}}x the stop; ruin = wealth < {100*RUIN:.0f}% of start\n")

    fgrid = [0.005, 0.006, 0.010, 0.012, 0.020, 0.025, 0.030, 0.040]
    for g, cap in [(0.0, 4.0), (0.05, 4.0), (0.10, 4.0), (0.05, 6.0)]:
        label = "NO gap (backtest-ideal)" if g == 0 else f"gap g={g:.0%}, cap {cap:.0f}x"
        print("=" * 84)
        print(f"{label}")
        print("=" * 84)
        print(f"  {'f (risk/trade)':>14} {'P(ruin)':>9} {'P(50% DD)':>11} {'median final W':>16}")
        for f in fgrid:
            pr, pdd, mw = simulate(base, f, g, cap, rng)
            flag = ""
            if pr > 0.01:
                flag = "  <- ruin > 1%"
            print(f"  {100*f:>12.1f}% {100*pr:>8.2f}% {100*pdd:>10.1f}% {mw:>15.2f}x{flag}")
        print()

    print("=" * 84)
    print("READ")
    print("=" * 84)
    print("  Compare the safe f under a realistic gap overlay to Z1's full Kelly (2.5%) and quarter (0.6%).")
    print("  The gap tail is what K6 warned about: a fraction that looks safe under the bounded-loss backtest")
    print("  (g=0) can breach the ruin threshold once gaps are included. Read off the largest f holding")
    print("  P(ruin) < 1% under a plausible gap rate — that is the tail-safe cap. The honest sizing is the")
    print("  MIN of (quarter-Kelly, the CI floor, this tail-safe f), with a hard contract cap on top.")
    print("  NOTE: the gap rate g and cap are ASSUMPTIONS from D2/D3, not measured live fills — sensitivity")
    print("  shown across g. Do not adopt a fraction without real fill/slippage data.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
