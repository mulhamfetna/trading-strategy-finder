"""WS-I.7 — regression lock for the VECTORIZED indicator gate (runner.veto_mask + confirm_mask
folded into the optimiser fast path). For each indicator config it builds the per-bar gate
  gate_used = vol_gate ∧ ¬veto ∧ confirm≥K
and asserts the fast engine (fast_backtest with that gate) matches the verified engine
(SimpleStrategy.backtest with the SAME entry_gate, entry_resolver=None) trade-for-trade.

Scope: the optimiser fast path treats confirm/veto as an immediate-fill GATE — it does NOT model
retrace/wait fill or the live-carry resolver (those stay in the exact dashboard engine). This test
locks exactly what the fast path does. Also checks the all-off ⇒ vol-gate parity invariant.

Run: python3 subprojects/Parametric-Indicators/optimize/test_indicator_parity.py [tf]   (default 4h)
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
from indicators import library, runner  # noqa: E402

# (name, indicator specs, k)
CASES = [
    ("rsi confirm k1",      [{"key": "rsi", "enabled": True, "mode": "confirm"}], 1),
    ("adx veto k1",         [{"key": "adx", "enabled": True, "mode": "veto", "params": {"threshold": 25}}], 1),
    ("ema+macd confirm k2", [{"key": "ema_trend", "enabled": True, "mode": "confirm"},
                             {"key": "macd", "enabled": True, "mode": "confirm"}], 2),
    ("rsi confirm + adx veto", [{"key": "rsi", "enabled": True, "mode": "confirm"},
                                {"key": "adx", "enabled": True, "mode": "veto"}], 1),
    ("bollinger veto k1",   [{"key": "bollinger", "enabled": True, "mode": "veto"}], 1),
]
SS, SH, TP, GP = 30, 40, 60, 60   # the winner box params


def _count_mismatch(E, F) -> int:
    """Trade-for-trade mismatch count between the exact engine (E) and fast engine (F)."""
    return sum(
        1 for e, f in zip(E, F)
        if pd.Timestamp(e["entry_time"]) != pd.Timestamp(f["entry_time"])
        or e["direction"] != f["direction"] or e["exit_reason"] != f["exit_reason"]
        or pd.Timestamp(e["exit_time"]) != pd.Timestamp(f["exit_time"])
        or abs(e["pnl_points"] - f["pnl_points"]) > 1e-6
    )


def main(tf: str = "4h", keys=None) -> int:
    df, df1, box, vf, n = data.load_inputs(tf)
    sig_int = signals_to_int(signals.decision_signals(df, box))
    DD, DC = df["Date"].to_numpy(), df["Close"].to_numpy(float)
    MD = df1["Date"].to_numpy(); MH = df1["High"].to_numpy(float)
    ML = df1["Low"].to_numpy(float); MC = df1["Close"].to_numpy(float); MO = df1["Open"].to_numpy(float)
    vol_gate = vf <= float(np.percentile(vf[:n], GP))

    def run_case(specs, k):
        inds = library.from_specs(specs)
        g = vol_gate & ~runner.veto_mask(df, box, inds) & runner.confirm_mask(df, box, inds, k)
        sp = SimpleStrategyParams(sl_soft_points=SS, sl_hard_points=SH,
                                  tp_hard_points=TP, data_path_4h="", data_path_1min="",
                                  box_data_path="", flip_entry_direction=False)
        E0, _ = SimpleStrategy(sp).backtest(df, df1, box, entry_gate=g)
        E = [t for t in E0 if t.get("exit_reason") not in (None, "OPEN")]
        F = fast_backtest(DD, DC, sig_int, g, MD, MH, ML, MC, SS, SH, TP, False, m_open=MO)
        return E, F, int(g.sum())

    ok_all = True
    # Legacy combo regressions run only in a full sweep (skipped when --keys narrows the run).
    if not keys:
        for name, specs, k in CASES:
            E, F, ng = run_case(specs, k)
            diffs = _count_mismatch(E, F)
            ok = len(E) == len(F) and diffs == 0
            ok_all &= ok
            print(f"{name:26} engine={len(E):4} fast={len(F):4} gate_bars={ng:5} mismatch={diffs:3}  "
                  f"{'OK' if ok else 'FAIL'}")

    # Full-registry sweep: every registered key enabled ALONE at its SCHEMA defaults (k=1).
    # New indicators auto-enter here — this is the per-batch parity gate. `--keys a,b` narrows it.
    sweep_keys = keys if keys else list(library.REGISTRY)
    for key in sweep_keys:
        if key not in library.SCHEMA:
            print(f"{key+' solo':26} UNKNOWN KEY"); ok_all = False; continue
        meta = library.SCHEMA[key]
        params = {p["name"]: p["default"] for p in meta["params"]}
        specs = [{"key": key, "enabled": True, "mode": meta["mode"], "params": params}]
        E, F, ng = run_case(specs, 1)
        diffs = _count_mismatch(E, F)
        ok = len(E) == len(F) and diffs == 0
        ok_all &= ok
        print(f"{key+' solo':26} engine={len(E):4} fast={len(F):4} gate_bars={ng:5} mismatch={diffs:3}  "
              f"{'OK' if ok else 'FAIL'}")

    # all-off ⇒ confirm/veto masks are identity ⇒ gate == vol_gate exactly
    inds_off = library.from_specs([{"key": "rsi", "enabled": False},
                                   {"key": "adx", "enabled": False}])
    g_off = vol_gate & ~runner.veto_mask(df, box, inds_off) & runner.confirm_mask(df, box, inds_off, 1)
    parity_off = bool(np.array_equal(g_off, vol_gate))
    ok_all &= parity_off
    print(f"{'all-off == vol_gate':26} {'OK' if parity_off else 'FAIL'}")

    print("INDICATOR-PARITY OK ✓" if ok_all else "INDICATOR-PARITY FAILED ✗")
    return 0 if ok_all else 1


if __name__ == "__main__":
    # usage: python optimize/test_indicator_parity.py [tf] [--keys=a,b,c]
    _argv = [a for a in sys.argv[1:]]
    _keys = None
    for _a in list(_argv):
        if _a.startswith("--keys="):
            _keys = [k for k in _a.split("=", 1)[1].split(",") if k]
            _argv.remove(_a)
    _tf = _argv[0] if _argv else "4h"
    raise SystemExit(main(_tf, keys=_keys))
