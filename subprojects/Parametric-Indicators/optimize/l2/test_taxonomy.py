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
