import sys
from pathlib import Path

_PI = Path(__file__).resolve().parents[2]   # subproject root
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

import numpy as np
import config
from optimize.core import backtest_metrics
from optimize.l2 import l1_runner


def test_run_l1_ledger_matches_frozen_engine():
    """Pass-1 ledger total P/L is byte-identical to core.backtest_metrics on the same lean params,
    and reproduces the lean champion's reported full-period P/L (~$149,989)."""
    r = l1_runner.run_l1("4h")
    l1_total = sum(t["pnl"] for t in r.ledger)

    ref = backtest_metrics(r.df_dec, r.df1, r.box, r.vf, r.n_split,
                           dict(r.params, window="full"), r.bar_td, sig_int=r.sig_int)
    assert abs(l1_total - ref["pnl"]) < 1e-6
    assert len(r.ledger) == ref["n_taken"]
    assert abs(l1_total - 149989.0) < 50.0          # loose sanity vs the rounded champion figure


def test_state_timeline_marks_each_trade_bar():
    r = l1_runner.run_l1("4h")
    assert r.state_timeline.dtype == bool
    assert len(r.state_timeline) == len(r.df_dec)
    # every ledger trade's entry bar is flagged in-position
    for t in r.ledger:
        assert r.state_timeline[int(t["entry_idx"])]


def test_cause_only_buckets_veto_and_vol_gate_into_dropped():
    r = l1_runner.run_l1("4h")
    reasons = {d["reason"] for d in r.dropped_signals}
    assert reasons <= {"veto", "vol_gate"}
    n_veto = int((r.cause == "vetoed").sum())
    n_gate = int((r.cause == "vol_gated").sum())
    assert len(r.dropped_signals) == n_veto + n_gate
    print(f"[lean-4h dropped] veto={n_veto} vol_gate={n_gate} total={len(r.dropped_signals)}")
