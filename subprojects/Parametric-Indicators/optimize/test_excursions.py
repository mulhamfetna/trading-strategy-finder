"""Task #2 — live unrealized-P/L tracking (excursions), in BOTH engines, with no speed regression.

WHAT THIS IS. The engine has never known how a trade was doing *while it was open* — profit was only
computed at exit. That made the "ignore the stop-loss if this is just a spike" idea (Task #3)
impossible to even express.

The two numbers that matter, and the standard names for them:

  MFE — Maximum Favourable Excursion: the BEST unrealized profit the trade ever saw before it closed.
  MAE — Maximum Adverse Excursion:    the WORST unrealized loss the trade ever saw before it closed.

A trade that exits at breakeven having been +80 points up (MFE=+80) is a completely different animal
from one that crawled sideways (MFE=+3). A trade stopped out at -40 that never went против us by more
than -41 (MAE=-41) was a clean loss; one that was +60 up first (MFE=+60, MAE=-41) was a giveback.

WHY IT MUST BE OPT-IN. Adding keys to the trade dict unconditionally would change the trade ledger the
golden gate hashes. So `track_excursions` defaults to False and the OFF path must be byte-identical.

WHY IT MUST BE CHEAP. fast_engine slices to the END of the array (m_high[e:]), so anything computed
over the full slice is O(remaining bars) per trade. Excursions are computed ONLY over [entry, exit] —
median trade life is ~84 one-minute bars — so the cost is negligible.
"""
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine import SimpleStrategy, SimpleStrategyParams          # noqa: E402
from optimize import data, signals                               # noqa: E402
from optimize.fast_engine import fast_backtest, signals_to_int   # noqa: E402

_SS, _SH, _TP, _GP = 30, 40, 60, 60
_B = {}


def _bundle(tf="4h"):
    if tf not in _B:
        _B[tf] = data.load_inputs(tf)
    return _B[tf]


def _both(track: bool, tf="4h"):
    df, df1, box, vf, n = _bundle(tf)
    sig = signals_to_int(signals.decision_signals(df, box))
    gate = vf <= float(np.percentile(vf[:n], _GP))

    sp = SimpleStrategyParams(sl_soft_points=_SS, sl_hard_points=_SH, tp_hard_points=_TP,
                              data_path_4h="", data_path_1min="", box_data_path="",
                              track_excursions=track)
    E0, _ = SimpleStrategy(sp).backtest(df, df1, box, entry_gate=gate)
    E = [t for t in E0 if t.get("exit_reason") not in (None, "OPEN")]

    F = fast_backtest(df["Date"].to_numpy(), df["Close"].to_numpy(float), sig, gate,
                      df1["Date"].to_numpy(), df1["High"].to_numpy(float),
                      df1["Low"].to_numpy(float), df1["Close"].to_numpy(float),
                      _SS, _SH, _TP, False, track_excursions=track, m_open=df1["Open"].to_numpy(float))
    return E, F


# ------------------------------------------------------------------ the identity contract

def test_off_by_default_adds_no_keys():
    """The golden gate hashes the trade ledger. OFF must not add a single field."""
    E, F = _both(track=False)
    assert "mfe_points" not in E[0], "exact engine leaked excursion keys when OFF"
    assert "mfe_points" not in F[0], "fast engine leaked excursion keys when OFF"


def test_on_adds_the_keys():
    E, F = _both(track=True)
    for k in ("mfe_points", "mae_points", "bars_1m"):
        assert k in E[0], f"exact engine missing {k}"
        assert k in F[0], f"fast engine missing {k}"


def test_turning_it_on_does_not_change_any_trade():
    """Tracking must be pure OBSERVATION — it cannot alter a single entry, exit, or P/L."""
    Eo, Fo = _both(track=False)
    En, Fn = _both(track=True)
    assert len(Eo) == len(En) and len(Fo) == len(Fn)
    for a, b in zip(Fo, Fn):
        assert a["entry_time"] == b["entry_time"]
        assert a["exit_time"] == b["exit_time"]
        assert a["exit_reason"] == b["exit_reason"]
        assert abs(a["pnl_points"] - b["pnl_points"]) < 1e-9


# ------------------------------------------------------------------ the maths must be sane

def test_mfe_is_never_negative_and_mae_is_never_positive():
    """By definition. MFE is the best it ever got (>= 0 at worst, i.e. entry). MAE the worst (<= 0)."""
    _, F = _both(track=True)
    mfe = np.array([t["mfe_points"] for t in F])
    mae = np.array([t["mae_points"] for t in F])
    assert (mfe >= -1e-9).all(), f"negative MFE found: {mfe.min()}"
    assert (mae <= 1e-9).all(), f"positive MAE found: {mae.max()}"


def test_the_trade_bracket_contains_its_own_pnl():
    """Final P/L can never be better than the best it saw, nor worse than the worst it saw."""
    _, F = _both(track=True)
    bad = [t for t in F
           if not (t["mae_points"] - 1e-6 <= t["pnl_points"] <= t["mfe_points"] + 1e-6)]
    assert not bad, f"{len(bad)} trades whose P/L escapes [MAE, MFE], first: {bad[0]}"


def test_a_hard_stop_loss_exit_has_MAE_at_about_the_stop_distance():
    """A trade killed by the 40-point hard stop must have gone at least ~40 points against us."""
    _, F = _both(track=True)
    stopped = [t for t in F if t["exit_reason"] == "STOP_LOSS_HARD"]
    assert stopped, "no hard-stop exits to check"
    for t in stopped[:50]:
        assert t["mae_points"] <= -(_SH) + 1e-6, \
            f"stopped-out trade has MAE {t['mae_points']:.2f}, expected <= -{_SH}"


# ------------------------------------------------------------------ the giveback question (Task #3)

def test_we_can_now_measure_giveback():
    """THE POINT of this task. How many losing trades were WINNING first, and by how much?

    This number was previously unmeasurable. It is the entire justification for a dynamic stop.
    """
    _, F = _both(track=True)
    losers = [t for t in F if t["pnl_points"] < 0]
    givebacks = [t for t in losers if t["mfe_points"] >= _TP * 0.5]   # was >= half a take-profit up
    assert len(losers) > 0
    frac = len(givebacks) / len(losers)
    print(f"\n  losing trades: {len(losers)}")
    print(f"  of those, were >= +{_TP*0.5:.0f} pts in profit first: {len(givebacks)} ({100*frac:.1f}%)")
    assert 0.0 <= frac <= 1.0


# ------------------------------------------------------------------ parity + speed

def test_both_engines_agree_on_the_excursions():
    E, F = _both(track=True)
    assert len(E) == len(F)
    diffs = [(e["entry_time"], e["mfe_points"], f["mfe_points"])
             for e, f in zip(E, F)
             if abs(e["mfe_points"] - f["mfe_points"]) > 1e-6
             or abs(e["mae_points"] - f["mae_points"]) > 1e-6]
    assert not diffs, f"{len(diffs)} excursion mismatches, first 3: {diffs[:3]}"


def test_no_meaningful_speed_regression():
    """The whole reason fast_engine exists is that it is ~200x faster. Do not spend that.

    MEASURE CPU TIME, NOT WALL TIME. This box runs optimizer campaigns that saturate all 32 threads
    (load average 50+), so wall-clock timing here is pure noise — an early version of this test
    reported a 74% regression that was entirely another process competing for the CPU. time.process_time()
    counts only THIS process's CPU, so it is immune to that. Interleaved A/B, median of the runs.
    """
    df, df1, box, vf, n = _bundle("4h")
    sig = signals_to_int(signals.decision_signals(df, box))
    gate = vf <= float(np.percentile(vf[:n], _GP))
    args = (df["Date"].to_numpy(), df["Close"].to_numpy(float), sig, gate,
            df1["Date"].to_numpy(), df1["High"].to_numpy(float),
            df1["Low"].to_numpy(float), df1["Close"].to_numpy(float), _SS, _SH, _TP, False)

    def bench(track, reps=10):
        fast_backtest(*args, track_excursions=track)          # warm
        ts = []
        for _ in range(reps):
            t = time.process_time()                            # CPU time — ignores other processes
            fast_backtest(*args, track_excursions=track)
            ts.append(time.process_time() - t)
        return float(np.median(ts))

    offs, ons = [], []
    for _ in range(3):                                         # interleave to cancel any drift
        offs.append(bench(False))
        ons.append(bench(True))
    off, on = float(np.median(offs)), float(np.median(ons))
    overhead = (on - off) / off
    print(f"\n  OFF: {off*1000:.1f} ms CPU | ON: {on*1000:.1f} ms CPU | overhead: {100*overhead:+.1f}%")
    assert overhead < 0.15, f"excursion tracking cost {100*overhead:.0f}% CPU — too expensive"
