import sys
from pathlib import Path

_PI = Path(__file__).resolve().parents[2]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

import numpy as np
from optimize.l2 import l1_runner, engine


def test_force_close_truncates_at_earliest_l1_entry():
    """A candidate spanning a later L1 entry is cut at that bar's close with reason 'L1-entry'; a
    candidate with no overlapping L1 entry is left untouched."""
    dec_dates = np.array(["2025-01-01T00:00", "2025-01-01T04:00", "2025-01-01T08:00",
                          "2025-01-01T12:00", "2025-01-01T16:00"], dtype="datetime64[ns]")
    dec_close = np.array([100.0, 110.0, 120.0, 130.0, 140.0])
    pv = 20.0
    # long entry at idx 0, natural exit at idx 4 (16:00); an L1 entry exists at idx 2.
    cand = [{"entry_idx": 0, "entry_time": dec_dates[0], "entry_price": 100.0, "direction": "long",
             "exit_time": dec_dates[4], "exit_price": 140.0, "exit_reason": "TAKE_PROFIT_HARD",
             "pnl_points": 40.0},
            # a second trade entirely after any L1 entry — untouched
            {"entry_idx": 3, "entry_time": dec_dates[3], "entry_price": 130.0, "direction": "short",
             "exit_time": dec_dates[4], "exit_price": 140.0, "exit_reason": "STOP_LOSS_HARD",
             "pnl_points": -10.0}]
    out = engine.force_close_on_l1_entry(cand, [2], dec_dates, dec_close, pv)
    assert out[0]["exit_reason"] == "L1-entry"
    assert out[0]["exit_price"] == 120.0                  # dec_close[2]
    assert out[0]["pnl_points"] == 20.0                   # 120 - 100 (long)
    assert out[1]["exit_reason"] == "STOP_LOSS_HARD"      # untouched (no L1 entry inside its span)


def test_l2_never_opens_while_l1_in_position():
    r = l1_runner.run_l1("4h")
    l2_params = dict(r.params)                            # reuse lean params as a stand-in L2 profile
    res = engine.run_l2(r, l2_params)
    for t in res.ledger:
        assert not bool(r.state_timeline[int(t["entry_idx"])]), "L2 opened while L1 in-position"


def test_l1_entry_exits_correspond_to_real_l1_entries():
    r = l1_runner.run_l1("4h")
    res = engine.run_l2(r, dict(r.params, flip=True))     # flip => 'oppose' labelling exercised
    l1_entry_bars = {int(t["entry_idx"]) for t in r.ledger}
    dec_dates = r.df_dec["Date"].to_numpy()
    for t in res.ledger:
        assert t["l2_dir_vs_box"] in ("agree", "oppose")
        if t["exit_reason"] == "L1-entry":
            xb = int(np.searchsorted(dec_dates, np.datetime64(t["exit_time"]), side="left"))
            assert xb in l1_entry_bars
    print(f"[lean-as-L2 run] n_trades={len(res.ledger)} l1_entry_exits={res.n_l1_entry_exits}")
