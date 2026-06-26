# optimize/l2/contributors/test_contrib_state.py
import sys
from pathlib import Path

_PI = Path(__file__).resolve().parents[3]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

import numpy as np
import pandas as pd
from optimize.l2.contributors import state, loader, registry
from optimize import signals as _signals
from optimize.fast_engine import signals_to_int


def test_touch_state_collapses_to_net_long_wins_ties():
    # 3 decision bars; delivery (2_holds_dropped) carries only long/short rows, possibly multiple per bar
    df_dec = pd.DataFrame({"Date": pd.to_datetime(
        ["2025-01-01T18:00", "2025-01-01T22:00", "2025-01-02T02:00"])})
    delivery = pd.DataFrame({
        "datetime": pd.to_datetime([
            "2025-01-01T18:00", "2025-01-01T18:00",   # bar0: a short box AND a long box -> long wins ties
            "2025-01-01T22:00",                        # bar1: only short -> short
            # bar2: no delivered row -> hold
        ]),
        "signal": ["short", "long", "short"],
    })
    st = state.touch_state(df_dec, delivery)
    assert list(st) == [1, -1, 0]


def test_traversal_state_fires_long_on_below_inside_above():
    # one weekly level box (W-RL via WRLU/WRLD); close path below -> inside -> above must fire 'long'.
    box = pd.DataFrame({
        "Date": pd.to_datetime(["2025-01-02"]),
        "WRLU": [110.0], "WRLD": [100.0],
    }).set_index("Date", drop=False)
    box_csv = str(Path(_PI) / "optimize" / "l2" / "contributors" / "_tmp_box_state.csv")
    box.reset_index(drop=True).to_csv(box_csv, index=False)
    # decision bars all map to box-date 2025-01-02 (hour < 18 ⇒ same day)
    df_dec = pd.DataFrame({
        "Date": pd.to_datetime(["2025-01-02T02:00", "2025-01-02T06:00", "2025-01-02T10:00"]),
        "Close": [90.0,   # below (close < lower - tick)
                  105.0,  # inside
                  120.0], # above -> traversal fires LONG
    })
    st = state.traversal_state(df_dec, box_csv, tick_threshold=0.75)
    Path(box_csv).unlink()
    assert st[0] == 0 and st[1] == 0 and st[2] == 1     # only the through-traversal bar fires long


def test_touch_vs_traversal_diverge_on_real_es():
    es = loader.load_contributor_inputs("ES", "4h")
    box_csv = registry.get_contributor("ES").box_csv
    touch = state.touch_state(es.df_dec, es.delivery)
    trav = state.traversal_state(es.df_dec, box_csv, es.tick_threshold)
    assert len(touch) == len(trav) == len(es.df_dec)
    # touch is much denser than traversal (measured: ~807 vs ~91 directional bars) — Spec §12 divergence
    assert int((touch != 0).sum()) > int((trav != 0).sum()) * 3


def test_touch_state_equals_decision_signals_recompute_on_real_es():
    """The delivered touch signal == optimize.signals.decision_signals(es) byte-for-byte (measured
    0/2119 mismatches). This anchors source (a) 'delivered' to the L1 Stage-1 rule (Spec §4.2)."""
    es = loader.load_contributor_inputs("ES", "4h")
    touch = state.touch_state(es.df_dec, es.delivery)
    recompute = signals_to_int(_signals.decision_signals(es.df_dec, es.box))
    assert np.array_equal(touch, recompute)
