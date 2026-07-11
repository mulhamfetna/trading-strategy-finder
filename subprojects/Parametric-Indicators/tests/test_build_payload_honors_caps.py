"""strategy.build_payload must HONOR the time caps.

It didn't. validate_params dropped cap_1min / cap_mode / eod_margin_min on the floor, so the legacy
chart + golden path ran every preset UNCAPPED. That was invisible while all NQ champions were capless —
but the 2026-07-11 cold-start champions are capped (NQ 4h uses bars/451), and the gap showed up as
build_payload reporting $143,291 for a champion whose true on-screen value is $148,670.

The shareable-bundle work had already measured this divergence (up to −73% on capped champions) and
worked around it by using the causal engine instead. This is the actual fix.
"""
import sys
from pathlib import Path

_PI = Path(__file__).resolve().parents[1]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

import pytest  # noqa: E402

import strategy  # noqa: E402


BASE = {"sl_soft": 60, "sl_hard": 120, "tp": 150, "gate_pct": 0, "dd_limit": 0,
        "cooldown": 0, "flip": False, "window": "full", "indicators": [], "k": 1}


def test_validate_params_preserves_the_cap_keys():
    P = strategy.validate_params({**BASE, "cap_1min": 451, "cap_mode": "bars"}, "NQ")
    assert P["cap_1min"] == 451
    assert P["cap_mode"] == "bars"
    assert P["eod_margin_min"] == 15


def test_bare_cap_1min_still_means_a_bars_cap():
    """Back-compat: every existing champion carries cap_1min with no explicit mode."""
    P = strategy.validate_params({**BASE, "cap_1min": 300}, "NQ")
    assert P["cap_mode"] == "bars"


def test_absent_caps_are_off_and_unchanged():
    P = strategy.validate_params(dict(BASE), "NQ")
    assert P["cap_1min"] == 0 and P["cap_mode"] == "none"


def test_unknown_cap_mode_is_rejected_loudly():
    with pytest.raises(strategy.ParamError):
        strategy.validate_params({**BASE, "cap_mode": "eod_maybe"}, "NQ")


def test_build_payload_actually_applies_the_bar_cap():
    """THE REGRESSION TEST: a tight cap must change the result. Before the fix it did nothing at all."""
    bundle = strategy.get_bundle("4h", "NQ")
    uncapped = strategy.build_payload(*bundle, dict(BASE), instrument="NQ")
    capped = strategy.build_payload(*bundle, {**BASE, "cap_1min": 30, "cap_mode": "bars"},
                                    instrument="NQ")
    assert uncapped["meta"]["summary"]["pnl"] != capped["meta"]["summary"]["pnl"], \
        "cap_1min had no effect on build_payload — the cap is being dropped again"
    assert any(t.get("exit_reason") == "TIME_CAP" for t in capped.get("trades", [])), \
        "no TIME_CAP exits fired despite a 30-bar cap"


def test_build_payload_applies_end_of_day_cap():
    bundle = strategy.get_bundle("4h", "NQ")
    eod = strategy.build_payload(*bundle, {**BASE, "cap_mode": "eod"}, instrument="NQ")
    assert any(t.get("exit_reason") == "END_OF_DAY" for t in eod.get("trades", [])), \
        "no END_OF_DAY exits fired with cap_mode='eod'"


def test_build_payload_matches_the_causal_engine_on_a_capped_champion():
    """build_payload (chart/golden path) and build_view_payload (what the dashboard SHOWS) must now agree
    on a capped preset. They did not before — that divergence is what made the golden gate unable to
    baseline a capped champion."""
    from optimize.l2 import payload as L2

    p = {**BASE, "cap_1min": 451, "cap_mode": "bars", "ind_1min": True, "timeframe": "4h"}
    legacy = strategy.build_payload(*strategy.get_bundle("4h", "NQ"), p, instrument="NQ")
    causal = L2.build_view_payload(dict(p, window="full"), {}, "4h", "l1",
                                   instrument="NQ", l1_engine=p)

    a = legacy["meta"]["summary"]["pnl"]
    b = causal["meta"]["boxes"]["pnl"]
    assert abs(a - b) < 1.0, f"legacy build_payload ${a:,.0f} != causal on-screen ${b:,.0f}"
