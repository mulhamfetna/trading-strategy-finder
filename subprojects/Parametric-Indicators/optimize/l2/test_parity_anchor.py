"""STEP 0 parity anchor — the single test that pins the three headline numbers of the two-layer
system to the CAUSAL source of truth (run_causal -> aggregate), plus the load-bearing frozen-default
guard. Every step of the unified-dashboard rebuild must keep this green.

Anchors (NQ, $20/pt, 1 contract, full research window) — RE-BASELINED 2026-07-27, see note below:
  L1 (4h default = the CHAMPION)  $151,655 / 277 trades / $15,560 max DD
  L2 (l2v2, reverse-entry)         $24,498 /  48 trades /  $7,015 max DD
  Combined                        $176,154 / 325 trades / $18,145 max DD  (recomputed merged book)

RE-BASELINE NOTE (2026-07-27, issue #66). These previously pinned the FROZEN LEAN anchor
($149,989 / 255). The 4h L1 default was deliberately moved to the champion (see
test_tf_defaults.test_4h_default_is_now_the_champion_not_the_anchor) and the gap-aware-fill champion
adoption (2026-07-22) then changed its numbers — so the old values had been stale ever since and these
three tests were failing. The new L1 figures are NOT re-baselined to "whatever the code now prints":
$151,655 / 277 is exactly the frozen GOLDEN baseline for 4h (`perf/golden/4h.json`), independently
verified by `perf/check_golden.py`. The L2/Combined figures were re-measured against it and reconcile
(325 = 277 + 48; $176,154 = $151,655 + $24,498). If a future champion adoption moves these, re-capture
the golden baseline FIRST, then update here to match — never the other way round.

The frozen-default guard protects the disk-cached oracle: run_causal selects it via the EXACT dict
equality use_frozen = (validate_layer_params(l1_default_params(tf)) == l1_default_params(tf))
(logbook.py:126). build_view_payload repeats the same check (payload.py:391). If a future schema change
adds a key to validate_layer_params without echoing it in l1_default_params/_lean_params, this equality
silently fails, the default routes OFF the cached oracle, and the $151,655/277 anchor can drift. This
test fails LOUDLY if that ever happens.
"""
import json
import sys
from pathlib import Path

_PI = Path(__file__).resolve().parents[2]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

import pytest

from optimize.l2 import logbook, aggregate, payload
from optimize import timeframes as TF

_TF = "4h"
_L2_CHAMP = _PI / "optimize" / "results" / "l2v2_4h_champion.json"   # re-locked 2026-06-22 (reverse-entry-only)


@pytest.fixture(scope="module")
def causal():
    l1p = payload.l1_default_params(_TF)
    l2p = json.loads(_L2_CHAMP.read_text())["params"]
    res = logbook.run_causal(l1p, l2p, _TF)
    bar_secs = int(TF.get(_TF).bar_td.total_seconds())
    return res, bar_secs


def test_l1_anchor(causal):
    res, bs = causal
    b = aggregate.boxes_for_layer(res, "L1", bs)
    assert b["n_taken"] == 277
    assert round(b["pnl"]) == 151655          # == perf/golden/4h.json
    assert round(b["max_dd"]) == 15560


def test_l2_anchor(causal):
    res, bs = causal
    b = aggregate.boxes_for_layer(res, "L2", bs)
    # l2v2 champion (reverse-entry-only engine, re-optimized 2026-06-22) — the honest, OOS-positive L2.
    assert b["n_taken"] == 48
    assert round(b["pnl"]) == 24498
    assert round(b["max_dd"]) == 7015


def test_combined_anchor(causal):
    res, bs = causal
    b = aggregate.combined_boxes(res, bs)
    # l2v2-era combined (L1 frozen + the honest reverse-entry-only L2)
    assert b["n_taken"]["value"] == 325                    # == 277 (L1) + 48 (L2)
    assert round(b["pnl"]["value"]) == 176154             # == $151,655 + $24,498
    assert round(b["max_dd"]["value"]) == 18145           # recomputed, merged book (< L1+L2 DDs summed)
    assert round(b["uplift"]["value"]) == 24498           # L2's exact marginal contribution


@pytest.mark.parametrize("window", ["full", "2024", "2025", "2026", "full+20d", "2026+20d"])
def test_run_l1_window_matches_build_payload(window):
    """STEP 3b gate: the causal run_l1 windowed via strategy.window_slice must reproduce
    strategy.build_payload's numbers for EVERY window — proving the shared slice helper + the L2
    gate-seed carried on L1Result.vf_seed keep the two engines in lockstep across windows."""
    import numpy as np
    import strategy
    from optimize.l2 import l1_runner
    P = dict(sl_soft=30, sl_hard=40, tp=60, gate_pct=0, dd_limit=0, cooldown=0, flip=False,
             k=1, indicators=[])
    r = l1_runner.run_l1("4h", params={**P, "ind_1min": False, "window": window})
    pnls = np.array([t["pnl"] for t in r.ledger], dtype=float)
    eq = np.cumsum(pnls)
    r_dd = float((np.maximum.accumulate(eq) - eq).max()) if len(pnls) else 0.0
    s = strategy.build_payload(*strategy.get_bundle("4h"), {**P, "window": window, "timeframe": "4h"})["meta"]["summary"]
    assert len(pnls) == s["n_taken"], f"{window}: n {len(pnls)} != {s['n_taken']}"
    assert abs(pnls.sum() - s["pnl"]) < 1.0, f"{window}: P/L {pnls.sum()} != {s['pnl']}"
    assert abs(r_dd - s["max_dd"]) < 1.0, f"{window}: max_dd {r_dd} != {s['max_dd']}"


def test_frozen_default_guard():
    """The default L1 params must round-trip through validate_layer_params unchanged, so run_causal's
    use_frozen equality (logbook.py:126) and build_view_payload's (payload.py:391) both select the
    cached oracle. Any new schema key added asymmetrically breaks THIS test before it breaks parity."""
    default = payload.l1_default_params(_TF)
    revalidated = payload.validate_layer_params(default)
    assert revalidated == default, (
        "l1_default_params no longer round-trips through validate_layer_params — the frozen-oracle "
        "fast path (use_frozen) is broken; the $151,655/277 anchor will recompute off a fresh path."
    )
