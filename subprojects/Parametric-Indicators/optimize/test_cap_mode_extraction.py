"""The cap mode a champion is EXTRACTED with must equal the one it was SCORED with.

THE BUG THIS LOCKS OUT (found on the eod1 campaign, 54 studies, 5 hours of compute):

    optimizer.objective()   en_cap_eod = True if force_eod else trial.suggest_categorical(...)

Under --force-eod the switch is PINNED, not suggested — and Optuna only records params it was asked to
SUGGEST. So `en_cap_eod` is simply ABSENT from trial.params. report_wsi then re-derived the exit rule from
those params, read the missing switch as OFF, and wrote out 54 champions that say "hold overnight" —
the exact opposite of what the campaign forced and what the scorer actually measured. Nothing crashed;
the numbers all looked plausible. Deploying them would have run a different strategy than the one that won.

THE FIX, IN TWO PARTS, BOTH TESTED HERE:
  * the optimizer RECORDS the resolved cap_mode/cap_1min as user_attrs (single source of truth), and
  * the extractor PREFERS that record over any re-derivation.
WSI_FORCE_EOD=1 recovers studies that ran before the record existed.
"""
import importlib
import os

import pytest

from optimize import optimizer, report_wsi


def cap_mode(params, user_attrs=None, forced=False):
    """Re-import under the requested env so the module-level _FORCED_EOD is re-read."""
    old = os.environ.get("WSI_FORCE_EOD")
    os.environ["WSI_FORCE_EOD"] = "1" if forced else "0"
    try:
        importlib.reload(report_wsi)
        return report_wsi._cap_mode_of(params, user_attrs)
    finally:
        if old is None:
            os.environ.pop("WSI_FORCE_EOD", None)
        else:
            os.environ["WSI_FORCE_EOD"] = old
        importlib.reload(report_wsi)


# ── the recorded value is authoritative ─────────────────────────────────────────────────────────────
@pytest.mark.parametrize("mode", ["none", "bars", "eod", "both"])
def test_user_attr_is_authoritative(mode):
    """Whatever the scorer was handed is what we extract — even if the params would say otherwise."""
    # params deliberately contradict the record: a re-derivation would return "bars"
    assert cap_mode({"en_cap_bars": True, "en_cap_eod": False, "cap_1min": 7}, {"cap_mode": mode}) == mode


def test_user_attr_ignored_when_junk():
    """A malformed record must not poison the result — fall through to the switches."""
    assert cap_mode({"en_cap_bars": True, "en_cap_eod": True}, {"cap_mode": "sideways"}) == "both"


# ── THE ACTUAL BUG: a pinned switch is absent from params ───────────────────────────────────────────
def test_forced_eod_study_without_record_is_recovered():
    """--force-eod pins en_cap_eod ⇒ it is ABSENT from params. WSI_FORCE_EOD=1 must restore it.

    This is the exact param shape of all 54 eod1 trials: en_cap_bars present, en_cap_eod MISSING."""
    assert cap_mode({"en_cap_bars": True, "cap_1min": 500}, forced=True) == "both"
    assert cap_mode({"en_cap_bars": False, "cap_1min": 500}, forced=True) == "eod"


def test_forced_eod_study_without_the_flag_reproduces_the_bug():
    """Documents the hazard: same trial, no WSI_FORCE_EOD ⇒ the end-of-day close silently vanishes.

    Pinned in a test so nobody 'fixes' the default and reintroduces it quietly."""
    assert cap_mode({"en_cap_bars": True, "cap_1min": 500}) == "bars"   # ← the wrong answer that shipped
    assert cap_mode({"en_cap_bars": False, "cap_1min": 500}) == "none"  # ← ditto


def test_env_flag_never_overrides_a_searched_switch():
    """If en_cap_eod WAS searched, its recorded value is the truth — the env flag must not stomp it."""
    assert cap_mode({"en_cap_bars": True, "en_cap_eod": False}, forced=True) == "bars"
    assert cap_mode({"en_cap_bars": False, "en_cap_eod": False}, forced=True) == "none"


# ── legacy studies (predate both switches) ──────────────────────────────────────────────────────────
def test_legacy_nonzero_cap_is_a_bars_cap():
    """wsh4/hg1/cl1/ng1 carry no switches at all; a non-zero cap_1min always meant a bars cap.
    Reading it as 'no cap' is what corrupted the deployed CL/NG champions once already."""
    assert cap_mode({"cap_1min": 9}) == "bars"
    assert cap_mode({"cap_1min": 0}) == "none"


# ── the optimizer really does record it ─────────────────────────────────────────────────────────────
def test_derive_cap_mode_truth_table():
    d = optimizer.derive_cap_mode
    assert (d(False, False), d(True, False), d(False, True), d(True, True)) == \
           ("none", "bars", "eod", "both")


def test_optimizer_records_cap_mode_as_user_attr():
    """The whole fix rests on this write existing. Guard the source so a refactor cannot drop it."""
    import inspect
    src = inspect.getsource(optimizer)
    assert 'set_user_attr("cap_mode"' in src, "optimizer must RECORD the cap mode it scored with"
    assert 'set_user_attr("cap_1min"' in src, "optimizer must RECORD the bar count it scored with"
