"""STEP 5 — split long/short SL/TP threaded through the causal layer (run_l1 + run_l2 -> fast_backtest).
Proves: (a) split fields default to None and fall back to the shared SL/TP byte-identically (so the
$149,989/255 and $78,391/80 anchors are untouched); (b) setting per-side overrides actually changes the
book (the wiring is live); (c) an L2 split run still completes through the force-close path."""
import json
import sys
from pathlib import Path

_PI = Path(__file__).resolve().parents[2]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

from optimize.l2 import l1_runner, engine, payload

_BASE = dict(sl_soft=30, sl_hard=40, tp=60, gate_pct=0, dd_limit=0, cooldown=0, flip=False,
             k=1, ind_1min=False, indicators=[])


def _ledger_key(taken):
    return [(round(t["pnl"], 4), int(t["entry_idx"])) for t in taken]


def test_split_equal_to_shared_is_byte_identical():
    """Setting every long_*/short_* override equal to the shared value must reproduce the no-split run."""
    shared = l1_runner.run_l1("4h", params={**_BASE})
    split = l1_runner.run_l1("4h", params={**_BASE,
        "long_sl_soft": 30, "long_sl_hard": 40, "long_tp": 60,
        "short_sl_soft": 30, "short_sl_hard": 40, "short_tp": 60})
    assert _ledger_key(shared.ledger) == _ledger_key(split.ledger)


def test_split_changes_the_book():
    """Asymmetric per-side TP must change the trade book (proves the args reach fast_backtest)."""
    shared = l1_runner.run_l1("4h", params={**_BASE})
    split = l1_runner.run_l1("4h", params={**_BASE, "long_tp": 30, "short_tp": 120})
    assert _ledger_key(shared.ledger) != _ledger_key(split.ledger), "split SL/TP had no effect"


def test_validate_layer_params_carries_split_and_defaults_none():
    p = payload.validate_layer_params({**_BASE})
    assert p["long_sl_soft"] is None and p["short_tp"] is None      # default: all None (=> shared)
    p2 = payload.validate_layer_params({**_BASE, "long_tp": 99})
    assert p2["long_tp"] == 99.0
    # the frozen-default round-trip still holds with the new keys present-but-None
    d = payload.l1_default_params("4h")
    assert payload.validate_layer_params(d) == d


def test_l2_split_runs_through_force_close():
    """L2 with split overrides still completes (force_close_on_l1_entry path) — the L2-split gate the
    council asked for. We don't assert a value (L2 split semantics are runtime-opt-in), only that the
    plumbing is safe and a force-closed L2 trade is exercised."""
    l1 = payload.run_l1_cached("4h")
    l2p = json.loads((_PI / "optimize" / "results" / "l2v1_4h_champion.json").read_text())["params"]
    res = engine.run_l2(l1, {**l2p, "long_tp": 80, "short_tp": 140})
    assert res.ledger is not None
    assert any(t.get("exit_reason") == "L1-entry" for t in res.ledger), "expected a force-closed L2 trade"
