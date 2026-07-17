"""#7 · D1 — WHAT IS THE SHAPE OF OUR PER-TRADE P&L? (fit the distribution that defeated every edge)

The DIST-01 research recipe assumes fat tails from RAW RETURNS. But a strategy's PER-TRADE P&L is not raw
returns — it is shaped by a fixed stop and take-profit, which TRUNCATE it. So the first, decisive question
is empirical: is our per-trade P&L actually FAT-TAILED (losses gap/slip beyond the stop — the real tail),
or is it BOUNDED/truncated by the stop and TP (a different risk profile entirely)? The answer decides how
to size and where the real large-loss risk lives.

We characterize the NQ champion trade ledgers directly:
  * exit-reason breakdown + P&L at each (winner mode / loser mode / in-between).
  * the full per-trade P&L distribution: sd, skew, excess kurtosis, quantiles.
  * THE TAIL: are there losses WORSE than the hard stop? how far? that is the fat tail (gaps/slippage/
    sweeps) — or its absence.
  * Gaussian vs empirical large-loss probability: does a normal assumption under-state our real tail risk?

Per-trade P&L in POINTS (comparable across TFs; $ = points x pv).

  WSH_DATA_BASE=/home/dev/Mulham/wsg-h python3 -u optimize/fundamentals/study_pnl_distribution.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from optimize import data, instruments, signals                    # noqa: E402
from optimize.fast_engine import fast_backtest, signals_to_int     # noqa: E402
from perf._common import champion_preset                           # noqa: E402
from scipy import stats                                            # noqa: E402

TFS = ["4h", "2h", "1h", "15m", "5m", "2m"]


def trades_for(tf, inst="NQ"):
    df, df1, box, vf, n = data.load_inputs(tf, instrument=inst)
    p = champion_preset(tf)
    slh = float(p.get("sl_hard_points", 40)); tp = float(p.get("tp_hard_points", 60))
    sig = signals_to_int(signals.decision_signals(df, box))
    gate = vf <= float(np.percentile(vf[:n], float(p.get("gate_pct", 60))))
    F = fast_backtest(df["Date"].to_numpy(), df["Close"].to_numpy(float), sig, gate,
                      df1["Date"].to_numpy(), df1["High"].to_numpy(float), df1["Low"].to_numpy(float),
                      df1["Close"].to_numpy(float), float(p.get("sl_soft_points", 30)), slh, tp,
                      bool(p.get("flip_entry_direction", False)))
    return F, slh, tp


def main() -> int:
    inst = "NQ"; pv = instruments.point_value(inst)
    all_pnl = []
    print(f"\n{inst} champions — per-trade P&L shape (points; ${pv:,.0f}/pt)\n")
    print(f"  {'tf':>4} {'n':>5} {'mean':>7} {'sd':>7} {'skew':>6} {'exkurt':>7} "
          f"{'min':>7} {'max':>7} | {'%@TP':>6} {'%@stop':>7} {'%beyond-stop':>12}")
    perslh = {}
    for tf in TFS:
        try:
            F, slh, tp = trades_for(tf)
        except Exception as e:                                     # noqa: BLE001
            print(f"  {tf:>4} FAIL {str(e)[:40]}"); continue
        r = np.array([t["pnl_points"] for t in F], float)
        perslh[tf] = slh
        all_pnl.append(r)
        at_tp = np.mean(r >= tp - 1)
        at_stop = np.mean((r <= -(slh - 1)) & (r >= -(slh + 1)))
        beyond = np.mean(r < -(slh + 1))                          # losses WORSE than the hard stop
        print(f"  {tf:>4} {len(r):>5} {r.mean():>+7.1f} {r.std():>7.1f} {stats.skew(r):>+6.2f} "
              f"{stats.kurtosis(r):>+7.2f} {r.min():>+7.0f} {r.max():>+7.0f} | "
              f"{100*at_tp:>5.1f}% {100*at_stop:>6.1f}% {100*beyond:>11.1f}%")

    R = np.concatenate(all_pnl)
    print(f"\n  POOLED n={len(R)}  mean {R.mean():+.1f}  sd {R.std():.1f}  skew {stats.skew(R):+.2f}  "
          f"excess-kurtosis {stats.kurtosis(R):+.2f}  (Gaussian would be 0/0)")

    # ---- TRUNCATED or FAT-TAILED? ------------------------------------------------------------------
    print("\n" + "=" * 92)
    print("IS THE PER-TRADE P&L FAT-TAILED, OR TRUNCATED BY THE STOP?")
    print("=" * 92)
    # a representative hard stop (use the median across TFs) to define "beyond stop"
    med_slh = float(np.median(list(perslh.values()))) if perslh else 40.0
    beyond = R[R < -med_slh - 1]
    print(f"  representative hard stop: {med_slh:.0f} pts")
    print(f"  trades with a loss WORSE than the stop: {len(beyond)} of {len(R)} "
          f"({100*len(beyond)/len(R):.2f}%)")
    if len(beyond):
        print(f"     those losses: median {np.median(beyond):.0f}  worst {beyond.min():.0f} pts "
              f"(${beyond.min()*pv:,.0f})  — the GAP/SLIPPAGE tail beyond the stop")
    losers = R[R < 0]
    print(f"  loss distribution: n={len(losers)}  mean {losers.mean():.1f}  "
          f"1st%ile {np.percentile(R,1):.0f}  0.1%ile {np.percentile(R,0.1):.0f} pts")

    # ---- GAUSSIAN vs EMPIRICAL tail ----------------------------------------------------------------
    print("\n" + "=" * 92)
    print("DOES A GAUSSIAN UNDER-STATE OUR TAIL? (the reason not to assume normal)")
    print("=" * 92)
    mu, sd = R.mean(), R.std()
    for q in (5, 1, 0.5, 0.1):
        emp = np.percentile(R, q)
        gau = stats.norm.ppf(q / 100, mu, sd)
        print(f"  {q:>4.1f}% worst-loss quantile:  empirical {emp:>+7.0f} pts (${emp*pv:>+8,.0f})   "
              f"Gaussian {gau:>+7.0f} pts   {'GAUSSIAN TOO OPTIMISTIC' if emp < gau else 'ok'}")

    # ---- GPD on the loss tail (peaks-over-threshold) -----------------------------------------------
    print("\n" + "=" * 92)
    print("EVT — Generalized Pareto fit to the LOSS tail (peaks-over-threshold), xi as a range")
    print("=" * 92)
    L = -R[R < 0]                                                  # losses as positive magnitudes
    L = L[np.isfinite(L)]
    print(f"  {'threshold %ile':>15} {'n exceed':>9} {'xi (shape)':>11} {'beta (scale)':>13}")
    for thr_q in (80, 90, 95):
        u = np.percentile(L, thr_q)
        exc = L[L > u] - u
        if len(exc) < 20:
            print(f"  {thr_q:>13}%  too few exceedances ({len(exc)})"); continue
        try:
            xi, loc, beta = stats.genpareto.fit(exc, floc=0)
            tail = "heavy (xi>0)" if xi > 0.05 else "bounded (xi<0)" if xi < -0.05 else "~exponential"
            print(f"  {thr_q:>13}%  {len(exc):>9} {xi:>+11.3f} {beta:>13.1f}   {tail}")
        except Exception as e:                                    # noqa: BLE001
            print(f"  {thr_q:>13}%  fit failed: {e}")
    print("  (xi < 0 => the loss tail is BOUNDED — the stop truncates it; xi > 0 => genuinely heavy)")

    print("\n" + "=" * 92)
    print("READ")
    print("=" * 92)
    print("  This tells us whether our risk is a TRUNCATED distribution (stop caps the loss; the '±$1,600")
    print("  swing' is really the winner/loser SPREAD, not a fat tail) or a genuine FAT TAIL (gaps/slippage")
    print("  push losses past the stop). Next (D2/D3): tail index of RAW 1-min NQ per session (the McNeil-")
    print("  Frey GARCH->GPD machinery), and condition on the event-volatility state from A2.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
