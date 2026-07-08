"""H.4 — per-timeframe cooldown cap via the realized-trade-gap rule (TASK.md D1, §9-a).

Rule: cap_cooldown(TF) = floor(1 trading day ÷ median wall-clock gap between consecutive TAKEN
trades), measured on a fixed REFERENCE config — gate OFF, breaker OFF, one-position-at-a-time —
so the cap is well-defined and independent of the gate/breaker being searched. The reference SL/TP
is the winner's (30/40/60); cadence depends mildly on stop distance, and this keeps it reproducible.

Why: the breaker's `cooldown` halts the next N entries; the wall-clock that costs ≈ N × median_gap,
so capping N at floor(1day / median_gap) guarantees a cooldown never pauses trading more than ~1 day.
Sparse TFs (4h) → cap ≈ 0 ("given holds, can't cool down"); dense fine TFs → larger caps.

CLI:  python3 subprojects/wsg-strategy/optimize/cooldown.py          # all 7 TFs → cooldown_caps.json
      python3 subprojects/wsg-strategy/optimize/cooldown.py 1h 4h    # subset
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

_HERE = Path(__file__).resolve().parent
_PARENT = _HERE.parent
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

import config            # noqa: E402
from engine import SimpleStrategy, SimpleStrategyParams  # noqa: E402
from optimize import data as data_mod, timeframes as TF  # noqa: E402

# 1 trading day for the NQ futures session (≈ 23h). Tunable; the cap scales inversely with it.
TRADING_DAY_HOURS = 23.0
# Reference stop/target used only to measure realized-trade cadence (winner's distances).
REF = dict(sl_soft=30.0, sl_hard=40.0, tp=60.0)

OUT = _HERE / "cooldown_caps.json"


def reference_entry_times(tf_name: str) -> list[pd.Timestamp]:
    """Run the reference config (gate off, breaker off) on the full window; return sorted
    entry timestamps of all completed trades (the realized cadence)."""
    df_dec, df1, box, _vf, _n = data_mod.load_inputs(tf_name)
    sp = SimpleStrategyParams(sl_soft_points=REF["sl_soft"], sl_hard_points=REF["sl_hard"],
                              tp_hard_points=REF["tp"],
                              data_path_4h="", data_path_1min="", box_data_path="",
                              flip_entry_direction=False)
    trades, _ = SimpleStrategy(sp).backtest(df_dec, df1, box, entry_gate=None)
    times = sorted(pd.Timestamp(t["entry_time"]) for t in trades
                   if t.get("exit_reason") not in (None, "OPEN"))
    return times


def cap_for(tf_name: str) -> dict:
    times = reference_entry_times(tf_name)
    n = len(times)
    if n < 2:
        return dict(timeframe=tf_name, n_trades=n, median_gap_h=None, mean_gap_h=None,
                    trades_per_day=None, cooldown_cap=0)
    gaps_h = np.diff(np.array([t.value for t in times])) / 3.6e12  # ns → hours
    med = float(np.median(gaps_h))
    span_days = (times[-1] - times[0]).total_seconds() / 86400.0
    cap = int(math.floor(TRADING_DAY_HOURS / med)) if med > 0 else 0
    return dict(timeframe=tf_name, n_trades=n, median_gap_h=round(med, 3),
                mean_gap_h=round(float(gaps_h.mean()), 3),
                trades_per_day=round(n / span_days, 2) if span_days > 0 else None,
                cooldown_cap=cap)


def main(argv: list[str]) -> int:
    names = argv or list(TF.TIMEFRAMES)
    results = {}
    print(f"cooldown caps (1 day = {TRADING_DAY_HOURS}h; ref SL/TP {REF}); gate+breaker OFF\n", flush=True)
    print(f"{'TF':>4} {'#trades':>8} {'med gap(h)':>11} {'mean gap(h)':>12} {'trades/day':>11} {'cap':>5}", flush=True)
    for name in names:
        t = time.time()
        r = cap_for(name)
        results[name] = r
        print(f"{name:>4} {r['n_trades']:>8} {str(r['median_gap_h']):>11} {str(r['mean_gap_h']):>12} "
              f"{str(r['trades_per_day']):>11} {r['cooldown_cap']:>5}   ({time.time()-t:.0f}s)", flush=True)
    OUT.write_text(json.dumps(results, indent=2))
    print(f"\nwrote {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
