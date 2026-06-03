"""H.1 parity lock — the timeframe-parametric core (bar_duration=4h) must reproduce the
verified winner exactly, AND agree with the dashboard's strategy.build_payload, before any
multi-timeframe search is trusted.

Run:  python3 subprojects/wsg-strategy/optimize/test_parity.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

_PARENT = Path(__file__).resolve().parents[1]
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

import config            # noqa: E402
import strategy          # noqa: E402
from optimize.core import backtest_metrics  # noqa: E402

# The locked winner result (full window) — notes/47, corrected global-HWM breaker.
EXPECT = {"pnl": 7735.0, "max_dd": 3670.0, "n_taken": 66}


def main() -> int:
    print("loading inputs (4h / 1m / box) + HAR-RV ...", flush=True)
    df4, df1, box, vf, n2025 = strategy.load_inputs()
    params = dict(config.WINNER)  # sl_soft30/sl_hard40/tp60/gate60/dd2000/cool20/flip F/full

    # (a) core metrics with bar_duration = 4h
    m = backtest_metrics(df4, df1, box, vf, n2025, params, bar_duration=pd.Timedelta(hours=4))
    print(f"core   : P/L ${m['pnl']:,.0f}  maxDD ${m['max_dd']:,.0f}  n={m['n_taken']}  "
          f"2025 ${m['pnl_2025']:,.0f}  2026 ${m['pnl_2026']:,.0f}  locks={m['n_locks']}")

    # (b) the dashboard payload builder (source of truth)
    p = strategy.build_payload(df4, df1, box, vf, n2025, params)["meta"]["summary"]
    print(f"payload: P/L ${p['pnl']:,.0f}  maxDD ${p['max_dd']:,.0f}  n={p['n_taken']}")

    ok = True
    for k, want in EXPECT.items():
        got = m[k]
        if abs(got - want) > 1e-6:
            print(f"  MISMATCH vs winner: {k} got {got} want {want}"); ok = False
    for k in ("pnl", "max_dd", "n_taken"):
        if abs(m[k] - p[k]) > 1e-6:
            print(f"  MISMATCH vs payload: {k} core {m[k]} payload {p[k]}"); ok = False

    print("PARITY OK ✓" if ok else "PARITY FAILED ✗")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
