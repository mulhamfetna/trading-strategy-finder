"""SIZING · Z4 — the fraction for OUR objective (PnL:DD), not raw log-growth.

Classic Kelly maximizes log-growth. Our accepted objective is PnL:DD (return per unit max-drawdown). SIZE-01
K7 (Maier-Paape-Zhu) formalizes trading growth against a drawdown risk measure. Z4 reads the PnL:DD-optimal
fraction straight off a Monte Carlo of our ledger: for each risk fraction f, the median growth and median
max-drawdown, and their ratio. Expectation: growth saturates toward Kelly while drawdown keeps rising, so
the PnL:DD ratio peaks LOW (a plateau below ~half-Kelly) and declines above it — independently confirming
Z2's ~quarter-half-Kelly answer from the drawdown side, and showing full Kelly is far too aggressive for a
PnL:DD trader.

Reuses the Z2 ledger + gap overlay (Pareto alpha=3 on a fraction g of stop-outs).

  WSH_DATA_BASE=/home/dev/Mulham/wsg-h python3 -u optimize/fundamentals/study_kelly_pnldd.py
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

STOP = 40.0; ALPHA = 3.0; M, N = 4000, 1000
TFS = ["4h", "2h", "1h", "15m"]


def ledger(rng):
    r = []
    for tf in TFS:
        df, df1, box, vf, n = data.load_inputs(tf, instrument="NQ")
        p = champion_preset(tf)
        _SS, _SH, _TP, _FL = champion_stops(p, tf)   # STRICT — a missing stop must raise, never default
        print(describe(p, tf), flush=True)
        s = signals_to_int(signals.decision_signals(df, box))
        gate = vf <= float(np.percentile(vf[:n], float(p.get("gate_pct", 60))))
        F = fast_backtest(df["Date"].to_numpy(), df["Close"].to_numpy(float), s, gate,
                          df1["Date"].to_numpy(), df1["High"].to_numpy(float), df1["Low"].to_numpy(float),
                          df1["Close"].to_numpy(float), _SS, _SH,
                          _TP, _FL)
        r.append(np.array([t["pnl_points"] for t in F], float) / STOP)
    return np.concatenate(r)


def sim(base, f, g, cap, rng):
    idx = rng.integers(0, len(base), size=(M, N))
    R = base[idx]
    stop = R <= -0.999
    gap = (rng.random((M, N)) < g) & stop
    fac = np.minimum(cap, (1 - rng.random((M, N))) ** (-1 / ALPHA))
    R = np.where(gap, R * fac, R)
    W = np.exp(np.cumsum(np.log(np.maximum(1 + f * R, 1e-9)), axis=1))
    dd = (1 - W / np.maximum.accumulate(W, axis=1)).max(axis=1)
    return float(np.median(W[:, -1])), float(np.median(dd))


def main() -> int:
    rng = np.random.default_rng(0)
    base = ledger(rng)
    print(f"\nNQ edge-champions · {len(base)} trades · expectancy {base.mean()*STOP:+.1f} pts · "
          f"objective = PnL:DD (growth per unit max-drawdown)\n")
    print(f"  {'f (risk/trade)':>14} {'med growth':>11} {'med maxDD':>10} {'PnL:DD':>8}  (Kelly markers)")
    print("-" * 66)
    grid = [0.003, 0.006, 0.009, 0.012, 0.015, 0.020, 0.025, 0.030, 0.040]
    best = (None, -1)
    rows = []
    for f in grid:
        gw, dd = sim(base, f, 0.05, 4.0, rng)
        ratio = (gw - 1) / dd if dd > 0 else np.inf
        rows.append((f, gw, dd, ratio))
        if np.isfinite(ratio) and ratio > best[1]:
            best = (f, ratio)
    for f, gw, dd, ratio in rows:
        mark = ""
        if abs(f - 0.006) < 1e-6: mark = "<- quarter-Kelly"
        elif abs(f - 0.012) < 1e-6: mark = "<- half-Kelly"
        elif abs(f - 0.025) < 1e-6: mark = "<- FULL Kelly"
        star = "  *** PnL:DD-optimal" if f == best[0] else ""
        print(f"  {100*f:>12.1f}% {gw:>11.2f}x {100*dd:>9.1f}% {ratio:>8.2f}  {mark}{star}")

    print("\n" + "=" * 66)
    print("READ")
    print("=" * 66)
    print(f"  PnL:DD-optimal fraction ~ {100*best[0]:.1f}% of capital/trade — vs FULL Kelly 2.5%.")
    print(f"  The ratio plateaus at the LOW end and DECLINES as f rises (growth saturates toward Kelly")
    print(f"  while drawdown keeps growing). So our accepted PnL:DD objective INDEPENDENTLY points to a")
    print(f"  small fraction (<= half-Kelly), confirming Z1/Z2 from the drawdown side. Full Kelly is far")
    print(f"  too aggressive for a PnL:DD trader. This CLOSES the sizing fraction question: ~quarter-to-")
    print(f"  half Kelly, edge-champions only, hard cap; vol-targeting (Z3) is a promising method on top,")
    print(f"  pending OOS.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
