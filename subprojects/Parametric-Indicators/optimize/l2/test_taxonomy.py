"""Candle taxonomy boxes — counts + dollars derived strictly from the causal log."""
import sys
from pathlib import Path

_PI = Path(__file__).resolve().parents[2]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

import json
from optimize.l2 import logbook, payload, taxonomy

_TF = "4h"


def _l1_res():
    return logbook.run_causal(payload.l1_default_params(_TF), dict(payload.PERMISSIVE), _TF)


def test_l1_partition_covers_every_classified_bar():
    res = _l1_res()
    t = taxonomy.taxonomy_l1(res)
    leaves = ["no_box_signal", "gate_rejected", "indicator_veto",
              "indicator_no_confirm", "passed_all_gates"]
    total = sum(t[k]["count"] for k in leaves)
    assert total == res.n - 1                 # bar 0 has cause None
    assert t["n_classified"] == res.n - 1


def test_l1_passed_branch_splits_and_reconciles():
    res = _l1_res()
    t = taxonomy.taxonomy_l1(res)
    # entered anchors to the known parity numbers
    assert t["entered"]["count"] == 255
    assert round(t["entered"]["pnl"]) == 149989
    # the three sub-buckets exactly partition passed_all_gates
    assert (t["entered"]["count"] + t["passed_skipped"]["count"]
            + t["passed_in_position"]["count"]) == t["passed_all_gates"]["count"]
    # passed_skipped carries counterfactual would-be $ (key present)
    assert "pnl" in t["passed_skipped"]
    assert "pnl" not in t["passed_in_position"]   # count-only


def test_l1_exit_leaves_partition_entries_and_timecap_winloss():
    res = _l1_res()
    t = taxonomy.taxonomy_l1(res)
    exits = ["tp_exit", "sl_soft_exit", "sl_hard_exit", "time_cap_exit"]
    assert sum(t[k]["count"] for k in exits) == t["entered"]["count"]
    assert round(sum(t[k]["pnl"] for k in exits), 2) == t["entered"]["pnl"]
    # TIME_CAP win/loss partition the TIME_CAP bucket
    assert t["time_cap_win"]["count"] + t["time_cap_loss"]["count"] == t["time_cap_exit"]["count"]
    assert round(t["time_cap_win"]["pnl"] + t["time_cap_loss"]["pnl"], 2) == t["time_cap_exit"]["pnl"]
    assert all(r >= 0 for r in [t["time_cap_win"]["pnl"]] if t["time_cap_win"]["count"])


def _l2_res():
    champ = json.load(open(str(_PI / "optimize/results/l2v2_4h_champion.json")))["params"]
    return logbook.run_causal(payload.l1_default_params(_TF), champ, _TF)


def test_l2_tree_partitions_and_reconciles_to_l1_drops():
    res = _l2_res()
    t = taxonomy.taxonomy_l2(res)
    # L2 entered anchors to the l2v2 parity number
    assert t["entered"]["count"] == 34
    # L2 decision partition sums to evaluated
    parts = ["gate_rejected", "indicator_veto", "indicator_no_confirm", "passed_no_open", "entered"]
    assert sum(t[k]["count"] for k in parts) == t["l2_evaluated"]["count"]
    # exits partition entered (L2 has the extra L1-entry force-close leaf)
    exits = ["tp_exit", "sl_soft_exit", "sl_hard_exit", "time_cap_exit", "l1_entry_exit"]
    assert sum(t[k]["count"] for k in exits) == t["entered"]["count"]
    # universe reconciles to L1's forwarded vetoed+vol_gated drops
    l1_drops = sum(1 for r in res.log if r.box_cause in ("vetoed", "vol_gated"))
    assert t["l2_evaluated"]["count"] + t["forwarded_but_l1_in_position"]["count"] == l1_drops
