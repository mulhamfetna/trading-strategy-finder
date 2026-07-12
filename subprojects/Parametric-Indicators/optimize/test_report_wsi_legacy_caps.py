"""A LEGACY champion must not lose its time cap when its pareto CSV is regenerated.

The regression this pins: report_wsi._row decided "is the bar cap armed?" with

    cap_1min = pr.get("cap_1min", 0) if pr.get("en_cap_bars") else 0

Legacy studies (wsh4 / hg1 / cl1 / ng1 …) ran before the two cap switches existed, so they carry NO
`en_cap_bars` param at all — the truthiness test is False for every one of them, and the cap was silently
stripped (CL 2h: cap_1min 9 → 0). That rewrote the DEPLOYED champions the moment their CSVs were
regenerated, turning a 9-bar-capped strategy into an uncapped one worth a different amount of money.

No error, no warning — the champion just quietly stopped being the champion.
"""
import sys
from pathlib import Path

_PI = Path(__file__).resolve().parents[1]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

from optimize import report_wsi as R  # noqa: E402


def test_legacy_trial_keeps_its_bar_cap():
    """No en_cap_* params (a pre-2026-07-11 study) + cap_1min>0 ⇒ still a bars cap."""
    pr = {"cap_1min": 9}
    assert R._cap_mode_of(pr) == "bars"


def test_legacy_trial_without_a_cap_stays_uncapped():
    assert R._cap_mode_of({"cap_1min": 0}) == "none"
    assert R._cap_mode_of({}) == "none"


def test_new_trial_switches_drive_the_mode():
    assert R._cap_mode_of({"en_cap_bars": True, "en_cap_eod": False, "cap_1min": 451}) == "bars"
    assert R._cap_mode_of({"en_cap_bars": False, "en_cap_eod": True, "cap_1min": 451}) == "eod"
    assert R._cap_mode_of({"en_cap_bars": True, "en_cap_eod": True, "cap_1min": 451}) == "both"
    assert R._cap_mode_of({"en_cap_bars": False, "en_cap_eod": False, "cap_1min": 451}) == "none"


def _row_of(params, attrs=None):
    """Minimal fake optuna trial for _row()."""
    class T:
        user_attrs = attrs or {"full_pnl": 1.0, "full_dd": 1.0, "median_pnl": 1.0,
                               "worst_dd": 1.0, "median_win": 1.0}
        values = [1.0, -1.0, 50.0]
    t = T()
    base = {"sl_soft": 10.0, "sl_hard_delta": 5.0, "tp": 20.0, "gate_pct": 0.0,
            "dd_limit": 0.0, "cooldown": 0, "flip": False, "k": 1}
    t.params = {**base, **params}
    return R._row(t)


def test_row_preserves_a_legacy_cap():
    """THE REGRESSION: a legacy champion's cap must survive the round-trip to the pareto CSV."""
    row = _row_of({"cap_1min": 9})                       # no en_cap_* — a legacy trial
    assert row["cap_1min"] == 9, "legacy cap was stripped — the deployed champion would be rewritten"
    assert row["cap_mode"] == "bars"


def test_row_zeroes_cap_1min_when_no_bar_cap_is_armed():
    row = _row_of({"en_cap_bars": False, "en_cap_eod": True, "cap_1min": 451})
    assert row["cap_mode"] == "eod"
    assert row["cap_1min"] == 0                          # a bars count is meaningless under eod-only


def test_row_keeps_cap_1min_under_both():
    row = _row_of({"en_cap_bars": True, "en_cap_eod": True, "cap_1min": 451})
    assert row["cap_mode"] == "both" and row["cap_1min"] == 451


def test_cap_switches_are_not_harvested_as_indicators():
    """en_cap_bars/en_cap_eod start with 'en_' but are NOT indicators — a bare startswith() would list
    phantom indicators named 'cap_bars'/'cap_eod' and corrupt the rebuilt champion."""
    enabled = R._enabled_inds({"en_cap_bars": True, "en_cap_eod": True, "en_macd": True})
    assert enabled == ["macd"]
