"""Parity gate for the intra-candle feature in the FAST engine: fast_backtest with the feature ON must match
the canonical exact-engine champion (strategy.build_payload, which uses the confirm resolver) trade-for-trade —
the contract that lets the optimizer use the fast path. Compared with the feature OFF (214) and ON (rescued).

Trade keys differ by format (fast: datetime64 + pnl_points; payload: epoch seconds + dollar pnl), so we compare
on (entry epoch, direction, exit_reason, dollar P/L)."""
import sys
from pathlib import Path

_PARENT = Path(__file__).resolve().parents[1]
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from optimize.fast_engine import fast_backtest  # noqa: E402
from optimize import counterfactual_pause as cp  # noqa: E402
from indicators import runner  # noqa: E402
from research.intracandle.champion_run import run_champion_exact  # noqa: E402

_PV = 20.0


def _fast_champion(ic_on, N=240):
    C = cp.load_champion("4h"); p = C["params"]
    gate = np.asarray(cp._engine_gate(C))                 # vol ∧ ¬veto ∧ confirm (fast bakes confirm in)
    veto = np.asarray(C["veto"]); volg = np.asarray(C["vol_gate"])
    ic = runner.intracandle_gate_arrays(C["d1"], C["indicators"], C["K"]) if ic_on else None
    DD = C["d"]["Date"].to_numpy(); DC = C["d"]["Close"].to_numpy(float)
    MD = C["d1"]["Date"].to_numpy(); MH = C["d1"]["High"].to_numpy(float)
    ML = C["d1"]["Low"].to_numpy(float); MC = C["d1"]["Close"].to_numpy(float)
    return fast_backtest(DD, DC, np.asarray(C["sig"]), gate, MD, MH, ML, MC,
                         float(p["sl_soft"]), float(p["sl_hard"]), float(p["tp"]), bool(p["flip"]),
                         intracandle_gate_by_dir=ic, intracandle_vol_gate=volg, intracandle_veto_mask=veto,
                         intracandle_max_wait=N)


def _fast_keys(F):
    return sorted((int(pd.Timestamp(f["entry_time"]).value // 10**9), f["direction"],
                   f["exit_reason"], round(f["pnl_points"] * _PV, 2)) for f in F)


def _exact_keys(E):
    return sorted((int(t["entry_time"]), t["direction"], t["exit_reason"], round(t["pnl"], 2)) for t in E)


def test_fast_matches_exact_feature_off():
    F = _fast_champion(ic_on=False)
    E, _ = run_champion_exact("4h", intracandle_veto_entry=False)
    assert len(F) == 214
    assert _fast_keys(F) == _exact_keys(E)         # trade-for-trade == canonical champion


def test_fast_matches_exact_feature_on():
    F = _fast_champion(ic_on=True, N=240)
    E, _ = run_champion_exact("4h", intracandle_veto_entry=True, intracandle_max_wait=240)
    assert len(F) > 214                            # the feature actually rescued entries
    assert _fast_keys(F) == _exact_keys(E)         # fast port matches the exact engine trade-for-trade
