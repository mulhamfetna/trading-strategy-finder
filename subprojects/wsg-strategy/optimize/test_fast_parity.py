"""Regression lock for the vectorized engine (fast_engine.fast_backtest) — it MUST match the
verified engine.SimpleStrategy trade-for-trade, across normal/flip/gate-on/gate-off/wide/tight.

This is the contract that lets the optimiser use the 200×-faster path safely. Run:
  python3 subprojects/wsg-strategy/optimize/test_fast_parity.py   [tf]   (default 4h)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_PARENT = Path(__file__).resolve().parents[1]
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

from optimize import data, signals  # noqa: E402
from optimize.fast_engine import fast_backtest, signals_to_int  # noqa: E402
from engine import SimpleStrategy, SimpleStrategyParams  # noqa: E402

CASES = [  # (name, sl_soft, sl_hard, tp, gate_pct, flip)
    ("winner 30/40/60 g60", 30, 40, 60, 60, False),
    ("no-gate 30/40/60",    30, 40, 60,  0, False),
    ("flip 30/40/60 g60",   30, 40, 60, 60, True),
    ("wide 100/160/200 g50", 100, 160, 200, 50, False),
    ("tight 10/14/18 g0",   10, 14, 18,  0, False),
    ("flip wide g70",       60, 120, 150, 70, True),
]


def main(tf: str = "4h") -> int:
    df, df1, box, vf, n = data.load_inputs(tf)
    sig_int = signals_to_int(signals.decision_signals(df, box))
    DD, DC = df["Date"].to_numpy(), df["Close"].to_numpy(float)
    MD = df1["Date"].to_numpy(); MH = df1["High"].to_numpy(float)
    ML = df1["Low"].to_numpy(float); MC = df1["Close"].to_numpy(float)

    def gate(gp):
        return None if gp <= 0 else (vf <= float(np.percentile(vf[:n], gp)))

    ok_all = True
    for name, ss, sh, tp, gp, flip in CASES:
        sp = SimpleStrategyParams(sl_soft_points=ss, sl_hard_points=sh, tp_soft_points=tp,
                                  tp_hard_points=tp, data_path_4h="", data_path_1min="",
                                  box_data_path="", flip_entry_direction=flip)
        E0, _ = SimpleStrategy(sp).backtest(df, df1, box, entry_gate=gate(gp))
        E = [t for t in E0 if t.get("exit_reason") not in (None, "OPEN")]
        F = fast_backtest(DD, DC, sig_int, gate(gp), MD, MH, ML, MC, ss, sh, tp, flip)
        diffs = sum(
            1 for e, f in zip(E, F)
            if pd.Timestamp(e["entry_time"]) != pd.Timestamp(f["entry_time"])
            or e["direction"] != f["direction"] or e["exit_reason"] != f["exit_reason"]
            or pd.Timestamp(e["exit_time"]) != pd.Timestamp(f["exit_time"])
            or abs(e["pnl_points"] - f["pnl_points"]) > 1e-6
        )
        ok = len(E) == len(F) and diffs == 0
        ok_all &= ok
        print(f"{name:24} engine={len(E):4} fast={len(F):4} mismatch={diffs:3}  {'OK' if ok else 'FAIL'}")

    print("FAST-PARITY OK ✓" if ok_all else "FAST-PARITY FAILED ✗")
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "4h"))
