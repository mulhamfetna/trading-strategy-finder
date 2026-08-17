"""WS-DEPLOY (#127/#128/#129) — the isolation proof battery that runs WITHOUT market data.

These are the synthetic-bar unit proofs; the heavy proofs (replay parity vs the committed M3
evidence, monitor era-walk on real history) run server-side and are recorded in the issues.
Every test here maps to a pre-registered proof line in #128/#129.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.deploy.release_executor import Leg, run_bracket, LEAD_S, EXIT_S, STOP_PCT, TP_PCT
from src.deploy.regime_monitor import rolling_state, current_state, WINDOW, CPI_TITLE
from src.strategy.simple_strategy import _finalise


REL = pd.Timestamp("2026-01-14 08:30:00")
ENTRY_T = REL - pd.Timedelta(seconds=LEAD_S)


def bars(spec):
    """Synthetic contiguous 1-second bars from (t_offset_s_from_release, o, h, l, c) rows."""
    rows = [(REL + pd.Timedelta(seconds=s), o, h, l, c) for s, o, h, l, c in spec]
    d = pd.DataFrame(rows, columns=["Date", "Open", "High", "Low", "Close"])
    return (d["Date"].to_numpy(), d["Open"].to_numpy(float), d["High"].to_numpy(float),
            d["Low"].to_numpy(float), d["Close"].to_numpy(float))


def flat_prefix(price=20000.0):
    """Quiet bars from entry−5s through the release second."""
    return [(s, price, price + 1, price - 1, price) for s in range(-LEAD_S - 5, 1)]


# ---------------- D1 · the bracket's exact fill semantics (#128 V-lines) ------------------------

def test_tp_fills_at_line_when_touched():
    p = 20000.0
    tp = p * (1 + TP_PCT / 100)
    spec = flat_prefix(p) + [(1, p + 5, tp + 3, p + 4, tp + 1)]     # open below TP, high crosses
    f = run_bracket(*bars(spec), REL, Leg("long", 1), 20.0, "CPI")
    assert f.outcome == "tp" and f.exit_price == pytest.approx(tp)


def test_tp_gap_open_fills_at_the_better_open():
    p = 20000.0
    tp = p * (1 + TP_PCT / 100)
    spec = flat_prefix(p) + [(1, tp + 10, tp + 12, tp + 8, tp + 9)]  # gaps ABOVE the limit
    f = run_bracket(*bars(spec), REL, Leg("long", 1), 20.0, "CPI")
    assert f.outcome == "tp" and f.exit_price == pytest.approx(tp + 10)   # limit fills at open


def test_stop_gap_open_fills_at_the_worse_open():
    p = 20000.0
    sl = p * (1 - STOP_PCT / 100)
    spec = flat_prefix(p) + [(1, sl - 8, sl - 5, sl - 12, sl - 6)]   # gaps BELOW the stop
    f = run_bracket(*bars(spec), REL, Leg("long", 1), 20.0, "CPI")
    assert f.outcome == "stopped_post" and f.exit_price == pytest.approx(sl - 8)  # GAP-01


def test_tie_one_bar_breaching_both_counts_as_stop():
    p = 20000.0
    sl, tp = p * (1 - STOP_PCT / 100), p * (1 + TP_PCT / 100)
    spec = flat_prefix(p) + [(1, p, tp + 5, sl - 5, p)]              # one violent second hits BOTH
    f = run_bracket(*bars(spec), REL, Leg("long", 1), 20.0, "CPI")
    assert f.outcome == "stopped_post"                               # pessimistic, pre-registered


def test_pre_release_stop_is_classified_pre():
    p = 20000.0
    sl = p * (1 - STOP_PCT / 100)
    spec = flat_prefix(p)[:-40] + [(-40, p, p + 1, sl - 2, sl - 1)] + \
           [(s, sl, sl + 1, sl - 1, sl) for s in range(-39, 2)]
    f = run_bracket(*bars(spec), REL, Leg("long", 1), 20.0, "CPI")
    assert f.outcome == "stopped_pre" and f.exit_s_from_release < 0


def test_timed_exit_at_the_last_bar_close():
    p = 20000.0
    spec = flat_prefix(p) + [(s, p + 2, p + 3, p + 1, p + 2) for s in range(1, EXIT_S + 1)]
    f = run_bracket(*bars(spec), REL, Leg("long", 1), 20.0, "CPI")
    assert f.outcome == "timed" and f.exit_price == pytest.approx(p + 2)
    assert f.pnl_usd == pytest.approx(2 * 20.0)


def test_qty_is_exactly_linear_and_points_are_per_contract():
    p = 20000.0
    spec = flat_prefix(p) + [(s, p + 4, p + 5, p + 3, p + 4) for s in range(1, EXIT_S + 1)]
    f1 = run_bracket(*bars(spec), REL, Leg("long", 1), 20.0, "CPI")
    f3 = run_bracket(*bars(spec), REL, Leg("long", 3), 20.0, "CPI")
    assert f3.pnl_usd == pytest.approx(3 * f1.pnl_usd)
    assert f3.pnl_points == pytest.approx(f1.pnl_points)             # per-contract, size-invariant


def test_entry_tolerance_rejects_a_distant_entry_bar():
    p = 20000.0
    spec = [(-LEAD_S - 120, p, p + 1, p - 1, p)] + \
           [(s, p, p + 1, p - 1, p) for s in range(-30, EXIT_S + 1)]  # nothing near entry time
    assert run_bracket(*bars(spec), REL, Leg("long", 1), 20.0, "CPI") is None


# ---------------- D1 · the engine's qty hook (#128: byte-identical at qty=1) --------------------

def _trade():
    return {"entry_time": None}


def test_engine_qty1_is_numerically_identical():
    t = _trade()
    _finalise(t, pd.Timestamp("2026-01-01"), 20010.0, "TAKE_PROFIT_HARD", 20000.0, "long", 20.0)
    assert t["pnl_dollars"] == 10.0 * 20.0                           # exact, not approx
    assert t["qty"] == 1


def test_engine_qty_scales_dollars_not_points():
    t = _trade()
    _finalise(t, pd.Timestamp("2026-01-01"), 20010.0, "TAKE_PROFIT_HARD", 20000.0, "long",
              20.0, qty=3)
    assert t["pnl_dollars"] == pytest.approx(3 * 10.0 * 20.0)
    assert t["pnl_points"] == pytest.approx(10.0)


def test_engine_rejects_invalid_qty():
    with pytest.raises(ValueError):
        _finalise(_trade(), pd.Timestamp("2026-01-01"), 1.0, "OPEN", 1.0, "long", 20.0, qty=0)


# ---------------- D2 · the regime monitor (#129 V-lines) ----------------------------------------

def _cpi_events(pnls, start="2016-01-15"):
    ets = pd.date_range(start, periods=len(pnls), freq="30D")
    return pd.DataFrame({"et": ets.astype(str), "title": CPI_TITLE, "pnl_usd": pnls})


def test_monitor_v1_rolling_mean_matches_independent_derivation():
    rng = np.random.default_rng(7)
    pnls = rng.normal(50, 300, 60)
    walk = rolling_state(_cpi_events(pnls))
    for i in range(WINDOW - 1, 60):
        assert walk.roll24.iloc[i] == pytest.approx(np.mean(pnls[i - WINDOW + 1:i + 1]))


def test_monitor_stands_down_on_a_dead_regime_and_goes_on_a_live_one():
    pnls = [-40.0] * 30 + [400.0] * 30                               # dead era, then the premium era
    walk = rolling_state(_cpi_events(pnls))
    assert (walk.state.iloc[WINDOW - 1:30] == "STAND_DOWN").all()
    assert walk.state.iloc[-1] == "GO"


def test_monitor_v3_planted_degradation_trips_within_the_window(tmp_path):
    good = [400.0] * 40
    poisoned = good + [-400.0] * WINDOW                              # sign-flipped recent P&Ls
    walk = rolling_state(_cpi_events(poisoned))
    assert walk.state.iloc[-1] == "STAND_DOWN"                       # alarms — the gate CAN fail


def test_monitor_stand_down_is_sticky_until_owner_clears(tmp_path):
    sf = tmp_path / "state.json"
    bad = _cpi_events([-40.0] * 30)
    assert current_state(bad, sf)["state"] == "STAND_DOWN"
    recovered = _cpi_events([-40.0] * 30 + [400.0] * 30)             # regime recovers…
    assert current_state(recovered, sf)["state"] == "STAND_DOWN"     # …but the halt STAYS
    sf.write_text(json.dumps({"halted": False, "halted_at": None}))  # the owner's clear
    assert current_state(recovered, sf)["state"] == "GO"
