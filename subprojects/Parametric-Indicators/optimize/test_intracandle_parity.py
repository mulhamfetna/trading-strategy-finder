"""Parity gate for the intra-candle feature in the FAST engine: fast_backtest with the feature ON must match
the canonical exact-engine champion (strategy.build_payload, which uses the confirm resolver) trade-for-trade —
the contract that lets the optimizer use the fast path. Compared with the feature OFF (the champion
anchor, see _CHAMPION_N_OFF) and ON (rescued entries).

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
from optimize.optimizer import derive_cap_mode  # noqa: E402
from optimize import counterfactual_pause as cp  # noqa: E402
from indicators import runner  # noqa: E402
from research.intracandle.champion_run import run_champion_exact  # noqa: E402

_PV = 20.0

# The 4h champion's trade count with the intra-candle feature OFF. This is an ANCHOR: it must equal the
# frozen golden baseline for 4h (`perf/golden/4h.json`), which `perf/check_golden.py` verifies as
# n=277 / P/L $151,655. It was 214 before the gap-aware-fill champion adoption (2026-07-22) and was left
# stale, which is why this test failed. If a future champion adoption moves it, re-capture the golden
# baseline FIRST and update this constant to match — never the other way round.
_CHAMPION_N_OFF = 277


def _champion_cap(C):
    """The champion's time-cap, read STRICTLY from its warm-start seed (never defaulted).

    `build_params()` does not carry the caps, but the exact engine (run_champion_exact → the champion
    preset) DOES apply them — so the fast side must read them from the seed or the two engines are
    comparing different strategies. A silent `params.get("cap_1min", 0)` yields cap-OFF and makes the
    exact side's TIME_CAP exits look like a parity failure (project rule: no silent defaults for a
    strategy parameter). `_native_seed` guarantees these three keys, so a strict lookup is safe and a
    KeyError here is the correct, loud failure.
    """
    ch = C["ctx"].champ
    cap_1min = int(ch["cap_1min"])
    cap_mode = derive_cap_mode(bool(ch["en_cap_bars"]), bool(ch["en_cap_eod"]))
    if cap_mode in ("eod", "both"):                       # would additionally need eod_target/session_last
        raise NotImplementedError(
            f"champion cap_mode={cap_mode!r} needs eod targets; this parity helper only wires the bars cap")
    return cap_1min, cap_mode


def _fast_champion(ic_on, N=240, force_close=False):
    C = cp.load_champion("4h"); p = C["params"]
    gate = np.asarray(cp._engine_gate(C))                 # vol ∧ ¬veto ∧ confirm (fast bakes confirm in)
    veto = np.asarray(C["veto"]); volg = np.asarray(C["vol_gate"])
    ic = runner.intracandle_gate_arrays(C["d1"], C["indicators"], C["K"]) if ic_on else None
    DD = C["d"]["Date"].to_numpy(); DC = C["d"]["Close"].to_numpy(float)
    MD = C["d1"]["Date"].to_numpy(); MH = C["d1"]["High"].to_numpy(float)
    ML = C["d1"]["Low"].to_numpy(float); MC = C["d1"]["Close"].to_numpy(float)
    MO = C["d1"]["Open"].to_numpy(float)                  # 1-min opens — required by gap-aware fills (m_open)
    cap_1min, cap_mode = _champion_cap(C)
    return fast_backtest(DD, DC, np.asarray(C["sig"]), gate, MD, MH, ML, MC,
                         float(p["sl_soft"]), float(p["sl_hard"]), float(p["tp"]), bool(p["flip"]),
                         cap_1min=cap_1min, cap_mode=cap_mode,
                         intracandle_gate_by_dir=ic, intracandle_vol_gate=volg, intracandle_veto_mask=veto,
                         intracandle_max_wait=N, intracandle_force_close=force_close, m_open=MO)


def _fast_keys(F):
    return sorted((int(pd.Timestamp(f["entry_time"]).value // 10**9), f["direction"],
                   f["exit_reason"], round(f["pnl_points"] * _PV, 2)) for f in F)


def _exact_keys(E):
    return sorted((int(t["entry_time"]), t["direction"], t["exit_reason"], round(t["pnl"], 2)) for t in E)


def test_fast_matches_exact_feature_off():
    F = _fast_champion(ic_on=False)
    E, _ = run_champion_exact("4h", intracandle_veto_entry=False)
    assert len(F) == _CHAMPION_N_OFF
    assert _fast_keys(F) == _exact_keys(E)         # trade-for-trade == canonical champion


def test_fast_matches_exact_feature_on():
    F = _fast_champion(ic_on=True, N=240)
    E, _ = run_champion_exact("4h", intracandle_veto_entry=True, intracandle_max_wait=240)
    assert len(F) > _CHAMPION_N_OFF                 # the feature actually rescued entries
    assert _fast_keys(F) == _exact_keys(E)         # fast port matches the exact engine trade-for-trade


def test_cached_ic_gate_matches_runner_and_memoises():
    # core's memoised gate must equal the parity-locked runner gate (so the optimizer passes correct inputs),
    # and the per-indicator direction memo must populate (the perf win).
    from optimize import core
    C = cp.load_champion("4h")
    core._IC_DIR_MEMO.clear()
    g1 = core._cached_ic_gate(C["d1"], C["indicators"], C["K"])
    g2 = runner.intracandle_gate_arrays(C["d1"], C["indicators"], C["K"])
    assert np.array_equal(g1[+1], g2[+1]) and np.array_equal(g1[-1], g2[-1])
    assert len(core._IC_DIR_MEMO) > 0                      # directions cached
    g3 = core._cached_ic_gate(C["d1"], C["indicators"], C["K"])   # 2nd call reuses the memo
    assert np.array_equal(g1[+1], g3[+1]) and np.array_equal(g1[-1], g3[-1])


def test_fast_matches_exact_force_close():
    F = _fast_champion(ic_on=True, N=240, force_close=True)
    E, _ = run_champion_exact("4h", intracandle_veto_entry=True, intracandle_max_wait=240,
                              intracandle_force_close=True)
    assert any(f["exit_reason"] == "FORCE_CLOSE" for f in F)   # force-close actually fires
    assert _fast_keys(F) == _exact_keys(E)         # force-close variant matches the exact engine
