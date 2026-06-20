"""STEP 0 parity anchor — the single test that pins the three headline numbers of the two-layer
system to the CAUSAL source of truth (run_causal -> aggregate), plus the load-bearing frozen-default
guard. Every step of the unified-dashboard rebuild must keep this green.

Anchors (NQ, $20/pt, 1 contract, full research window):
  L1 (frozen lean champion)  $149,989 / 255 trades / $15,491 max DD
  L2 (extend champion)        $78,391 /  80 trades /  $8,961 max DD
  Combined                   $228,380 / 335 trades / $20,303 max DD  (recomputed merged book)

The frozen-default guard protects the disk-cached oracle: run_causal selects it via the EXACT dict
equality use_frozen = (validate_layer_params(l1_default_params(tf)) == l1_default_params(tf))
(logbook.py:126). build_view_payload repeats the same check (payload.py:391). If a future schema change
adds a key to validate_layer_params without echoing it in l1_default_params/_lean_params, this equality
silently fails, the default routes OFF the cached oracle, and the $149,989/255 anchor can drift. This
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
_L2_CHAMP = _PI / "optimize" / "results" / "l2v1_4h_champion.json"


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
    assert b["n_taken"] == 255
    assert round(b["pnl"]) == 149989
    assert round(b["max_dd"]) == 15491


def test_l2_anchor(causal):
    res, bs = causal
    b = aggregate.boxes_for_layer(res, "L2", bs)
    assert b["n_taken"] == 80
    assert round(b["pnl"]) == 78391
    assert round(b["max_dd"]) == 8961


def test_combined_anchor(causal):
    res, bs = causal
    b = aggregate.combined_boxes(res, bs)
    assert b["n_taken"]["value"] == 335
    assert round(b["pnl"]["value"]) == 228380
    assert round(b["max_dd"]["value"]) == 20303          # recomputed, merged book (< L1+L2 DDs)
    assert round(b["uplift"]["value"]) == 78391           # L2's exact marginal contribution


def test_frozen_default_guard():
    """The default L1 params must round-trip through validate_layer_params unchanged, so run_causal's
    use_frozen equality (logbook.py:126) and build_view_payload's (payload.py:391) both select the
    cached oracle. Any new schema key added asymmetrically breaks THIS test before it breaks parity."""
    default = payload.l1_default_params(_TF)
    revalidated = payload.validate_layer_params(default)
    assert revalidated == default, (
        "l1_default_params no longer round-trips through validate_layer_params — the frozen-oracle "
        "fast path (use_frozen) is broken; the $149,989/255 anchor will recompute off a fresh path."
    )
